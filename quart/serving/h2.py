import asyncio
from logging import Logger
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Union  # noqa: F401

import h2.config
import h2.connection
import h2.events
import h2.exceptions

from ._base import RequestResponseServer, Stream
from ..datastructures import CIMultiDict
from ..wrappers import Request, Response  # noqa: F401

if TYPE_CHECKING:
    import h11  # noqa
    from ..app import Quart  # noqa


class H2Stream(Stream):
    __slots__ = ('event')

    def __init__(self, loop: asyncio.AbstractEventLoop, request: Request) -> None:
        super().__init__(loop, request)
        self.event: Optional[asyncio.Event] = None

    def unblock(self) -> None:
        if self.event is not None:
            self.event.set()
            self.event = None

    async def block(self) -> None:
        self.event = asyncio.Event()
        await self.event.wait()


class H2Server(RequestResponseServer):

    stream_class = H2Stream

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            logger: Optional[Logger],
            access_log_format: str,
            timeout: int,
            *,
            upgrade_request: Optional['h11.Request']=None,
    ) -> None:
        super().__init__(app, loop, transport, logger, 'h2', access_log_format, timeout)
        self.connection = h2.connection.H2Connection(
            config=h2.config.H2Configuration(client_side=False, header_encoding='utf-8'),
        )
        if upgrade_request is None:
            self.connection.initiate_connection()
        else:
            headers = CIMultiDict()
            for name, value in upgrade_request.headers:
                headers.add(name.decode().title(), value.decode())
            self.connection.initiate_upgrade_connection(headers.get('HTTP2-Settings', ''))
            self.handle_request(
                1, upgrade_request.method.decode().upper(), upgrade_request.target.decode(),
                headers,
            )
        self.write(self.connection.data_to_send())  # type: ignore

    def data_received(self, data: bytes) -> None:
        super().data_received(data)
        try:
            events = self.connection.receive_data(data)
        except h2.exceptions.ProtocolError:
            self.write(self.connection.data_to_send())  # type: ignore
            self.close()
        else:
            self._handle_events(events)
            self.write(self.connection.data_to_send())  # type: ignore

    def _handle_events(self, events: List[h2.events.Event]) -> None:
        for event in events:
            if isinstance(event, h2.events.RequestReceived):
                headers = CIMultiDict()
                for name, value in event.headers:
                    headers.add(name.title(), value)
                self.handle_request(
                    event.stream_id, headers[':method'].upper(), headers[':path'], headers,
                )
            elif isinstance(event, h2.events.DataReceived):
                self.streams[event.stream_id].append(event.data)
            elif isinstance(event, h2.events.StreamReset):
                self.streams[event.stream_id].task.cancel()
            elif isinstance(event, h2.events.StreamEnded):
                self.streams[event.stream_id].complete()
            elif isinstance(event, h2.events.WindowUpdated):
                self._window_updated(event.stream_id)
            elif isinstance(event, h2.events.ConnectionTerminated):
                self.close()
                return

            self.write(self.connection.data_to_send())  # type: ignore

    async def send_response(self, stream_id: int, response: Response, suppress_body: bool) -> None:
        headers = [(':status', str(response.status_code))]
        headers.extend([(key, value) for key, value in response.headers.items()])
        headers.extend(self.response_headers())
        self.connection.send_headers(stream_id, headers)
        for push_promise in response.push_promises:
            self._server_push(stream_id, push_promise)
        self.write(self.connection.data_to_send())  # type: ignore
        if not suppress_body:
            async for data in response.response:
                await self._send_data(stream_id, data)
        self.connection.end_stream(stream_id)
        self.write(self.connection.data_to_send())  # type: ignore

    def _server_push(self, stream_id: int, path: str) -> None:
        push_stream_id = self.connection.get_next_available_stream_id()
        request_headers = [
            (':method', 'GET'), (':path', path),
            (':scheme', self.streams[stream_id].request.headers[':scheme']),
            (':authority', self.streams[stream_id].request.headers[':authority']),
        ]
        try:
            self.connection.push_stream(
                stream_id=stream_id, promised_stream_id=push_stream_id,
                request_headers=request_headers,
            )
        except h2.exceptions.ProtocolError:
            pass  # Client does not accept push promises
        else:
            self.handle_request(push_stream_id, 'GET', path, CIMultiDict(request_headers))

    async def _send_data(self, stream_id: int, data: bytes) -> None:
        while True:
            while not self.connection.local_flow_control_window(stream_id):
                await self.streams[stream_id].block()  # type: ignore

            chunk_size = min(len(data), self.connection.local_flow_control_window(stream_id))
            chunk_size = min(chunk_size, self.connection.max_outbound_frame_size)
            self.connection.send_data(stream_id, data[:chunk_size])
            self.write(self.connection.data_to_send())  # type: ignore
            data = data[chunk_size:]
            if not data:
                break
            await self.drain()

    def _window_updated(self, stream_id: Optional[int]) -> None:
        if stream_id:
            self.streams[stream_id].unblock()  # type: ignore
        elif stream_id is None:
            # Unblock all streams
            for stream in self.streams.values():
                stream.unblock()  # type: ignore
