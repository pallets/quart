import asyncio
from unittest.mock import Mock

import h11
import h2
import pytest

from quart import make_response, Quart, ResponseReturnValue
from quart.serving import H11Server, H2Server, HTTPProtocol, Server

BASIC_H11_HEADERS = [('Host', 'quart')]
BASIC_H2_HEADERS = [
    (':authority', 'quart'), (':path', '/'), (':scheme', 'https'), (':method', 'GET'),
]
BASIC_H2_PUSH_HEADERS = [
    (':authority', 'quart'), (':path', '/push'), (':scheme', 'https'), (':method', 'GET'),
]
BASIC_DATA = 'index'
FLOW_WINDOW_SIZE = 1


@pytest.fixture()
def serving_app() -> Quart:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> ResponseReturnValue:
        return BASIC_DATA, 202, {'X-Test': 'Test'}

    @app.route('/push')
    async def push() -> ResponseReturnValue:
        response = await make_response(BASIC_DATA, 202, {'X-Test': 'Test'})
        response.push_promises.add('/')
        return response

    return app


def test_server() -> None:
    h2_ssl_mock = Mock()
    h2_ssl_mock.selected_alpn_protocol.return_value = 'h2'
    transport = Mock()
    transport.get_extra_info.return_value = h2_ssl_mock
    server = Server(Mock(), Mock(), Mock(), '', '', 5)
    server.connection_made(transport)
    assert isinstance(server._http_server, H2Server)
    transport.get_extra_info.return_value = None
    server.connection_made(transport)
    assert isinstance(server._http_server, H11Server)


@pytest.mark.asyncio
async def test_timeout(event_loop: asyncio.AbstractEventLoop) -> None:
    timeout = 0.1
    protocol = HTTPProtocol(Mock(), event_loop, Mock(), None, '', '', timeout)  # type: ignore
    await asyncio.sleep(0.5 * timeout)
    protocol._transport.close.assert_not_called()  # type: ignore
    await asyncio.sleep(2 * timeout)
    protocol._transport.close.assert_called_once()  # type: ignore


class TestTransport:

    def __init__(self) -> None:
        self.data = bytearray()
        self.closed = asyncio.Event()
        self.updated = asyncio.Event()

    def get_extra_info(self, _: str) -> tuple:
        return ('127.0.0.1',)

    def write(self, data: bytes) -> None:
        self.data.extend(data)
        self.updated.set()

    def close(self) -> None:
        self.closed.set()

    def clear(self) -> None:
        self.data = bytearray()
        self.updated.clear()


@pytest.mark.asyncio
async def test_h11server(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    transport = TestTransport()
    server = H11Server(serving_app, event_loop, transport, None, '', '', 5)  # type: ignore
    connection = h11.Connection(h11.CLIENT)
    server.data_received(
        connection.send(h11.Request(method='GET', target='/', headers=BASIC_H11_HEADERS)),
    )
    server.data_received(connection.send(h11.EndOfMessage()))
    await transport.closed.wait()
    connection.receive_data(transport.data)
    response_data = b''
    while True:
        event = connection.next_event()
        if isinstance(event, h11.Response):
            assert event.status_code == 202
            assert (b'server', b'quart-h11') in event.headers
            assert b'date' in (header[0] for header in event.headers)
            assert (b'x-test', b'Test') in event.headers
        elif isinstance(event, h11.Data):
            response_data += event.data
        else:
            break
    assert response_data.decode() == BASIC_DATA


class TestH2Connection:

    def __init__(self, serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
        self.transport = TestTransport()
        self.server = H2Server(  # type: ignore
            serving_app, event_loop, self.transport, None, '', 'authority', 5,
        )
        self.connection = h2.connection.H2Connection()

    def send_request(self, headers: list, settings: dict) -> int:
        self.connection.initiate_connection()
        self.connection.update_settings(settings)
        self.server.data_received(self.connection.data_to_send())
        stream_id = self.connection.get_next_available_stream_id()
        self.connection.send_headers(stream_id, headers, end_stream=True)
        self.server.data_received(self.connection.data_to_send())
        return stream_id

    async def get_events(self) -> h2.events.Event:
        connection_open = True
        while connection_open:
            await self.transport.updated.wait()
            events = self.connection.receive_data(self.transport.data)
            self.transport.clear()
            for event in events:
                if isinstance(event, (h2.events.StreamEnded, h2.events.ConnectionTerminated)):
                    connection_open = False
                elif isinstance(event, h2.events.DataReceived):
                    self.connection.acknowledge_received_data(
                        event.flow_controlled_length, event.stream_id,
                    )
                    self.server.data_received(self.connection.data_to_send())
                print(event)
                yield event


@pytest.mark.asyncio
async def test_h2server(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = TestH2Connection(serving_app, event_loop)
    connection.send_request(BASIC_H2_HEADERS, {})
    response_data = b''
    async for event in connection.get_events():
        if isinstance(event, h2.events.ResponseReceived):
            assert (b':status', b'202') in event.headers
            assert (b'server', b'quart-h2') in event.headers
            assert b'date' in (header[0] for header in event.headers)
            assert (b'x-test', b'Test') in event.headers
        elif isinstance(event, h2.events.DataReceived):
            response_data += event.data
    assert response_data.decode() == BASIC_DATA


@pytest.mark.asyncio
async def test_h2_flow_control(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = TestH2Connection(serving_app, event_loop)
    connection.send_request(
        BASIC_H2_HEADERS, {h2.settings.SettingCodes.INITIAL_WINDOW_SIZE: FLOW_WINDOW_SIZE},
    )
    response_data = b''
    async for event in connection.get_events():
        if isinstance(event, h2.events.DataReceived):
            assert len(event.data) <= FLOW_WINDOW_SIZE
            response_data += event.data
    assert response_data.decode() == BASIC_DATA


@pytest.mark.asyncio
async def test_h2_push(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = TestH2Connection(serving_app, event_loop)
    connection.send_request(BASIC_H2_PUSH_HEADERS, {})
    push_received = False
    async for event in connection.get_events():
        if isinstance(event, h2.events.PushedStreamReceived):
            assert (b':path', b'/') in event.headers
            assert (b':method', b'GET') in event.headers
            assert (b':scheme', b'https') in event.headers
            assert (b':authority', b'authority') in event.headers
            push_received = True
    assert push_received
