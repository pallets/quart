from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import NoReturn
from unittest.mock import AsyncMock

import pytest
from hypercorn.typing import HTTPScope
from hypercorn.typing import WebsocketScope
from werkzeug.datastructures import Headers
from werkzeug.exceptions import InternalServerError
from werkzeug.wrappers import Response as WerkzeugResponse

from quart.app import Quart
from quart.globals import session
from quart.globals import websocket
from quart.sessions import SecureCookieSession
from quart.sessions import SessionInterface
from quart.testing import no_op_push
from quart.testing import WebsocketResponseError
from quart.typing import ResponseReturnValue
from quart.typing import ResponseTypes
from quart.wrappers import Request
from quart.wrappers import Response

TEST_RESPONSE = Response("")


class SimpleError(Exception):
    pass


def test_endpoint_overwrite() -> None:
    app = Quart(__name__)

    def route() -> str:
        return ""

    def route2() -> str:
        return ""

    async def route3() -> str:
        return ""

    app.add_url_rule("/a", "index", route, methods=["GET"])
    app.add_url_rule(
        "/a/a", "index", route, methods=["GET"]
    )  # Should not assert, as same view func
    with pytest.raises(AssertionError):
        app.add_url_rule("/a/b", "index", route2, methods=["GET"])
    app.add_url_rule("/b", "async", route3, methods=["GET"])
    app.add_url_rule(
        "/b/a", "async", route3, methods=["GET"]
    )  # Should not assert, as same view func
    with pytest.raises(AssertionError):
        app.add_url_rule("/b/b", "async", route2, methods=["GET"])


@pytest.mark.parametrize(
    "methods, required_methods, automatic_options",
    [
        ({}, {}, False),
        ({}, {}, True),
        ({"GET", "PUT"}, {}, False),
        ({"GET", "PUT"}, {}, True),
        ({}, {"GET", "PUT"}, False),
        ({}, {"GET", "PUT"}, True),
    ],
)
def test_add_url_rule_methods(
    methods: set[str], required_methods: set[str], automatic_options: bool
) -> None:
    app = Quart(__name__)

    def route() -> str:
        return ""

    route.methods = methods  # type: ignore
    route.required_methods = required_methods  # type: ignore

    non_func_methods = {"PATCH"} if not methods else None
    app.add_url_rule(
        "/",
        "end",
        route,
        methods=non_func_methods,
        provide_automatic_options=automatic_options,
    )
    result = {"PATCH"} if not methods else set()
    result.update(methods)
    result.update(required_methods)
    if "GET" in result:
        result.add("HEAD")
    assert app.url_map._rules_by_endpoint["end"][0].methods == result


@pytest.mark.parametrize(
    "methods, arg_automatic, func_automatic, expected_methods, expected_automatic",
    [
        ({"GET"}, True, None, {"HEAD", "GET"}, True),
        ({"GET"}, None, None, {"HEAD", "GET", "OPTIONS"}, True),
        ({"GET"}, None, True, {"HEAD", "GET"}, True),
        ({"GET", "OPTIONS"}, None, None, {"HEAD", "GET", "OPTIONS"}, False),
        ({"GET"}, False, True, {"HEAD", "GET"}, False),
        ({"GET"}, None, False, {"HEAD", "GET"}, False),
    ],
)
def test_add_url_rule_automatic_options(
    methods: set[str],
    arg_automatic: bool | None,
    func_automatic: bool | None,
    expected_methods: set[str],
    expected_automatic: bool,
) -> None:
    app = Quart(__name__)

    def route() -> str:
        return ""

    route.provide_automatic_options = func_automatic  # type: ignore

    app.add_url_rule(
        "/", "end", route, methods=methods, provide_automatic_options=arg_automatic
    )
    assert app.url_map._rules_by_endpoint["end"][0].methods == expected_methods
    assert (
        app.url_map._rules_by_endpoint["end"][0].provide_automatic_options  # type: ignore
        == expected_automatic
    )


async def test_host_matching() -> None:
    app = Quart(__name__, static_host="quart.com", host_matching=True)

    @app.route("/", host="quart.com")
    async def route() -> str:
        return ""

    test_client = app.test_client()
    response = await test_client.get("/", headers={"host": "quart.com"})
    assert response.status_code == 200

    response = await test_client.get("/", headers={"host": "localhost"})
    assert response.status_code == 404


async def test_subdomain() -> None:
    app = Quart(__name__, subdomain_matching=True)
    app.config["SERVER_NAME"] = "quart.com"

    @app.route("/", subdomain="<subdomain>")
    async def route(subdomain: str) -> str:
        return subdomain

    test_client = app.test_client()
    response = await test_client.get("/", headers={"host": "sub.quart.com"})
    assert (await response.get_data(as_text=True)) == "sub"


@pytest.mark.parametrize(
    "result, expected, raises",
    [
        (None, None, True),
        ((None, 201), None, True),
        (TEST_RESPONSE, TEST_RESPONSE, False),
        (
            ("hello", {"X-Header": "bob"}),
            Response("hello", headers={"X-Header": "bob"}),
            False,
        ),
        (("hello", 201), Response("hello", 201), False),
        (
            ("hello", 201, {"X-Header": "bob"}),
            Response("hello", 201, headers={"X-Header": "bob"}),
            False,
        ),
        (
            (WerkzeugResponse("hello"), 201, {"X-Header": "bob"}),
            WerkzeugResponse("hello", 201, {"X-Header": "bob"}),
            False,
        ),
        (InternalServerError(), InternalServerError().get_response(), False),
        ((val for val in "abcd"), Response(val for val in "abcd"), False),
        (int, None, True),
    ],
)
async def test_make_response(
    result: ResponseReturnValue, expected: Response | WerkzeugResponse, raises: bool
) -> None:
    app = Quart(__name__)
    app.config["RESPONSE_TIMEOUT"] = None
    try:
        response = await app.make_response(result)
    except TypeError:
        if not raises:
            raise
    else:
        assert set(response.headers.keys()) == set(expected.headers.keys())
        assert response.status_code == expected.status_code
        if isinstance(response, Response):
            assert (await response.get_data()) == (await expected.get_data())  # type: ignore
        elif isinstance(response, WerkzeugResponse):
            assert response.get_data() == expected.get_data()


@pytest.fixture(name="basic_app")
def _basic_app() -> Quart:
    app = Quart(__name__)

    @app.route("/")
    def route() -> str:
        return ""

    @app.route("/exception/")
    def exception() -> str:
        raise Exception()

    return app


async def test_app_route_exception(basic_app: Quart) -> None:
    test_client = basic_app.test_client()
    response = await test_client.get("/exception/")
    assert response.status_code == 500


async def test_app_before_request_exception(basic_app: Quart) -> None:
    @basic_app.before_request
    def before() -> None:
        raise Exception()

    test_client = basic_app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 500


async def test_app_after_request_exception(basic_app: Quart) -> None:
    @basic_app.after_request
    def after(_: ResponseTypes) -> None:
        raise Exception()

    test_client = basic_app.test_client()
    response = await test_client.get("/")
    assert response.status_code == 500


async def test_app_after_request_handler_exception(basic_app: Quart) -> None:
    @basic_app.after_request
    def after(_: ResponseTypes) -> None:
        raise Exception()

    test_client = basic_app.test_client()
    response = await test_client.get("/exception/")
    assert response.status_code == 500


async def test_app_handle_request_asyncio_cancelled_error(
    http_scope: HTTPScope,
) -> None:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> NoReturn:
        raise asyncio.CancelledError()

    request = app.request_class(
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
    with pytest.raises(asyncio.CancelledError):
        await app.handle_request(request)


async def test_app_handle_websocket_asyncio_cancelled_error(
    websocket_scope: WebsocketScope,
) -> None:
    app = Quart(__name__)

    @app.websocket("/")
    async def index() -> NoReturn:
        raise asyncio.CancelledError()

    websocket = app.websocket_class(
        "/",
        b"",
        "wss",
        Headers([("host", "quart.com")]),
        "",
        "1.1",
        None,
        None,
        None,
        None,
        None,
        websocket_scope,
    )
    with pytest.raises(asyncio.CancelledError):
        await app.handle_websocket(websocket)


@pytest.fixture(name="session_app", scope="function")
def _session_app() -> Quart:
    app = Quart(__name__)
    app.session_interface = AsyncMock(spec=SessionInterface)
    app.session_interface.open_session.return_value = SecureCookieSession()
    app.session_interface.is_null_session.return_value = False

    @app.route("/")
    async def route() -> str:
        session["a"] = "b"
        return ""

    @app.websocket("/ws/")
    async def ws() -> None:
        session["a"] = "b"
        await websocket.accept()
        await websocket.send("")

    @app.websocket("/ws_return/")
    async def ws_return() -> str:
        session["a"] = "b"
        return ""

    return app


async def test_app_session(session_app: Quart) -> None:
    test_client = session_app.test_client()
    await test_client.get("/")
    session_app.session_interface.open_session.assert_called()  # type: ignore
    session_app.session_interface.save_session.assert_called()  # type: ignore


async def test_app_session_websocket(session_app: Quart) -> None:
    test_client = session_app.test_client()
    async with test_client.websocket("/ws/") as test_websocket:
        await test_websocket.receive()
    session_app.session_interface.open_session.assert_called()  # type: ignore
    session_app.session_interface.save_session.assert_called()  # type: ignore


async def test_app_session_websocket_return(session_app: Quart) -> None:
    test_client = session_app.test_client()
    async with test_client.websocket("/ws_return/") as test_websocket:
        with pytest.raises(WebsocketResponseError):
            await test_websocket.receive()
    session_app.session_interface.open_session.assert_called()  # type: ignore
    session_app.session_interface.save_session.assert_called()  # type: ignore


@pytest.mark.parametrize(
    "debug, testing, raises",
    [
        (False, False, False),
        (True, False, True),
        (False, True, True),
        (True, True, True),
    ],
)
async def test_propagation(
    debug: bool, testing: bool, raises: bool, http_scope: HTTPScope
) -> None:
    app = Quart(__name__)

    @app.route("/")
    async def exception() -> ResponseReturnValue:
        raise SimpleError()

    app.debug = debug
    app.testing = testing
    test_client = app.test_client()

    if raises:
        with pytest.raises(SimpleError):
            await app.handle_request(
                Request(
                    "GET",
                    "http",
                    "/",
                    b"",
                    Headers(),
                    "",
                    "1.1",
                    http_scope,
                    send_push_promise=no_op_push,
                )
            )
    else:
        response = await test_client.get("/")
        assert response.status_code == 500


async def test_test_app() -> None:
    startup = False
    shutdown = False
    serving = []

    app = Quart(__name__)

    @app.before_serving
    async def before() -> None:
        nonlocal startup
        startup = True

    @app.after_serving
    async def after() -> None:
        nonlocal shutdown
        shutdown = True

    @app.while_serving
    async def lifespan() -> AsyncGenerator[None, None]:
        nonlocal serving
        serving.append(1)
        yield
        serving.append(2)

    @app.route("/")
    async def index() -> str:
        return ""

    async with app.test_app() as test_app:
        assert startup
        test_client = test_app.test_client()
        await test_client.get("/")
        assert not shutdown
        assert serving == [1]
    assert shutdown
    assert serving == [1, 2]
