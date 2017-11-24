import asyncio
from typing import AsyncGenerator

import h11
import pytest

from quart import make_response, Quart, ResponseReturnValue
from quart.serving.h11 import H11Server

BASIC_H11_HEADERS = [('Host', 'quart'), ('Connection', 'close')]
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


class MockH11Connection:

    def __init__(self, serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
        self.transport = MockTransport()
        self.server = H11Server(  # type: ignore
            serving_app, event_loop, self.transport, None, '', 5,
        )
        self.connection = h11.Connection(h11.CLIENT)

    def send_request(self, method: str, target: str, headers: list) -> None:
        self.server.data_received(
            self.connection.send(h11.Request(method=method, target=target, headers=headers)),
        )
        self.server.data_received(self.connection.send(h11.EndOfMessage()))

    async def get_events(self) -> AsyncGenerator:
        while True:
            await self.transport.updated.wait()
            self.connection.receive_data(self.transport.data)
            self.transport.clear()
            while True:
                event = self.connection.next_event()
                yield event
                if event is h11.NEED_DATA or isinstance(event, h11.ConnectionClosed):
                    break
            if self.transport.closed.is_set():
                break


@pytest.mark.asyncio
async def test_h11server(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = MockH11Connection(serving_app, event_loop)
    connection.send_request('GET', '/', BASIC_H11_HEADERS)
    response_data = b''
    async for event in connection.get_events():
        if isinstance(event, h11.Response):
            assert event.status_code == 202
            assert (b'server', b'quart-h11') in event.headers
            assert b'date' in (header[0] for header in event.headers)
            assert (b'x-test', b'Test') in event.headers
        elif isinstance(event, h11.Data):
            response_data += event.data
    assert response_data.decode() == BASIC_DATA


@pytest.mark.asyncio
async def test_h11_protocol_error(
        serving_app: Quart, event_loop: asyncio.AbstractEventLoop,
) -> None:
    connection = MockH11Connection(serving_app, event_loop)
    connection.server.data_received(b'broken nonsense\r\n\r\n')
    received_400_response = False
    async for event in connection.get_events():
        if isinstance(event, h11.Response):
            received_400_response = True
            assert event.status_code == 400
            assert (b'connection', b'close') in event.headers
    assert received_400_response


@pytest.mark.asyncio
async def test_h11_pipelining(
        serving_app: Quart, event_loop: asyncio.AbstractEventLoop,
) -> None:
    connection = MockH11Connection(serving_app, event_loop)
    # Note H11 does not support client pipelining
    connection.server.data_received(
        b'GET / HTTP/1.1\r\nHost: quart\r\nConnection: keep-alive\r\n\r\n'
        b'GET / HTTP/1.1\r\nHost: quart\r\nConnection: close\r\n\r\n',
    )
    await connection.transport.closed.wait()
    assert connection.transport.data.decode().count('HTTP/1.1') == 2
