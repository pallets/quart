from __future__ import annotations

import asyncio
from urllib.parse import urlencode

import pytest
from hypercorn.typing import HTTPScope
from werkzeug.datastructures import Headers
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.exceptions import RequestTimeout

from quart import Quart
from quart import request
from quart.testing import no_op_push
from quart.wrappers.request import Body
from quart.wrappers.request import Request


async def _fill_body(body: Body, semaphore: asyncio.Semaphore, limit: int) -> None:
    for number in range(limit):
        await body.put(b"%d" % number)
        await semaphore.acquire()
    body.set_complete()


async def test_full_body() -> None:
    body = Body(None, None)
    limit = 3
    semaphore = asyncio.Semaphore(limit)
    asyncio.ensure_future(_fill_body(body, semaphore, limit))
    assert b"012" == await body


async def test_body_streaming() -> None:
    body = Body(None, None)
    limit = 3
    semaphore = asyncio.Semaphore(0)
    asyncio.ensure_future(_fill_body(body, semaphore, limit))
    index = 0
    result = []
    async for data in body:
        semaphore.release()
        result.append(data)
        index += 1
    assert result == [b"0", b"1", b"2", b""]
    assert b"" == await body


async def test_body_stream_single_chunk() -> None:
    body = Body(None, None)
    body.set_result(b"data")

    async def _check_data() -> None:
        async for data in body:
            assert data == b"data"

    await asyncio.wait_for(_check_data(), 1)


async def test_body_streaming_no_data() -> None:
    body = Body(None, None)
    semaphore = asyncio.Semaphore(0)
    asyncio.ensure_future(_fill_body(body, semaphore, 0))
    async for data in body:
        assert data == b""
    assert b"" == await body


async def test_body_exceeds_max_content_length() -> None:
    max_content_length = 5
    body = Body(None, max_content_length)
    semaphore = asyncio.Semaphore(max_content_length + 1)
    asyncio.ensure_future(_fill_body(body, semaphore, max_content_length + 1))
    with pytest.raises(RequestEntityTooLarge):
        await body


async def test_request_exceeds_max_content_length(http_scope: HTTPScope) -> None:
    max_content_length = 5
    headers = Headers()
    headers["Content-Length"] = str(max_content_length + 1)
    request = Request(
        "POST",
        "http",
        "/",
        b"",
        headers,
        "",
        "1.1",
        http_scope,
        max_content_length=max_content_length,
        send_push_promise=no_op_push,
    )
    with pytest.raises(RequestEntityTooLarge):
        await request.get_data()


@pytest.mark.parametrize("read_mode", ["body", "get_data", "stream", "form"])
@pytest.mark.parametrize("with_content_length", [False, True])
@pytest.mark.parametrize(
    "limit, payload, expected_status",
    [
        (None, b"a=1234", 200),
        (0, b"a=1", 413),
        (2, b"a=1", 413),
        (6, b"a=1234", 200),
        (8, b"a=1234", 200),
    ],
)
async def test_request_max_content_length_override(
    read_mode: str,
    with_content_length: bool,
    limit: int | None,
    payload: bytes,
    expected_status: int,
) -> None:
    app = Quart(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4

    @app.put("/")
    async def upload() -> dict:
        request.max_content_length = limit
        if read_mode == "stream":
            data = b"".join([chunk async for chunk in request.body])
        elif read_mode == "form":
            data = f"a={(await request.form)['a']}".encode()
        elif read_mode == "get_data":
            data = await request.get_data(
                cache=True, as_text=False, parse_form_data=False
            )
        else:
            data = await request.body
        return {"data": data.decode(), "limit": request.max_content_length}

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if with_content_length:
        headers["Content-Length"] = str(len(payload))

    async with app.test_client().request(
        "/", method="PUT", headers=headers
    ) as connection:
        for byte in payload:
            await connection.send(bytes([byte]))
        await connection.send_complete()

    response = await connection.as_response()
    if read_mode == "stream" and not with_content_length:
        expected_status = 200
    assert response.status_code == expected_status
    if expected_status == 200:
        assert await response.get_json() == {"data": payload.decode(), "limit": limit}
    assert app.config["MAX_CONTENT_LENGTH"] == 4


@pytest.mark.parametrize("limit", [None, 1024])
@pytest.mark.parametrize("with_content_length", [False, True])
async def test_request_max_content_length_multipart(
    limit: int | None, with_content_length: bool
) -> None:
    app = Quart(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4

    @app.put("/")
    async def upload() -> dict:
        request.max_content_length = limit
        return dict(await request.form)

    payload = (
        b'--boundary\r\nContent-Disposition: form-data; name="a"\r\n'
        b"\r\n1234\r\n--boundary--\r\n"
    )
    headers = {"Content-Type": "multipart/form-data; boundary=boundary"}
    if with_content_length:
        headers["Content-Length"] = str(len(payload))

    response = await app.test_client().put("/", data=payload, headers=headers)
    assert response.status_code == 200
    assert await response.get_json() == {"a": "1234"}


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("with_content_length", [False, True])
async def test_request_global_max_content_length(
    stream: bool, with_content_length: bool
) -> None:
    app = Quart(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4

    @app.put("/")
    async def upload() -> bytes:
        assert request.max_content_length == 4
        if stream:
            return b"".join([chunk async for chunk in request.body])
        return await request.get_data(cache=True, as_text=False, parse_form_data=False)

    headers = {"Content-Length": "6"} if with_content_length else {}
    async with app.test_client().request(
        "/", method="PUT", headers=headers
    ) as connection:
        await connection.send(b"abc")
        await connection.send(b"def")
        await connection.send_complete()

    response = await connection.as_response()
    if stream and not with_content_length:
        assert response.status_code == 200
        assert await response.get_data() == b"abcdef"
    else:
        assert response.status_code == 413


async def test_request_get_data_timeout(http_scope: HTTPScope) -> None:
    request = Request(
        "POST",
        "http",
        "/",
        b"",
        Headers(),
        "",
        "1.1",
        http_scope,
        body_timeout=1,
        send_push_promise=no_op_push,
    )
    with pytest.raises(RequestTimeout):
        await request.get_data()


@pytest.mark.parametrize(
    "method, expected",
    [("GET", ["b", "c"]), ("POST", ["b", "c", "d"])],
)
async def test_request_values(
    method: str, expected: list[str], http_scope: HTTPScope
) -> None:
    request = Request(
        method,
        "http",
        "/",
        b"a=b&a=c",
        Headers(
            {"host": "quart.com", "Content-Type": "application/x-www-form-urlencoded"}
        ),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    request.body.set_result(urlencode({"a": "d"}).encode())
    assert (await request.values).getlist("a") == expected


async def test_request_send_push_promise(http_scope: HTTPScope) -> None:
    push_promise: tuple[str, Headers] = None

    async def _push(path: str, headers: Headers) -> None:
        nonlocal push_promise
        push_promise = (path, headers)

    request = Request(
        "GET",
        "http",
        "/",
        b"a=b&a=c",
        Headers(
            {
                "host": "quart.com",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*",
                "Accept-Encoding": "gzip",
                "User-Agent": "quart",
            }
        ),
        "",
        "2",
        http_scope,
        send_push_promise=_push,
    )
    await request.send_push_promise("/")
    assert push_promise[0] == "/"
    valid_headers = {"Accept": "*/*", "Accept-Encoding": "gzip", "User-Agent": "quart"}
    assert len(push_promise[1]) == len(valid_headers)
    for name, value in valid_headers.items():
        assert push_promise[1][name] == value
