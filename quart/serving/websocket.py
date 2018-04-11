import asyncio
from functools import partial
from itertools import chain
from logging import Logger
from typing import Optional, TYPE_CHECKING, Union

import h11
import wsproto.connection
import wsproto.events
import wsproto.extensions

from ._base import HTTPServer, suppress_body
from ..datastructures import CIMultiDict
from ..wrappers import Websocket

if TYPE_CHECKING:
    from ..app import Quart  # noqa


class WebsocketServer(HTTPServer):

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            logger: Optional[Logger],
            request: h11.Request,
    ) -> None:
        """Instantiate a Websocket handling server.

        This requires a request that has websocket upgrade headers
        present. If no such request exists, this is the wrong server
        to use, see H11Server or H2Server instead.
        """
        super().__init__(loop, transport, logger, 'wsproto')
        self.app = app
        self.connection = wsproto.connection.WSConnection(
            wsproto.connection.SERVER, extensions=[wsproto.extensions.PerMessageDeflate()],
        )
        self.task: Optional[asyncio.Future] = None
        self.queue: asyncio.Queue = asyncio.Queue()
        fake_client = h11.Connection(h11.CLIENT)
        self._buffer: Optional[Union[bytes, str]] = None
        # wsproto has a bug in the acceptance of Connection headers,
        # which this works around.
        headers = []
        for name, value in request.headers:
            if name.lower() == b'connection':
                headers.append((b'Connection', b'Upgrade'))
            else:
                headers.append((name, value))
        request.headers = headers

        self.data_received(fake_client.send(request))

    def data_received(self, data: bytes) -> None:
        super().data_received(data)
        self.connection.receive_bytes(data)
        for event in self.connection.events():
            if isinstance(event, wsproto.events.ConnectionRequested):
                self.handle_websocket(event)
            elif isinstance(event, wsproto.events.DataReceived):
                if self._buffer is None:
                    if isinstance(event, wsproto.events.TextReceived):
                        self._buffer = ''
                    else:
                        self._buffer = b''
                self._buffer += event.data
                if len(self._buffer) > self.app.config['MAX_CONTENT_LENGTH']:
                    self.write(self.connection.bytes_to_send())
                    self.close()
                if event.message_finished:
                    self.queue.put_nowait(self._buffer)
                    self._buffer = None
            elif isinstance(event, wsproto.events.ConnectionClosed):
                self.write(self.connection.bytes_to_send())
                self.close()
            self.write(self.connection.bytes_to_send())

    def close(self) -> None:
        if self.task is not None:
            self.task.cancel()
        super().close()

    @property
    def active(self) -> bool:
        return self.connection._state == wsproto.connection.ConnectionState.OPEN

    def handle_websocket(self, event: wsproto.events.ConnectionRequested) -> None:
        headers = CIMultiDict()
        for name, value in event.h11request.headers:
            headers.add(name.decode().title(), value.decode())
        headers['Remote-Addr'] = self.remote_addr
        scheme = 'wss' if self.ssl_info is not None else 'ws'
        websocket = Websocket(
            event.h11request.target.decode(), scheme, headers, self.queue, self.send_data,
            partial(self.accept_connection, event),
        )
        self.task = asyncio.ensure_future(self._handle_websocket(websocket))
        self.task.add_done_callback(self.cleanup_task)

    def accept_connection(self, event: wsproto.events.ConnectionRequested) -> None:
        if not self.active:
            self.connection.accept(event)
            self.write(self.connection.bytes_to_send())

    async def _handle_websocket(self, websocket: Websocket) -> None:
        response = await self.app.handle_websocket(websocket)
        if response is not None:
            if self.active:
                self.connection.close(wsproto.connection.CloseReason.INTERNAL_ERROR)
                self.write(self.connection.bytes_to_send())
            else:
                headers = chain(
                    ((key, value) for key, value in response.headers.items()),
                    self.response_headers(),
                )
                self.write(self.connection._upgrade_connection.send(
                    h11.Response(status_code=response.status_code, headers=headers),
                ))
                if not suppress_body('GET', response.status_code):
                    async for data in response.response:
                        self.write(self.connection._upgrade_connection.send(
                            h11.Data(data=data),
                        ))
                        await self.drain()
                self.write(self.connection._upgrade_connection.send(
                    h11.EndOfMessage(),
                ))
        self.close()

    def send_data(self, data: bytes) -> None:
        self.connection.send_data(data)
        self.write(self.connection.bytes_to_send())
