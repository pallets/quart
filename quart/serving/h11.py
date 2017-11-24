import asyncio
from itertools import chain
from logging import Logger
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Union  # noqa: F401

import h11

from ._base import HTTPProtocol
from ..datastructures import CIMultiDict
from ..wrappers import Request, Response  # noqa: F401

if TYPE_CHECKING:
    from ..app import Quart  # noqa


class H11Server(HTTPProtocol):

    protocol = 'h11'

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            logger: Optional[Logger],
            access_log_format: str,
            timeout: int,
    ) -> None:
        super().__init__(app, loop, transport, logger, access_log_format, timeout)
        self.connection = h11.Connection(h11.SERVER)

    def data_received(self, data: bytes) -> None:
        super().data_received(data)
        self.connection.receive_data(data)
        self._handle_events()

    def _handle_events(self) -> None:
        if self.connection.they_are_waiting_for_100_continue:
            self._send(
                h11.InformationalResponse(status_code=100, headers=self.response_headers),
            )
        while True:
            try:
                event = self.connection.next_event()
            except h11.RemoteProtocolError:
                self._handle_error()
                self.close()
                break
            else:
                if isinstance(event, h11.Request):
                    headers = CIMultiDict()
                    for name, value in event.headers:
                        headers.add(name.decode().title(), value.decode())
                    self.handle_request(
                        0, event.method.decode().upper(), event.target.decode(), headers,
                    )
                elif isinstance(event, h11.EndOfMessage):
                    self.streams[0].complete()
                elif isinstance(event, h11.Data):
                    self.streams[0].append(event.data)
                elif event is h11.NEED_DATA or event is h11.PAUSED:
                    break
                elif isinstance(event, h11.ConnectionClosed):
                    break
        if self.connection.our_state is h11.MUST_CLOSE:
            self.close()

    def _after_request(self, stream_id: int, future: asyncio.Future) -> None:
        super()._after_request(stream_id, future)
        if self.connection.our_state is h11.DONE:
            self.connection.start_next_cycle()
        self._handle_events()

    async def send_response(self, stream_id: int, response: Response) -> None:
        headers = chain(
            ((key, value) for key, value in response.headers.items()), self.response_headers(),
        )
        self._send(h11.Response(status_code=response.status_code, headers=headers))
        for data in response.response:
            self._send(h11.Data(data=data))
        self._send(h11.EndOfMessage())

    def _handle_error(self) -> None:
        self._send(h11.Response(status_code=400, headers=[]))
        self._send(h11.EndOfMessage())

    def _send(
            self, event: Union[h11.Data, h11.EndOfMessage, h11.InformationalResponse, h11.Response],
    ) -> None:
        self.send(self.connection.send(event))  # type: ignore
