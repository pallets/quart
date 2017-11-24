import asyncio
from typing import AsyncGenerator

import h2
import pytest

from quart import make_response, Quart, ResponseReturnValue
from quart.serving.h2 import H2Server

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


class MockTransport:

    def __init__(self) -> None:
        self.data = bytearray()
        self.closed = asyncio.Event()
        self.updated = asyncio.Event()

    def get_extra_info(self, _: str) -> tuple:
        return ('127.0.0.1',)

    def write(self, data: bytes) -> None:
        assert not self.closed.is_set()
        self.data.extend(data)
        self.updated.set()

    def close(self) -> None:
        self.updated.set()
        self.closed.set()

    def clear(self) -> None:
        self.data = bytearray()
        self.updated.clear()


class MockH2Connection:

    def __init__(self, serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
        self.transport = MockTransport()
        self.server = H2Server(  # type: ignore
            serving_app, event_loop, self.transport, None, '', 5,
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

    async def get_events(self) -> AsyncGenerator[h2.events.Event, None]:
        while True:
            await self.transport.updated.wait()
            events = self.connection.receive_data(self.transport.data)
            self.transport.clear()
            for event in events:
                if isinstance(event, (h2.events.StreamEnded, h2.events.ConnectionTerminated)):
                    self.transport.close()
                elif isinstance(event, h2.events.DataReceived):
                    self.connection.acknowledge_received_data(
                        event.flow_controlled_length, event.stream_id,
                    )
                    self.server.data_received(self.connection.data_to_send())
                yield event
            if self.transport.closed.is_set():
                break


@pytest.mark.asyncio
async def test_h2server(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = MockH2Connection(serving_app, event_loop)
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
async def test_h2_protocol_error(
        serving_app: Quart, event_loop: asyncio.AbstractEventLoop,
) -> None:
    connection = MockH2Connection(serving_app, event_loop)
    connection.server.data_received(b'broken nonsense\r\n\r\n')
    assert connection.transport.closed.is_set()  # H2 just closes on error


@pytest.mark.asyncio
async def test_h2_flow_control(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = MockH2Connection(serving_app, event_loop)
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
    connection = MockH2Connection(serving_app, event_loop)
    connection.send_request(BASIC_H2_PUSH_HEADERS, {})
    push_received = False
    async for event in connection.get_events():
        if isinstance(event, h2.events.PushedStreamReceived):
            assert (b':path', b'/') in event.headers
            assert (b':method', b'GET') in event.headers
            assert (b':scheme', b'https') in event.headers
            assert (b':authority', b'quart') in event.headers
            push_received = True
    assert push_received
