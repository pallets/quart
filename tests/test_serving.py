import asyncio
from unittest.mock import Mock

import h11
import h2
import pytest

from quart import Quart, ResponseReturnValue
from quart.serving import H11Server, H2Server, Server

BASIC_H11_HEADERS = [('Host', 'quart')]
BASIC_H2_HEADERS = [
    (':authority', 'quart'), (':path', '/'), (':scheme', 'https'), (':method', 'GET'),
]
BASIC_DATA = 'index'
FLOW_WINDOW_SIZE = 1


class MockTransport:

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


@pytest.fixture()
def serving_app() -> Quart:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> ResponseReturnValue:
        return BASIC_DATA, 202, {'X-Test': 'Test'}

    return app


def test_server() -> None:
    h2_ssl_mock = Mock()
    h2_ssl_mock.selected_alpn_protocol.return_value = 'h2'
    transport = Mock()
    transport.get_extra_info.return_value = h2_ssl_mock
    server = Server(Mock(), Mock())
    server.connection_made(transport)
    assert isinstance(server._http_server, H2Server)
    transport.get_extra_info.return_value = None
    server.connection_made(transport)
    assert isinstance(server._http_server, H11Server)


@pytest.mark.asyncio
async def test_h11server(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    transport = MockTransport()
    server = H11Server(serving_app, event_loop, transport)  # type: ignore
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
            assert (b'x-test', b'Test') in event.headers
        elif isinstance(event, h11.Data):
            response_data += event.data
        else:
            break
    assert response_data.decode() == BASIC_DATA


@pytest.mark.asyncio
async def test_h2server(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    transport = MockTransport()
    server = H2Server(serving_app, event_loop, transport)  # type: ignore
    connection = h2.connection.H2Connection()
    connection.initiate_connection()
    server.data_received(connection.data_to_send())
    connection.send_headers(1, BASIC_H2_HEADERS, end_stream=True)
    server.data_received(connection.data_to_send())
    response_data = b''
    connection_open = True
    while connection_open:
        await transport.updated.wait()
        events = connection.receive_data(transport.data)
        transport.clear()
        for event in events:
            if isinstance(event, h2.events.ResponseReceived):
                assert (b':status', b'202') in event.headers
                assert (b'server', b'quart-h2') in event.headers
                assert (b'x-test', b'Test') in event.headers
            elif isinstance(event, h2.events.DataReceived):
                response_data += event.data
            elif isinstance(event, (h2.events.StreamEnded, h2.events.ConnectionTerminated)):
                connection_open = False
    assert response_data.decode() == BASIC_DATA


@pytest.mark.asyncio
async def test_h2_flow_control(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    transport = MockTransport()
    server = H2Server(serving_app, event_loop, transport)  # type: ignore
    connection = h2.connection.H2Connection()
    connection.initiate_connection()
    connection.update_settings({h2.settings.SettingCodes.INITIAL_WINDOW_SIZE: FLOW_WINDOW_SIZE})
    server.data_received(connection.data_to_send())
    connection.send_headers(1, BASIC_H2_HEADERS, end_stream=True)
    server.data_received(connection.data_to_send())
    response_data = b''
    connection_open = True
    while connection_open:
        await transport.updated.wait()
        events = connection.receive_data(transport.data)
        transport.clear()
        for event in events:
            if isinstance(event, h2.events.DataReceived):
                assert len(event.data) <= FLOW_WINDOW_SIZE
                response_data += event.data
                connection.acknowledge_received_data(event.flow_controlled_length, 1)
                server.data_received(connection.data_to_send())
            elif isinstance(event, (h2.events.StreamEnded, h2.events.ConnectionTerminated)):
                connection_open = False
    assert response_data.decode() == BASIC_DATA
