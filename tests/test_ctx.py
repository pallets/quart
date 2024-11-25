from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import Mock

import pytest
from hypercorn.typing import HTTPScope
from werkzeug.datastructures import Headers
from werkzeug.exceptions import BadRequest

from quart.app import Quart
from quart.ctx import after_this_request
from quart.ctx import AppContext
from quart.ctx import copy_current_app_context
from quart.ctx import copy_current_request_context
from quart.ctx import copy_current_websocket_context
from quart.ctx import has_app_context
from quart.ctx import has_request_context
from quart.ctx import RequestContext
from quart.globals import g
from quart.globals import request
from quart.globals import websocket
from quart.routing import QuartRule
from quart.testing import make_test_headers_path_and_query_string
from quart.testing import no_op_push
from quart.wrappers import Request


async def test_request_context_match(http_scope: HTTPScope) -> None:
    app = Quart(__name__)
    url_adapter = Mock()
    rule = QuartRule("/", methods={"GET"}, endpoint="index")
    url_adapter.match.return_value = (rule, {"arg": "value"})
    app.create_url_adapter = lambda *_: url_adapter  # type: ignore
    request = Request(
        "GET",
        "http",
        "/",
        b"",
        Headers([("host", "quart.com")]),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    async with RequestContext(app, request):
        assert request.url_rule == rule
        assert request.view_args == {"arg": "value"}


async def test_bad_request_if_websocket_route(http_scope: HTTPScope) -> None:
    app = Quart(__name__)
    url_adapter = Mock()
    url_adapter.match.side_effect = BadRequest()
    app.create_url_adapter = lambda *_: url_adapter  # type: ignore
    request = Request(
        "GET",
        "http",
        "/",
        b"",
        Headers([("host", "quart.com")]),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    async with RequestContext(app, request):
        assert isinstance(request.routing_exception, BadRequest)


async def test_after_this_request(http_scope: HTTPScope) -> None:
    app = Quart(__name__)
    headers, path, query_string = make_test_headers_path_and_query_string(app, "/")
    async with RequestContext(
        Quart(__name__),
        Request(
            "GET",
            "http",
            path,
            query_string,
            headers,
            "",
            "1.1",
            http_scope,
            send_push_promise=no_op_push,
        ),
    ) as context:
        after_this_request(lambda: "hello")  # type: ignore
        assert context._after_request_functions[0]() == "hello"  # type: ignore


async def test_has_request_context(http_scope: HTTPScope) -> None:
    app = Quart(__name__)
    headers, path, query_string = make_test_headers_path_and_query_string(app, "/")
    request = Request(
        "GET",
        "http",
        path,
        query_string,
        headers,
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    async with RequestContext(Quart(__name__), request):
        assert has_request_context() is True
        assert has_app_context() is True
    assert has_request_context() is False
    assert has_app_context() is False


async def test_has_app_context() -> None:
    async with AppContext(Quart(__name__)):
        assert has_app_context() is True
    assert has_app_context() is False


async def test_copy_current_app_context() -> None:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> str:
        g.foo = "bar"

        @copy_current_app_context
        async def within_context() -> None:
            assert g.foo == "bar"

        await asyncio.ensure_future(within_context())
        return ""

    test_client = app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 200


def test_copy_current_app_context_error() -> None:
    with pytest.raises(RuntimeError):
        copy_current_app_context(lambda: None)()


async def test_copy_current_request_context() -> None:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> str:
        @copy_current_request_context
        async def within_context() -> None:
            assert request.path == "/"

        await asyncio.ensure_future(within_context())
        return ""

    test_client = app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 200


def test_copy_current_request_context_error() -> None:
    with pytest.raises(RuntimeError):
        copy_current_request_context(lambda: None)()


async def test_works_without_copy_current_request_context() -> None:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> str:
        async def within_context() -> None:
            assert request.path == "/"

        await asyncio.ensure_future(within_context())
        return ""

    test_client = app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 200


async def test_copy_current_websocket_context() -> None:
    app = Quart(__name__)

    @app.websocket("/")
    async def index() -> None:
        @copy_current_websocket_context
        async def within_context() -> str:
            return websocket.path

        data = await asyncio.ensure_future(within_context())
        await websocket.send(data.encode())

    test_client = app.test_client()
    async with test_client.websocket("/") as test_websocket:
        data = await test_websocket.receive()
    assert cast(bytes, data) == b"/"


def test_copy_current_websocket_context_error() -> None:
    with pytest.raises(RuntimeError):
        copy_current_websocket_context(lambda: None)()
