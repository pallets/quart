import asyncio
from typing import Optional

import pytest
from asynctest.mock import CoroutineMock

from quart import Quart
from quart.asgi import (
    _convert_version, _encode_headers, ASGIHTTPConnection, ASGIWebsocketConnection,
)
from quart.datastructures import Headers


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
    request = connection._create_request_from_scope(lambda: None)
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
        'subprotocols': [],
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


def test_http_path_from_absolute_target() -> None:
    app = Quart(__name__)
    scope = {
        'headers': [(b'host', b'quart')],
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'https',
        'path': 'http://quart/path',
        'query_string': b'',
    }
    connection = ASGIHTTPConnection(app, scope)
    request = connection._create_request_from_scope(lambda: None)
    assert request.path == '/path'


def test_websocket_path_from_absolute_target() -> None:
    app = Quart(__name__)
    scope = {
        'headers': [(b'host', b'quart')],
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'wss',
        'path': 'ws://quart/path',
        'query_string': b'',
        'subprotocols': [],
        'extensions': {'websocket.http.response': {}},
    }
    connection = ASGIWebsocketConnection(app, scope)
    websocket = connection._create_websocket_from_scope(lambda: None)
    assert websocket.path == '/path'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scope, headers, subprotocol, has_headers",
    [
        ({}, Headers(), None, False),
        ({}, Headers(), "abc", False),
        ({"asgi": {"spec_version": "2.1"}}, Headers({"a": "b"}), None, True),
        ({"asgi": {"spec_version": "2.1.1"}}, Headers({"a": "b"}), None, True),
    ],
)
async def test_websocket_accept_connection(
        scope: dict, headers: Headers, subprotocol: Optional[str], has_headers: bool,
) -> None:
    connection = ASGIWebsocketConnection(Quart(__name__), scope)
    mock_send = CoroutineMock()
    await connection.accept_connection(mock_send, headers, subprotocol)

    if has_headers:
        mock_send.assert_called_with({
            "subprotocol": subprotocol,
            "type": "websocket.accept",
            "headers": _encode_headers(headers),
        })
    else:
        mock_send.assert_called_with({
            "subprotocol": subprotocol,
            "type": "websocket.accept",
        })


@pytest.mark.asyncio
async def test_websocket_accept_connection_warns() -> None:
    connection = ASGIWebsocketConnection(Quart(__name__), {})

    async def mock_send(message: dict) -> None:
        pass

    with pytest.warns(None):
        await connection.accept_connection(mock_send, Headers({"a": "b"}), None)


def test__encode_headers() -> None:
    assert _encode_headers(Headers({"Foo": "Bar"})) == [(b"foo", b"Bar")]


def test__convert_version() -> None:
    assert _convert_version("2.1") == [2, 1]
