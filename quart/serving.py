import asyncio
from email.utils import formatdate
from functools import partial
from itertools import chain
from logging import Logger
from ssl import SSLContext
from time import time
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Union  # noqa: F401

import h11
import h2.config
import h2.connection
import h2.events
import h2.exceptions

from .datastructures import CIMultiDict
from .logging import AccessLogAtoms
from .wrappers import Request, Response  # noqa: F401

if TYPE_CHECKING:
    from .app import Quart  # noqa


class Stream:
    __slots__ = ('buffer', 'request', 'task')

    def __init__(self, loop: asyncio.AbstractEventLoop, request: Request) -> None:
        self.buffer = bytearray()
        self.request = request
        self.task: Optional[asyncio.Future] = None

    def append(self, data: bytes) -> None:
        self.buffer.extend(data)

    def complete(self) -> None:
        self.request._body.set_result(self.buffer)


class Server(asyncio.Protocol):
    __slots__ = (
        'access_log_format', 'app', 'logger', 'loop', 'timeout', '_http_server',
    )

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            logger: Optional[Logger],
            access_log_format: str,
            timeout: int,
    ) -> None:
        self.app = app
        self.loop = loop
        self._http_server: Optional[HTTPProtocol] = None
        self.logger = logger
        self.access_log_format = access_log_format
        self.timeout = timeout

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        ssl_object = transport.get_extra_info('ssl_object')
        if ssl_object is not None:
            protocol = ssl_object.selected_alpn_protocol()
        else:
            protocol = 'http/1.1'

        if protocol == 'h2':
            self._http_server = H2Server(
                self.app, self.loop, transport, self.logger, self.access_log_format,
                self.timeout,
            )
        else:
            self._http_server = H11Server(
                self.app, self.loop, transport, self.logger, self.access_log_format,
                self.timeout,
            )

    def connection_lost(self, _: Exception) -> None:
        self._http_server.close()

    def data_received(self, data: bytes) -> None:
        self._http_server.data_received(data)


class HTTPProtocol:

    protocol = ''
    stream_class = Stream

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            logger: Optional[Logger],
            access_log_format: str,
            timeout: int,
    ) -> None:
        self.app = app
        self.loop = loop
        self.logger = logger
        self.streams: Dict[int, Stream] = {}
        self.access_log_format = access_log_format
        self._timeout = timeout
        self._last_activity = time()
        self._timeout_handle = self.loop.call_later(self._timeout, self._handle_timeout)
        self._transport = transport

    def data_received(self, data: bytes) -> None:
        self._last_activity = time()

    def handle_request(
            self,
            stream_id: int,
            method: str,
            path: str,
            headers: CIMultiDict,
    ) -> None:
        self._timeout_handle.cancel()
        headers['Remote-Addr'] = self._transport.get_extra_info('peername')[0]
        request = self.app.request_class(method, path, headers, self.loop.create_future())
        self.streams[stream_id] = self.stream_class(self.loop, request)
        # It is important that the app handles the request in a unique
        # task as the globals are task locals
        self.streams[stream_id].task = asyncio.ensure_future(self._handle_request(stream_id))
        self.streams[stream_id].task.add_done_callback(partial(self._after_request, stream_id))

    async def _handle_request(self, stream_id: int) -> None:
        request = self.streams[stream_id].request
        response = await self.app.handle_request(request)
        await self.send_response(stream_id, response)
        if self.logger is not None:
            self.logger.info(
                self.access_log_format, AccessLogAtoms(request, response, self.protocol),
            )

    async def send_response(self, stream_id: int, response: Response) -> None:
        raise NotImplemented()

    def send(self, data: bytes) -> None:
        self._last_activity = time()
        self._transport.write(data)  # type: ignore

    def close(self) -> None:
        for stream in self.streams.values():
            stream.task.cancel()
        self._transport.close()
        self._timeout_handle.cancel()

    def _after_request(self, stream_id: int, future: asyncio.Future) -> None:
        del self.streams[stream_id]
        if not self.streams:
            self._timeout_handle = self.loop.call_later(self._timeout, self._handle_timeout)
        exception = future.exception()
        if exception is not None and not isinstance(exception, asyncio.CancelledError):
            self.logger.error('Request handling exception', exc_info=exception)

    def response_headers(self) -> List[Tuple[str, str]]:
        return [
            ('date', formatdate(time(), usegmt=True)), ('server', f"quart-{self.protocol}"),
        ]

    def _handle_timeout(self) -> None:
        if time() - self._last_activity > self._timeout:
            self.close()


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


class H2Server(HTTPProtocol):

    protocol = 'h2'
    stream_class = H2Stream

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
        self.connection = h2.connection.H2Connection(
            h2.config.H2Configuration(client_side=False, header_encoding='utf-8'),
        )
        self.connection.initiate_connection()
        self.send(self.connection.data_to_send())  # type: ignore

    def data_received(self, data: bytes) -> None:
        super().data_received(data)
        try:
            events = self.connection.receive_data(data)
        except h2.exceptions.ProtocolError:
            self.send(self.connection.data_to_send())  # type: ignore
            self.close()
        else:
            self._handle_events(events)

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
                self.streams.pop(event.stream_id).task.cancel()
            elif isinstance(event, h2.events.StreamEnded):
                self.streams[event.stream_id].complete()
            elif isinstance(event, h2.events.WindowUpdated):
                self._window_updated(event.stream_id)
            elif isinstance(event, h2.events.ConnectionTerminated):
                self.close()
                return

            self.send(self.connection.data_to_send())  # type: ignore

    async def send_response(self, stream_id: int, response: Response) -> None:
        headers = [(':status', str(response.status_code))]
        headers.extend([(key, value) for key, value in response.headers.items()])
        headers.extend(self.response_headers())
        self.connection.send_headers(stream_id, headers)
        for push_promise in response.push_promises:
            self._server_push(stream_id, push_promise)
        self.send(self.connection.data_to_send())  # type: ignore
        for data in response.response:
            await self._send_data(stream_id, data)
        self.connection.end_stream(stream_id)
        self.send(self.connection.data_to_send())  # type: ignore

    def _server_push(self, stream_id: int, path: str) -> None:
        push_stream_id = self.connection.get_next_available_stream_id()
        request_headers = [
            (':method', 'GET'), (':path', path),
            (':scheme', 'https'),  # quart only supports HTTPS HTTP2 so can assume this
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
            self.send(self.connection.data_to_send())  # type: ignore
            data = data[chunk_size:]
            if not data:
                break

    def _window_updated(self, stream_id: Optional[int]) -> None:
        if stream_id:
            self.streams[stream_id].unblock()  # type: ignore
        elif stream_id is None:
            # Unblock all streams
            for stream in self.streams.values():
                stream.unblock()  # type: ignore


def run_app(
        app: 'Quart',
        *,
        host: str='127.0.0.1',
        port: int=5000,
        access_log_format: str,
        ssl: Optional[SSLContext]=None,
        logger: Optional[Logger]=None,
        timeout: int,
        debug: bool=False,
) -> None:
    """Create a server to run the app on given the options.

    Arguments:
        app: The Quart app to run.
        host: Hostname e.g. localhost
        port: The port to listen on.
        ssl: Optional SSLContext to use.
        logger: Optional logger for serving (access) logs.
    """
    loop = asyncio.get_event_loop()
    loop.set_debug(debug)
    create_server = loop.create_server(
        lambda: Server(app, loop, logger, access_log_format, timeout),
        host, port, ssl=ssl,
    )
    server = loop.run_until_complete(create_server)

    scheme = 'http' if ssl is None else 'https'
    print("Running on {}://{}:{} (CTRL + C to quit)".format(scheme, host, port))

    try:
        loop.run_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
