import asyncio

import pytest

from quart import Quart
from quart.asgi import ASGIHTTPConnection, ASGIWebsocketConnection


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'headers, expected',
    [([(b'host', b'quart')], 'quart'), ([], '')],
)
async def test_http_1_0_host_header(headers: list, expected: str) -> None:
    app = Quart(__name__)
    scope = {
        'headers': headers,
        'http_version': '1.0',
        'method': 'GET',
        'scheme': 'https',
        'path': '/',
        'query_string': b'',
    }
    connection = ASGIHTTPConnection(app, scope)
    request = connection._create_request_from_scope()
    assert request.headers['host'] == expected


@pytest.mark.asyncio
async def test_http_completion() -> None:
    # Ensure that the connecion callable returns on completion
    app = Quart(__name__)
    scope = {
        'headers': [(b'host', b'quart')],
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'https',
        'path': '/',
        'query_string': b'',
    }
    connection = ASGIHTTPConnection(app, scope)

    queue: asyncio.Queue = asyncio.Queue()
    queue.put_nowait({'type': 'http.request', 'body': b'', 'more_body': False})

    async def receive() -> dict:
        # This will block after returning the first and only entry
        return await queue.get()

    async def send(message: dict) -> None:
        pass

    # This test fails if a timeout error is raised here
    await asyncio.wait_for(connection(receive, send), timeout=1)


@pytest.mark.asyncio
async def test_websocket_completion() -> None:
    # Ensure that the connecion callable returns on completion
    app = Quart(__name__)
    scope = {
        'headers': [(b'host', b'quart')],
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'wss',
        'path': '/',
        'query_string': b'',
        'extensions': {'websocket.http.response': {}},
    }
    connection = ASGIWebsocketConnection(app, scope)

    queue: asyncio.Queue = asyncio.Queue()
    queue.put_nowait({'type': 'websocket.connect'})

    async def receive() -> dict:
        # This will block after returning the first and only entry
        return await queue.get()

    async def send(message: dict) -> None:
        pass

    # This test fails if a timeout error is raised here
    await asyncio.wait_for(connection(receive, send), timeout=1)
