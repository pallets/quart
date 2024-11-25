from __future__ import annotations

from io import BytesIO
from typing import Callable

import pytest
from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response as WerkzeugResponse

from quart import jsonify
from quart import Quart
from quart import redirect
from quart import request
from quart import Response
from quart import session
from quart import websocket
from quart.datastructures import FileStorage
from quart.testing import make_test_body_with_headers
from quart.testing import make_test_headers_path_and_query_string
from quart.testing import make_test_scope
from quart.testing import QuartClient as Client
from quart.testing import WebsocketResponseError


async def test_methods() -> None:
    app = Quart(__name__)

    methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "TRACE"]

    @app.route("/", methods=methods)
    async def echo() -> str:
        return request.method

    client = Client(app)

    for method in methods:
        func = getattr(client, method.lower())
        response = await func("/")
        assert method in (await response.get_data(as_text=True))


@pytest.mark.parametrize(
    (
        "path",
        "query_string",
        "subdomain",
        "expected_path",
        "expected_query_string",
        "expected_host",
    ),
    [
        ("/path", {"a": "b"}, None, "/path", b"a=b", "localhost"),
        ("/path", {"a": ["b", "c"]}, None, "/path", b"a=b&a=c", "localhost"),
        ("/path?b=c", None, None, "/path", b"b=c", "localhost"),
        ("/path%20", None, None, "/path ", b"", "localhost"),
        ("/path", None, "api", "/path", b"", "api.localhost"),
    ],
)
def test_build_headers_path_and_query_string(
    path: str,
    query_string: dict | None,
    subdomain: str | None,
    expected_path: str,
    expected_query_string: bytes,
    expected_host: str,
) -> None:
    headers, result_path, result_qs = make_test_headers_path_and_query_string(
        Quart(__name__), path, None, query_string, None, subdomain
    )
    assert result_path == expected_path
    assert headers["User-Agent"] == "Quart"
    assert headers["host"] == expected_host
    assert result_qs == expected_query_string


def test_build_headers_path_and_query_string_with_query_string_error() -> None:
    with pytest.raises(ValueError):
        make_test_headers_path_and_query_string(
            Quart(__name__), "/?a=b", None, {"c": "d"}
        )


def test_build_headers_path_and_query_string_with_auth() -> None:
    headers, *_ = make_test_headers_path_and_query_string(
        Quart(__name__),
        "/",
        None,
        None,
        ("user", "pass"),
    )
    assert headers["Authorization"] == "Basic dXNlcjpwYXNz"


def test_make_test_body_with_headers_data() -> None:
    body, headers = make_test_body_with_headers(data="data")
    assert body == b"data"
    assert headers == Headers()


def test_make_test_body_with_headers_form() -> None:
    body, headers = make_test_body_with_headers(form={"a": "b"})
    assert body == b"a=b"
    assert headers == Headers({"Content-Type": "application/x-www-form-urlencoded"})


def test_make_test_body_with_headers_files() -> None:
    body, headers = make_test_body_with_headers(
        files={"a": FileStorage(BytesIO(b"abc"), filename="Quart")}
    )
    assert body == (
        b'\r\n------QuartBoundary\r\nContent-Disposition: form-data; name="a"; '
        b'filename="Quart"\r\n\r\nabc\r\n------QuartBoundary--\r\n'
    )
    assert headers == Headers(
        {"Content-Type": "multipart/form-data; boundary=----QuartBoundary"}
    )


def test_make_test_body_with_headers_form_and_files() -> None:
    body, headers = make_test_body_with_headers(
        form={"b": "c"}, files={"a": FileStorage(BytesIO(b"abc"), filename="Quart")}
    )
    assert body == (
        b'\r\n------QuartBoundary\r\nContent-Disposition: form-data; name="a"; '
        b'filename="Quart"\r\n\r\nabc\r\n------QuartBoundary\r\n'
        b'Content-Disposition: form-data; name="b"\r\n\r\nc\r\n'
        b"------QuartBoundary--\r\n"
    )
    assert headers == Headers(
        {"Content-Type": "multipart/form-data; boundary=----QuartBoundary"}
    )


def test_make_test_body_with_headers_json() -> None:
    body, headers = make_test_body_with_headers(json={"a": "b"})
    assert body == b'{"a": "b"}'
    assert headers == Headers({"Content-Type": "application/json"})


def test_make_test_body_with_headers_argument_error() -> None:
    with pytest.raises(ValueError):
        make_test_body_with_headers(json={}, data="", form={}, files={})
    make_test_body_with_headers(form={}, files={})


@pytest.mark.parametrize(
    "path, expected_raw_path",
    [
        ("/", b"/"),
        ("/❤️", b"/%E2%9D%A4%EF%B8%8F"),
    ],
)
def test_make_test_scope_with_scope_base(path: str, expected_raw_path: bytes) -> None:
    scope = make_test_scope(
        "http",
        path,
        "GET",
        Headers(),
        b"",
        "http",
        "",
        "1.1",
        {"client": ("127.0.0.2", "1234")},
    )
    assert scope == {
        "type": "http",
        "http_version": "1.1",
        "asgi": {"spec_version": "2.1"},
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": expected_raw_path,
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "extensions": {},
        "_quart._preserve_context": False,
        "client": ("127.0.0.2", "1234"),
    }


@pytest.mark.parametrize(
    "headers, expected",
    [
        (None, Headers({"User-Agent": "Quart", "host": "localhost"})),
        (
            Headers({"User-Agent": "Quarty", "host": "quart.com"}),
            Headers({"User-Agent": "Quarty", "host": "quart.com"}),
        ),
    ],
)
def test_build_headers_path_and_query_string_headers_defaults(
    headers: Headers, expected: Headers
) -> None:
    result, path, query_string = make_test_headers_path_and_query_string(
        Quart(__name__), "/path", headers
    )
    assert result == expected
    assert path == "/path"
    assert query_string == b""


async def test_remote_addr() -> None:
    app = Quart(__name__)

    @app.route("/")
    async def echo() -> str:
        return request.remote_addr

    client = Client(app)
    response = await client.get("/", scope_base={"client": ("127.0.0.2", "1234")})
    assert (await response.get_data(as_text=True)) == "127.0.0.2"


async def test_json() -> None:
    app = Quart(__name__)

    @app.route("/", methods=["POST"])
    async def echo() -> Response:
        data = await request.get_json()
        return jsonify(data)

    client = Client(app)
    response = await client.post("/", json={"a": "b"})
    assert (await response.get_json()) == {"a": "b"}


async def test_form() -> None:
    app = Quart(__name__)

    @app.route("/", methods=["POST"])
    async def echo() -> Response:
        data = await request.form
        return jsonify(**data)

    client = Client(app)
    response = await client.post("/", form={"a": "b"})
    assert (await response.get_json()) == {"a": "b"}


async def test_files() -> None:
    app = Quart(__name__)

    @app.route("/", methods=["POST"])
    async def echo() -> Response:
        files = await request.files
        data = files["file"].read()
        return data

    client = Client(app)
    response = await client.post(
        "/", files={"file": FileStorage(BytesIO(b"bar"), filename="a.txt")}
    )
    assert (await response.get_data(as_text=True)) == "bar"


async def test_data() -> None:
    app = Quart(__name__)

    @app.route("/", methods=["POST"])
    async def echo() -> str:
        data = await request.get_data(as_text=True)
        return data  # type: ignore

    client = Client(app)
    headers = {"Content-Type": "application/octet-stream"}
    response = await client.post("/", data=b"ABCDEFG", headers=headers)
    assert (await response.get_data(as_text=False)) == b"ABCDEFG"


async def test_query_string() -> None:
    app = Quart(__name__)

    @app.route("/", methods=["GET"])
    async def echo() -> Response:
        data = request.args
        return jsonify(**data)

    client = Client(app)
    response = await client.get("/", query_string={"a": "b"})
    assert (await response.get_json()) == {"a": "b"}


async def test_redirect() -> None:
    app = Quart(__name__)

    @app.route("/", methods=["GET"])
    async def echo() -> str:
        return request.method

    @app.route("/redirect", methods=["GET"])
    async def redir() -> WerkzeugResponse:
        return redirect("/")

    client = Client(app)
    assert (await client.get("/redirect", follow_redirects=True)).status_code == 200


async def test_cookie_jar() -> None:
    app = Quart(__name__)
    app.secret_key = "secret"

    @app.route("/", methods=["GET"])
    async def echo() -> Response:
        foo = session.get("foo")
        bar = request.cookies.get("bar")
        session["foo"] = "bar"
        response = jsonify({"foo": foo, "bar": bar})
        response.set_cookie("bar", "foo")
        return response

    client = Client(app)
    response = await client.get("/")
    assert (await response.get_json()) == {"foo": None, "bar": None}
    response = await client.get("/")
    assert (await response.get_json()) == {"foo": "bar", "bar": "foo"}


async def test_redirect_cookie_jar() -> None:
    app = Quart(__name__)
    app.secret_key = "secret"

    @app.route("/a")
    async def a() -> WerkzeugResponse:
        response = redirect("/b")
        response.set_cookie("bar", "foo")
        return response

    @app.route("/b")
    async def echo() -> Response:
        bar = request.cookies.get("bar")
        response = jsonify({"bar": bar})
        return response

    client = Client(app)
    response = await client.get("/a", follow_redirects=True)
    assert (await response.get_json()) == {"bar": "foo"}


async def test_set_cookie() -> None:
    app = Quart(__name__)

    @app.route("/", methods=["GET"])
    async def echo() -> Response:
        return jsonify({"foo": request.cookies.get("foo")})

    client = Client(app)
    client.set_cookie("localhost", "foo", "bar")
    response = await client.get("/")
    assert (await response.get_json()) == {"foo": "bar"}


async def test_websocket_bad_request() -> None:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> str:
        return ""

    test_client = app.test_client()
    with pytest.raises(WebsocketResponseError):
        async with test_client.websocket("/"):
            pass


async def test_push_promise() -> None:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> str:
        await request.send_push_promise("/")
        return ""

    test_client = app.test_client()
    await test_client.get("/", http_version="2")
    assert test_client.push_promises[0][0] == "/"


async def test_session_transactions() -> None:
    app = Quart(__name__)
    app.secret_key = "secret"

    @app.route("/")
    async def index() -> str:
        return str(session["foo"])

    test_client = app.test_client()

    async with test_client.session_transaction() as local_session:
        assert len(local_session) == 0
        local_session["foo"] = [42]
        assert len(local_session) == 1
    response = await test_client.get("/")
    assert (await response.get_data()) == b"[42]"
    async with test_client.session_transaction() as local_session:
        assert len(local_session) == 1
        assert local_session["foo"] == [42]


async def test_with_usage() -> None:
    app = Quart(__name__)
    app.secret_key = "secret"

    @app.route("/")
    async def index() -> str:
        session["hello"] = "world"
        return "Hello"

    async with app.test_client() as client:
        await client.get("/")
        assert request.method == "GET"
        assert session["hello"] == "world"


async def test_websocket_json() -> None:
    app = Quart(__name__)

    @app.websocket("/ws/")
    async def ws() -> None:
        data = await websocket.receive_json()
        await websocket.send_json(data)

    async with app.test_client().websocket("/ws/") as test_websocket:
        await test_websocket.send_json({"foo": "bar"})
        data = await test_websocket.receive_json()
        assert data == {"foo": "bar"}


async def test_middleware() -> None:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> str:
        return "Hello"

    class OddMiddleware:
        def __init__(self, app: Callable) -> None:
            self.app = app

        async def __call__(
            self, scope: dict, receive: Callable, send: Callable
        ) -> None:
            if scope["path"] != "/":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-length", b"0")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b"",
                        "more_body": False,
                    }
                )
            else:
                await self.app(scope, receive, send)

    app.asgi_app = OddMiddleware(app.asgi_app)  # type: ignore

    client = app.test_client()
    response = await client.get("/")
    assert response.status_code == 200
    response = await client.get("/odd")
    assert response.status_code == 401


async def test_auth() -> None:
    app = Quart(__name__)

    @app.get("/")
    async def echo() -> str:
        return f"{request.authorization.username}:{request.authorization.password}"

    client = Client(app)

    response = await client.get("/", auth=("user", "pass"))
    assert (await response.get_data(as_text=True)) == "user:pass"
