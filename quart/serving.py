import asyncio
from functools import partial
from itertools import chain
from ssl import SSLContext
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Union  # noqa: F401

import h11
import h2.config
import h2.connection
import h2.events
import h2.exceptions

from .datastructures import CIMultiDict

if TYPE_CHECKING:
    from .app import Quart  # noqa


class Stream:
    __slots__ = ('buffer', 'future')

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.buffer = bytearray()
        self.future = loop.create_future()

    def append(self, data: bytes) -> None:
        self.buffer.extend(data)

    def complete(self) -> None:
        self.future.set_result(self.buffer)


class Server(asyncio.Protocol):
    __slots__ = ('app', 'loop', '_http_server')

    def __init__(self, app: 'Quart', loop: asyncio.AbstractEventLoop) -> None:
        self.app = app
        self.loop = loop
        self._http_server: Optional[HTTPProtocol] = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        ssl_object = transport.get_extra_info('ssl_object')
        if ssl_object is not None:
            protocol = ssl_object.selected_alpn_protocol()
        else:
            protocol = 'http/1.1'

        if protocol == 'h2':
            self._http_server = H2Server(self.app, self.loop, transport)
        else:
            self._http_server = H11Server(self.app, self.loop, transport)

    def data_received(self, data: bytes) -> None:
        self._http_server.data_received(data)


class HTTPProtocol:

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            server_header: str,
    ) -> None:
        self.app = app
        self.transport = transport
        self.loop = loop
        self.streams: Dict[int, Stream] = {}
        self.server_header = server_header

    def data_received(self, data: bytes) -> None:
        raise NotImplemented()

    def handle_request(
            self,
            stream_id: int,
            method: str,
            path: str,
            headers: CIMultiDict,
    ) -> None:
        headers['Remote-Addr'] = self.transport.get_extra_info('peername')[0]
        request = self.app.request_class(method, path, headers, self.streams[stream_id].future)
        # It is important that the app handles the request in a unique
        # task as the globals are task locals
        task = asyncio.ensure_future(self.app.handle_request(request))
        task.add_done_callback(partial(self.handle_response, stream_id))  # type: ignore

    def handle_response(self, stream_id: int, future: asyncio.Future) -> None:
        raise NotImplemented()

    def response_headers(self) -> List[Tuple[str, str]]:
        return [('server', self.server_header)]


class H11Server(HTTPProtocol):

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
    ) -> None:
        super().__init__(app, loop, transport, 'quart-h11')
        self.connection = h11.Connection(h11.SERVER)

    def data_received(self, data: bytes) -> None:
        self.connection.receive_data(data)
        self._handle_events()

    def _handle_events(self) -> None:
        if self.connection.they_are_waiting_for_100_continue:
            self._send(
                h11.InformationalResponse(status_code=100, headers=(('Date', ''), ('Server', ''))),
            )
        while True:
            try:
                event = self.connection.next_event()
            except h11.ProtocolError:
                self._handle_error()
                self.transport.close()
            else:
                if isinstance(event, h11.Request):
                    headers = CIMultiDict()
                    for name, value in event.headers:
                        headers.add(name.decode().title(), value.decode())
                    self.streams[0] = Stream(self.loop)
                    self.handle_request(
                        0, event.method.decode().upper(), event.target.decode(), headers,
                    )
                elif isinstance(event, h11.EndOfMessage):
                    self.streams[0].complete()
                elif isinstance(event, h11.Data):
                    self.streams[0].append(event.data)
                elif event is h11.NEED_DATA:
                    break
        if self.connection.our_state is h11.MUST_CLOSE:
            self.transport.close()
        elif self.connection.our_state is h11.DONE:
            self.connection.start_next_cycle()

    def handle_response(self, stream_id: int, future: asyncio.Future) -> None:
        response = future.result()
        headers = chain(
            ((key, value) for key, value in response.headers.items()), self.response_headers(),
        )
        self._send(h11.Response(status_code=response.status_code, headers=headers))
        for data in response.response:
            self._send(h11.Data(data=data))
        self._send(h11.EndOfMessage())
        self._handle_events()

    def _handle_error(self) -> None:
        self._send(h11.Response(status_code=400, headers=tuple()))
        self._send(h11.EndOfMessage())

    def _send(
            self, event: Union[h11.Data, h11.EndOfMessage, h11.InformationalResponse, h11.Response],
    ) -> None:
        self.transport.write(self.connection.send(event))  # type: ignore


class H2Server(HTTPProtocol):

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
    ) -> None:
        super().__init__(app, loop, transport, 'quart-h11')
        self.connection = h2.connection.H2Connection(
            h2.config.H2Configuration(client_side=False, header_encoding='utf-8'),
        )
        self.connection.initiate_connection()
        self.transport.write(self.connection.data_to_send())  # type: ignore

    def data_received(self, data: bytes) -> None:
        try:
            events = self.connection.receive_data(data)
        except h2.ProtocolError:
            self.transport.write(self.connection.data_to_send())  # type: ignore
            self.transport.close()
        else:
            self._handle_events(events)

    def _handle_events(self, events: List[h2.events.Event]) -> None:
        for event in events:
            if isinstance(event, h2.events.RequestReceived):
                headers = CIMultiDict()
                for name, value in event.headers:
                    headers.add(name.title(), value)
                self.streams[event.stream_id] = Stream(self.loop)
                self.handle_request(
                    event.stream_id, headers[':method'].upper(), headers[':path'], headers,
                )
            elif isinstance(event, h2.events.DataReceived):
                self.streams[event.stream_id].append(event.data)
            elif isinstance(event, h2.events.StreamEnded):
                self.streams[event.stream_id].complete()
            elif isinstance(event, h2.events.ConnectionTerminated):
                del self.streams[event.stream_id]
                self.transport.close()

            self.transport.write(self.connection.data_to_send())  # type: ignore

    def handle_response(self, stream_id: int, future: asyncio.Future) -> None:
        response = future.result()
        headers = [(':status', str(response.status_code))]
        headers.extend([(key, value) for key, value in response.headers.items()])
        headers.extend(self.response_headers())
        self.connection.send_headers(stream_id, headers)
        for data in response.response:
            self.connection.send_data(stream_id, data)
        self.connection.end_stream(stream_id)
        self.transport.write(self.connection.data_to_send())  # type: ignore


def run_app(
        app: 'Quart',
        *,
        host: str='127.0.0.1',
        port: int=5000,
        ssl: Optional[SSLContext]=None
) -> None:
    """Create a server to run the app on given the options.

    Arguments:
        app: The Quart app to run.
        host: Hostname e.g. localhost
        port: The port to listen on.
        ssl: SSLContext to use.
    """
    loop = asyncio.get_event_loop()
    create_server = loop.create_server(lambda: Server(app, loop), host, port, ssl=ssl)
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
        loop.close()
