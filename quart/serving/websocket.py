import asyncio
from functools import partial
from itertools import chain
from typing import Optional, TYPE_CHECKING, Union

import h11
import wsproto.connection
import wsproto.events
import wsproto.extensions

from ._base import response_headers, suppress_body
from ..datastructures import CIMultiDict
from ..wrappers import Websocket

if TYPE_CHECKING:
    from ..app import Quart  # noqa


class WebsocketServer:

    protocol = 'wsproto'

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            request: h11.Request,
    ) -> None:
        self.app = app
        self.loop = loop
        self._transport = transport
        self.connection = wsproto.connection.WSConnection(
            wsproto.connection.SERVER, extensions=[wsproto.extensions.PerMessageDeflate()],
        )
        self.task: Optional[asyncio.Future] = None
        self.queue: asyncio.Queue = asyncio.Queue()
        fake_client = h11.Connection(h11.CLIENT)
        self._buffer: Optional[Union[bytes, str]] = None
        self.data_received(fake_client.send(request))

    @property
    def active(self) -> bool:
        return self.connection._state == wsproto.connection.ConnectionState.OPEN

    def data_received(self, data: bytes) -> None:
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
                if event.message_finished:
                    self.queue.put_nowait(self._buffer)
                    self._buffer = None
            elif isinstance(event, wsproto.events.ConnectionClosed):
                self._send()
                self.close()
            self._send()

    def eof_received(self) -> bool:
        pass

    def connection_lost(self, exception: Exception) -> None:
        self.close()

    def close(self) -> None:
        if self.task is not None:
            self.task.cancel()
        self._transport.close()

    def handle_websocket(self, event: wsproto.events.ConnectionRequested) -> None:
        headers = CIMultiDict()
        for name, value in event.h11request.headers:
            headers.add(name.decode().title(), value.decode())
        scheme = 'wss' if self._transport.get_extra_info('ssl_object') is not None else 'ws'
        websocket = Websocket(
            event.h11request.target.decode(), scheme, headers, self.queue, self.send_data,
            partial(self.accept_connection, event),
        )
        self.task = asyncio.ensure_future(self._handle_websocket(websocket))

    def accept_connection(self, event: wsproto.events.ConnectionRequested) -> None:
        if not self.active:
            self.connection.accept(event)
            self._send()

    async def _handle_websocket(self, websocket: Websocket) -> None:
        response = await self.app.handle_websocket(websocket)
        if response is not None:
            if self.active:
                self.connection.close(wsproto.connection.CloseReason.INTERNAL_ERROR)
            else:
                headers = chain(
                    ((key, value) for key, value in response.headers.items()),
                    response_headers(self.protocol),
                )
                self.connection._outgoing += self.connection._upgrade_connection.send(
                    h11.Response(status_code=response.status_code, headers=headers),
                )
                if not suppress_body('GET', response.status_code):
                    async for data in response.response:
                        self.connection._outgoing += self.connection._upgrade_connection.send(
                            h11.Data(data=data),
                        )
                self.connection._outgoing += self.connection._upgrade_connection.send(
                    h11.EndOfMessage(),
                )
        self._send()
        self.close()

    def send_data(self, data: bytes) -> None:
        self.connection.send_data(data)
        self._send()

    def _send(self) -> None:
        self._transport.write(self.connection.bytes_to_send())  # type: ignore
