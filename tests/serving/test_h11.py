import asyncio
from typing import Union
from unittest.mock import Mock

import h11
import pytest

from quart import Quart, request, ResponseReturnValue
from quart.serving.h11 import H11Server
from .helpers import MockTransport

BASIC_HEADERS = [('Host', 'quart'), ('Connection', 'close')]
BASIC_DATA = 'index'
FLOW_WINDOW_SIZE = 1


@pytest.fixture()
def serving_app() -> Quart:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> ResponseReturnValue:
        return BASIC_DATA, 202, {'X-Test': 'Test'}

    @app.route('/echo', methods=['POST', 'PUT'])
    async def push() -> ResponseReturnValue:
        data = await request.get_data(raw=False)
        return data

    @app.route('/chunked')
    async def chunked() -> ResponseReturnValue:
        return [b'chunked ', b'data']  # type: ignore

    return app


class MockConnection:

    def __init__(self, serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
        self.transport = MockTransport()
        self.client = h11.Connection(h11.CLIENT)
        self.server = H11Server(  # type: ignore
            serving_app, event_loop, self.transport, None, '', 5,
        )

    async def send(self, event: Union[h11.Request, h11.Data, h11.EndOfMessage]) -> None:
        await self.send_raw(self.client.send(event))

    async def send_raw(self, data: bytes) -> None:
        self.server.data_received(data)
        await asyncio.sleep(0)  # Yield to allow the server to process

    def get_events(self) -> list:
        events = []
        self.client.receive_data(self.transport.data)
        while True:
            event = self.client.next_event()
            if event in (h11.NEED_DATA, h11.PAUSED):
                break
            events.append(event)
            if isinstance(event, h11.ConnectionClosed):
                break
        return events


@pytest.mark.asyncio
async def test_get_request(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = MockConnection(serving_app, event_loop)
    await connection.send(h11.Request(method='GET', target='/', headers=BASIC_HEADERS))
    await connection.send(h11.EndOfMessage())
    await connection.transport.closed.wait()
    response, *data, end = connection.get_events()
    assert isinstance(response, h11.Response)
    assert response.status_code == 202
    assert (b'server', b'quart-h11') in response.headers
    assert b'date' in (header[0] for header in response.headers)
    assert (b'x-test', b'Test') in response.headers
    assert all(isinstance(datum, h11.Data) for datum in data)
    assert b''.join(datum.data for datum in data).decode() == BASIC_DATA
    assert isinstance(end, h11.EndOfMessage)


@pytest.mark.asyncio
async def test_post_request(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = MockConnection(serving_app, event_loop)
    await connection.send(
        h11.Request(
            method='POST', target='/echo',
            headers=BASIC_HEADERS + [('content-length', str(len(BASIC_DATA.encode())))],
        ),
    )
    await connection.send(h11.Data(data=BASIC_DATA.encode()))
    await connection.send(h11.EndOfMessage())
    await connection.transport.closed.wait()
    response, *data, end = connection.get_events()
    assert isinstance(response, h11.Response)
    assert response.status_code == 200
    assert all(isinstance(datum, h11.Data) for datum in data)
    assert b''.join(datum.data for datum in data).decode() == BASIC_DATA
    assert isinstance(end, h11.EndOfMessage)


@pytest.mark.asyncio
async def test_protocol_error(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = MockConnection(serving_app, event_loop)
    await connection.send_raw(b'broken nonsense\r\n\r\n')
    response = connection.get_events()[0]
    assert isinstance(response, h11.Response)
    assert response.status_code == 400
    assert (b'connection', b'close') in response.headers


@pytest.mark.asyncio
async def test_pipelining(serving_app: Quart, event_loop: asyncio.AbstractEventLoop) -> None:
    connection = MockConnection(serving_app, event_loop)
    # Note that h11 does not support client pipelining, so this is all raw checks
    await connection.send_raw(
        b'GET / HTTP/1.1\r\nHost: quart\r\nConnection: keep-alive\r\n\r\n'
        b'GET / HTTP/1.1\r\nHost: quart\r\nConnection: close\r\n\r\n',
    )
    await connection.transport.closed.wait()
    assert connection.transport.data.decode().count('HTTP/1.1') == 2


@pytest.mark.asyncio
async def test_client_sends_chunked(
        serving_app: Quart, event_loop: asyncio.AbstractEventLoop,
) -> None:
    connection = MockConnection(serving_app, event_loop)
    chunked_headers = [('transfer-encoding', 'chunked'), ('expect', '100-continue')]
    await connection.send(
        h11.Request(method='POST', target='/echo', headers=BASIC_HEADERS + chunked_headers),
    )
    await connection.transport.updated.wait()
    informational_response = connection.get_events()[0]
    assert isinstance(informational_response, h11.InformationalResponse)
    assert informational_response.status_code == 100
    connection.transport.clear()
    for chunk in [b'chunked ', b'data']:
        await connection.send(h11.Data(data=chunk, chunk_start=True, chunk_end=True))
    await connection.send(h11.EndOfMessage())
    response, *data, end = connection.get_events()
    assert isinstance(response, h11.Response)
    assert response.status_code == 200
    assert all(isinstance(datum, h11.Data) for datum in data)
    assert b''.join(datum.data for datum in data) == b'chunked data'
    assert isinstance(end, h11.EndOfMessage)


@pytest.mark.asyncio
async def test_server_sends_chunked(
        serving_app: Quart, event_loop: asyncio.AbstractEventLoop,
) -> None:
    connection = MockConnection(serving_app, event_loop)
    await connection.send(h11.Request(method='GET', target='/chunked', headers=BASIC_HEADERS))
    await connection.send(h11.EndOfMessage())
    await connection.transport.closed.wait()
    events = connection.get_events()
    response, *data, end = events
    assert isinstance(response, h11.Response)
    assert all(isinstance(datum, h11.Data) for datum in data)
    assert b''.join(datum.data for datum in data).decode() == 'chunked data'
    assert isinstance(end, h11.EndOfMessage)


def test_max_incomplete_size() -> None:
    transport = MockTransport()
    server = H11Server(Mock(), Mock(), transport, None, '', 5, max_incomplete_size=5)  # type: ignore # noqa: E501
    server.data_received(b'GET / HTTP/1.1\r\nHost: quart\r\n')  # Longer than 5 bytes
    assert transport.data.startswith(b'HTTP/1.1 400')
