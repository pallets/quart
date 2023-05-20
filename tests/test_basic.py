from __future__ import annotations

from typing import AsyncGenerator, cast

import pytest
from werkzeug.wrappers import Response as WerkzeugResponse

from quart import abort, jsonify, Quart, request, Response, ResponseReturnValue, url_for, websocket
from quart.testing import WebsocketResponseError


@pytest.fixture
def app() -> Quart:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> ResponseReturnValue:
        return "index"

    @app.route("/❤️")
    async def iri() -> ResponseReturnValue:
        return "💔"

    @app.route("/sync/")
    def sync() -> ResponseReturnValue:
        return "index"

    @app.route("/json/", methods=["POST"])
    async def json() -> ResponseReturnValue:
        data = await request.get_json()
        return jsonify(data)

    @app.route("/implicit_json/", methods=["POST"])
    async def implicit_json() -> ResponseReturnValue:
        data = await request.get_json()
        return data

    @app.route("/werkzeug/")
    async def werkzeug() -> ResponseReturnValue:
        return WerkzeugResponse(b"Hello")

    @app.route("/error/")
    async def error() -> ResponseReturnValue:
        abort(409)
        return "OK"

    @app.route("/param/<value>")
    async def param(value: str) -> ResponseReturnValue:
        return value

    @app.route("/stream")
    async def stream() -> ResponseReturnValue:
        async def _gen() -> AsyncGenerator[str, None]:
            yield "Hello "
            yield "World"

        return _gen()

    @app.errorhandler(409)
    async def generic_http_handler(_: Exception) -> ResponseReturnValue:
        return "Something Unique", 409

    @app.errorhandler(404)
    async def not_found_handler(_: Exception) -> ResponseReturnValue:
        return "Not Found", 404

    @app.websocket("/ws/")
    async def ws() -> None:
        # async for message in websocket:
        while True:
            message = await websocket.receive()
            await websocket.send(message)

    @app.websocket("/ws/abort/")
    async def ws_abort() -> None:
        abort(401)

    return app


@pytest.mark.parametrize("path", ["/", "/sync/"])
async def test_index(path: str, app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get(path)
    assert response.status_code == 200
    assert b"index" in (await response.get_data())  # type: ignore


async def test_iri(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get("/❤️")
    assert "💔".encode() in (await response.get_data())  # type: ignore


async def test_options(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.options("/")
    assert response.status_code == 200
    assert {method.strip() for method in response.headers["Allow"].split(",")} == {
        "HEAD",
        "OPTIONS",
        "GET",
    }


async def test_json(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.post("/json/", json={"value": "json"})
    assert response.status_code == 200
    assert b'{"value":"json"}\n' == (await response.get_data())  # type: ignore


async def test_implicit_json(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.post("/implicit_json/", json={"value": "json"})
    assert response.status_code == 200
    assert b'{"value":"json"}\n' == (await response.get_data())  # type: ignore


async def test_implicit_json_list(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.post("/implicit_json/", json=["a", 2])
    assert response.status_code == 200
    assert b'["a",2]\n' == (await response.get_data())  # type: ignore


async def test_werkzeug(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get("/werkzeug/")
    assert response.status_code == 200
    assert b"Hello" == (await response.get_data())  # type: ignore


async def test_generic_error(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get("/error/")
    assert response.status_code == 409
    assert b"Something Unique" in (await response.get_data())  # type: ignore


async def test_url_defaults(app: Quart) -> None:
    @app.url_defaults
    def defaults(_: str, values: dict) -> None:
        values["value"] = "hello"

    async with app.test_request_context("/"):
        assert url_for("param") == "/param/hello"


async def test_not_found_error(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get("/not_found/")
    assert response.status_code == 404
    assert b"Not Found" in (await response.get_data())  # type: ignore


async def test_make_response_str(app: Quart) -> None:
    response = await app.make_response("Result")
    assert response.status_code == 200
    assert (await response.get_data()) == b"Result"  # type: ignore

    response = await app.make_response(("Result", 200))
    response = await app.make_response(("Result", {"name": "value"}))
    assert response.status_code == 200
    assert (await response.get_data()) == b"Result"  # type: ignore
    assert response.headers["name"] == "value"

    response = await app.make_response(("Result", 404, {"name": "value"}))
    assert response.status_code == 404
    assert (await response.get_data()) == b"Result"  # type: ignore
    assert response.headers["name"] == "value"


async def test_make_response_response(app: Quart) -> None:
    response = await app.make_response(Response("Result"))
    assert response.status_code == 200
    assert (await response.get_data()) == b"Result"  # type: ignore

    response = await app.make_response((Response("Result"), {"name": "value"}))
    assert response.status_code == 200
    assert (await response.get_data()) == b"Result"  # type: ignore
    assert response.headers["name"] == "value"

    response = await app.make_response((Response("Result"), 404, {"name": "value"}))
    assert response.status_code == 404
    assert (await response.get_data()) == b"Result"  # type: ignore
    assert response.headers["name"] == "value"


async def test_make_response_errors(app: Quart) -> None:
    with pytest.raises(TypeError):
        await app.make_response(("Result", {"name": "value"}, 200))  # type: ignore
    with pytest.raises(TypeError):
        await app.make_response(("Result", {"name": "value"}, 200, "a"))  # type: ignore
    with pytest.raises(TypeError):
        await app.make_response(("Result",))  # type: ignore


async def test_websocket(app: Quart) -> None:
    test_client = app.test_client()
    data = b"bob"
    async with test_client.websocket("/ws/") as test_websocket:
        await test_websocket.send(data)
        result = await test_websocket.receive()
    assert cast(bytes, result) == data


async def test_websocket_abort(app: Quart) -> None:
    test_client = app.test_client()
    try:
        async with test_client.websocket("/ws/abort/") as test_websocket:
            await test_websocket.receive()
    except WebsocketResponseError as error:
        assert error.response.status_code == 401


async def test_root_path(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get("/", root_path="/bob")
    assert response.status_code == 404
    response = await test_client.get("/bob/", root_path="/bob")
    assert response.status_code == 200


async def test_stream(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get("/stream")
    assert (await response.get_data()) == b"Hello World"  # type: ignore
