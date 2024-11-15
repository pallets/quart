from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from hypercorn.typing import ASGIReceiveEvent
from hypercorn.typing import ASGISendEvent
from hypercorn.typing import HTTPScope
from hypercorn.typing import WebsocketScope
from werkzeug.datastructures import Headers

from quart import Quart
from quart.asgi import _convert_version
from quart.asgi import _handle_exception
from quart.asgi import ASGIHTTPConnection
from quart.asgi import ASGIWebsocketConnection
from quart.utils import encode_headers


@pytest.mark.parametrize(
    "headers, expected", [([(b"host", b"quart")], "quart"), ([], "")]
)
async def test_http_1_0_host_header(headers: list, expected: str) -> None:
    app = Quart(__name__)
    scope: HTTPScope = {
        "type": "http",
        "asgi": {},
        "http_version": "1.0",
        "method": "GET",
        "scheme": "https",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 80),
        "server": None,
        "extensions": {},
        "state": {},  # type: ignore[typeddict-item]
    }
    connection = ASGIHTTPConnection(app, scope)
    request = connection._create_request_from_scope(lambda: None)  # type: ignore
    assert request.headers["host"] == expected


async def test_http_completion() -> None:
    # Ensure that the connecion callable returns on completion
    app = Quart(__name__)
    scope: HTTPScope = {
        "type": "http",
        "asgi": {},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"quart")],
        "client": ("127.0.0.1", 80),
        "server": None,
        "extensions": {},
        "state": {},  # type: ignore[typeddict-item]
    }
    connection = ASGIHTTPConnection(app, scope)

    queue: asyncio.Queue = asyncio.Queue()
    queue.put_nowait({"type": "http.request", "body": b"", "more_body": False})

    async def receive() -> ASGIReceiveEvent:
        # This will block after returning the first and only entry
        return await queue.get()

    async def send(message: ASGISendEvent) -> None:
        pass

    # This test fails if a timeout error is raised here
    await asyncio.wait_for(connection(receive, send), timeout=1)


@pytest.mark.parametrize(
    "request_message",
    [
        {"type": "http.request", "body": b"", "more_body": False},
        {"type": "http.request", "more_body": False},
    ],
)
async def test_http_request_without_body(request_message: dict) -> None:
    app = Quart(__name__)

    scope: HTTPScope = {
        "type": "http",
        "asgi": {},
        "http_version": "1.0",
        "method": "GET",
        "scheme": "https",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"quart")],
        "client": ("127.0.0.1", 80),
        "server": None,
        "extensions": {},
        "state": {},  # type: ignore[typeddict-item]
    }
    connection = ASGIHTTPConnection(app, scope)
    request = connection._create_request_from_scope(lambda: None)  # type: ignore

    queue: asyncio.Queue = asyncio.Queue()
    queue.put_nowait(request_message)

    async def receive() -> ASGIReceiveEvent:
        # This will block after returning the first and only entry
        return await queue.get()

    # This test fails with a timeout error if the request body is not received
    # within 1 second
    receiver_task = asyncio.ensure_future(connection.handle_messages(request, receive))
    body = await asyncio.wait_for(request.body, timeout=1)
    receiver_task.cancel()

    assert body == b""


async def test_websocket_completion() -> None:
    # Ensure that the connecion callable returns on completion
    app = Quart(__name__)
    scope: WebsocketScope = {
        "type": "websocket",
        "asgi": {},
        "http_version": "1.1",
        "scheme": "wss",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"quart")],
        "client": ("127.0.0.1", 80),
        "server": None,
        "subprotocols": [],
        "extensions": {"websocket.http.response": {}},
        "state": {},  # type: ignore[typeddict-item]
    }
    connection = ASGIWebsocketConnection(app, scope)

    queue: asyncio.Queue = asyncio.Queue()
    queue.put_nowait({"type": "websocket.connect"})

    async def receive() -> ASGIReceiveEvent:
        # This will block after returning the first and only entry
        return await queue.get()

    async def send(message: ASGISendEvent) -> None:
        pass

    # This test fails if a timeout error is raised here
    await asyncio.wait_for(connection(receive, send), timeout=1)


def test_http_path_from_absolute_target() -> None:
    app = Quart(__name__)
    scope: HTTPScope = {
        "type": "http",
        "asgi": {},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "http://quart/path",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"quart")],
        "client": ("127.0.0.1", 80),
        "server": None,
        "extensions": {},
        "state": {},  # type: ignore[typeddict-item]
    }
    connection = ASGIHTTPConnection(app, scope)
    request = connection._create_request_from_scope(lambda: None)  # type: ignore
    assert request.path == "/path"


@pytest.mark.parametrize(
    "path, expected",
    [("/app", "/ "), ("/", "/ "), ("/app/", "/"), ("/app/2", "/2")],
)
def test_http_path_with_root_path(path: str, expected: str) -> None:
    app = Quart(__name__)
    scope: HTTPScope = {
        "type": "http",
        "asgi": {},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": path,
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "/app",
        "headers": [(b"host", b"quart")],
        "client": ("127.0.0.1", 80),
        "server": None,
        "extensions": {},
        "state": {},  # type: ignore[typeddict-item]
    }
    connection = ASGIHTTPConnection(app, scope)
    request = connection._create_request_from_scope(lambda: None)  # type: ignore
    assert request.path == expected


def test_websocket_path_from_absolute_target() -> None:
    app = Quart(__name__)
    scope: WebsocketScope = {
        "type": "websocket",
        "asgi": {},
        "http_version": "1.1",
        "scheme": "wss",
        "path": "ws://quart/path",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"quart")],
        "client": ("127.0.0.1", 80),
        "server": None,
        "subprotocols": [],
        "extensions": {"websocket.http.response": {}},
        "state": {},  # type: ignore[typeddict-item]
    }
    connection = ASGIWebsocketConnection(app, scope)
    websocket = connection._create_websocket_from_scope(lambda: None)  # type: ignore
    assert websocket.path == "/path"


@pytest.mark.parametrize(
    "path, expected",
    [("/app", "/ "), ("/", "/ "), ("/app/", "/"), ("/app/2", "/2")],
)
def test_websocket_path_with_root_path(path: str, expected: str) -> None:
    app = Quart(__name__)
    scope: WebsocketScope = {
        "type": "websocket",
        "asgi": {},
        "http_version": "1.1",
        "scheme": "wss",
        "path": path,
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "/app",
        "headers": [(b"host", b"quart")],
        "client": ("127.0.0.1", 80),
        "server": None,
        "subprotocols": [],
        "extensions": {"websocket.http.response": {}},
        "state": {},  # type: ignore[typeddict-item]
    }
    connection = ASGIWebsocketConnection(app, scope)
    websocket = connection._create_websocket_from_scope(lambda: None)  # type: ignore
    assert websocket.path == expected


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
    scope: dict, headers: Headers, subprotocol: str | None, has_headers: bool
) -> None:
    connection = ASGIWebsocketConnection(Quart(__name__), scope)  # type: ignore
    mock_send = AsyncMock()
    await connection.accept_connection(mock_send, headers, subprotocol)

    if has_headers:
        mock_send.assert_called_with(
            {
                "subprotocol": subprotocol,
                "type": "websocket.accept",
                "headers": encode_headers(headers),
            }
        )
    else:
        mock_send.assert_called_with(
            {"headers": [], "subprotocol": subprotocol, "type": "websocket.accept"}
        )


async def test_websocket_accept_connection_warns(
    websocket_scope: WebsocketScope,
) -> None:
    connection = ASGIWebsocketConnection(Quart(__name__), websocket_scope)

    async def mock_send(message: ASGISendEvent) -> None:
        pass

    with pytest.warns(UserWarning):
        await connection.accept_connection(mock_send, Headers({"a": "b"}), None)


def test__convert_version() -> None:
    assert _convert_version("2.1") == [2, 1]


def test_http_asgi_scope_from_request() -> None:
    app = Quart(__name__)
    scope = {
        "headers": [(b"host", b"quart")],
        "http_version": "1.0",
        "method": "GET",
        "scheme": "https",
        "path": "/",
        "query_string": b"",
        "test_result": "PASSED",
    }
    connection = ASGIHTTPConnection(app, scope)  # type: ignore
    request = connection._create_request_from_scope(lambda: None)  # type: ignore
    assert request.scope["test_result"] == "PASSED"  # type: ignore


@pytest.mark.parametrize(
    "propagate_exceptions, testing, raises",
    [
        (True, False, False),
        (True, True, True),
        (False, True, True),
        (False, False, True),
    ],
)
async def test__handle_exception(
    propagate_exceptions: bool, testing: bool, raises: bool
) -> None:
    app = Mock()
    app.config = {}
    app.config["PROPAGATE_EXCEPTIONS"] = propagate_exceptions
    app.testing = testing

    if raises:
        with pytest.raises(ValueError):
            await _handle_exception(app, ValueError())
    else:
        await _handle_exception(app, ValueError())
