import asyncio
from itertools import chain
from logging import Logger
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Union  # noqa: F401

import h11

from ._base import RequestResponseServer
from ..datastructures import CIMultiDict
from ..wrappers import Request, Response  # noqa: F401

if TYPE_CHECKING:
    from ..app import Quart  # noqa

DEFAULT_MAX_INCOMPLETE_EVENT_SIZE = 16 * 1024


class WrongProtocolError(Exception):

    def __init__(self, request: h11.Request) -> None:
        self.request = request


class WebsocketProtocolRequired(WrongProtocolError):
    pass


class H2CProtocolRequired(WrongProtocolError):
    pass


class H11Server(RequestResponseServer):

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            logger: Optional[Logger],
            access_log_format: str,
            timeout: int,
            *,
            max_incomplete_size: Optional[int]=None,
    ) -> None:
        super().__init__(app, loop, transport, logger, 'h11', access_log_format, timeout)
        self.connection = h11.Connection(
            h11.SERVER,
            max_incomplete_event_size=max_incomplete_size or DEFAULT_MAX_INCOMPLETE_EVENT_SIZE,
        )

    def data_received(self, data: bytes) -> None:
        super().data_received(data)
        self.connection.receive_data(data)
        self._handle_events()

    def eof_received(self) -> bool:
        self.connection.receive_data(b'')
        return True

    def _handle_events(self) -> None:
        while True:
            if self.connection.they_are_waiting_for_100_continue:
                self._send(h11.InformationalResponse(
                    status_code=100, headers=self.response_headers(),
                ))
            try:
                event = self.connection.next_event()
            except h11.RemoteProtocolError:
                self._handle_error()
                self.close()
                break
            else:
                if isinstance(event, h11.Request):
                    headers = CIMultiDict()
                    if event.http_version < b'1.1':
                        headers.setdefault('host', self.app.config['SERVER_NAME'] or '')
                    for name, value in event.headers:
                        headers.add(name.decode().title(), value.decode())
                    if 'Upgrade' in headers:
                        self._handle_upgrade_request(headers, event)
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

    def _handle_upgrade_request(self, headers: CIMultiDict, event: h11.Request) -> None:
        self._keep_alive_timeout_handle.cancel()
        connection_tokens = headers.get('connection', '').lower().split(',')
        if (
                any(token.strip() == 'upgrade' for token in connection_tokens) and
                headers.get('upgrade', '').lower() == 'websocket' and
                event.method.decode().upper() == 'GET'
        ):
            raise WebsocketProtocolRequired(event)
        # h2c Upgrade requests with a body are a pain as the body must
        # be fully recieved in HTTP/1.1 before the upgrade response
        # and HTTP/2 takes over, so Quart ignores the upgrade and
        # responds in HTTP/1.1. Use a preflight OPTIONS request to
        # initiate the upgrade if really required (or just use h2).
        elif (
                headers.get('upgrade', '').lower() == 'h2c' and 'Content-Length' not in headers
                and 'Transfer-Encoding' not in headers
        ):
            self._send(h11.InformationalResponse(
                status_code=101, headers=[('upgrade', 'h2c')] + self.response_headers(),
            ))
            raise H2CProtocolRequired(event)

    def _after_request(self, stream_id: int, future: asyncio.Future) -> None:
        super()._after_request(stream_id, future)
        if self.connection.our_state is h11.DONE:
            self.connection.start_next_cycle()
        self._handle_events()

    async def send_response(self, stream_id: int, response: Response, suppress_body: bool) -> None:
        headers = chain(
            ((key.strip(), value.strip()) for key, value in response.headers.items()),
            self.response_headers(),
        )
        self._send(h11.Response(status_code=response.status_code, headers=headers))
        if not suppress_body:
            async for data in response.response:
                self._send(h11.Data(data=data))
                await self.drain()
        self._send(h11.EndOfMessage())

    def _handle_error(self) -> None:
        self._send(h11.Response(
            status_code=400, headers=chain(
                [('content-length', '0'), ('connection', 'close')],
                self.response_headers(),
            ),
        ))
        self._send(h11.EndOfMessage())

    def _send(
            self, event: Union[h11.Data, h11.EndOfMessage, h11.InformationalResponse, h11.Response],
    ) -> None:
        self.write(self.connection.send(event))  # type: ignore
