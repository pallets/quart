import asyncio
from typing import Optional, TYPE_CHECKING, Union

import h11
import wsproto.connection
import wsproto.events
import wsproto.extensions

from ..datastructures import CIMultiDict
from ..exceptions import BadRequest, HTTPException, MethodNotAllowed, NotFound, RedirectRequired
from ..wrappers import Websocket

if TYPE_CHECKING:
    from ..app import Quart  # noqa


class WebsocketServer:

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
        self.data_received(fake_client.send(request))
        self._buffer: Optional[Union[bytes, str]] = None

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
        self.task.cancel()
        self._transport.close()

    def handle_websocket(self, event: wsproto.events.ConnectionRequested) -> None:
        headers = CIMultiDict()
        for name, value in event.h11request.headers:
            headers.add(name.decode().title(), value.decode())
        scheme = 'wss' if self._transport.get_extra_info('ssl_object') is not None else 'ws'
        websocket = Websocket(
            event.h11request.target.decode(), scheme, headers, self.queue, self.send_data,
        )
        adapter = self.app.create_url_adapter(websocket)
        try:
            url_rule, _ = adapter.match()
            if not url_rule.is_websocket:
                raise BadRequest()
        except (BadRequest, NotFound, MethodNotAllowed, RedirectRequired) as error:
            asyncio.ensure_future(self.send_error(error))
            self.close()
        else:
            self.connection.accept(event)
            self.task = asyncio.ensure_future(self._handle_websocket(websocket))

    async def _handle_websocket(self, websocket: Websocket) -> None:
        await self.app.handle_websocket(websocket)

    def send_data(self, data: bytes) -> None:
        self.connection.send_data(data)
        self._send()

    async def send_error(self, error: HTTPException) -> None:
        response = error.get_response()
        headers = ((key, value) for key, value in response.headers.items())
        self.connection._outgoing += self.connection._upgrade_connection.send(
            h11.Response(status_code=response.status_code, headers=headers),
        )
        async for data in response.response:
            self.connection._outgoing += self.connection._upgrade_connection.send(
                h11.Data(data=data),
            )
        self.connection._outgoing += self.connection._upgrade_connection.send(h11.EndOfMessage())
        self._send()

    def _send(self) -> None:
        self._transport.write(self.connection.bytes_to_send())  # type: ignore
