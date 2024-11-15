from __future__ import annotations

import asyncio
from urllib.parse import urlencode

import pytest
from hypercorn.typing import HTTPScope
from werkzeug.datastructures import Headers
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.exceptions import RequestTimeout

from quart.testing import no_op_push
from quart.wrappers.request import Body
from quart.wrappers.request import Request


async def _fill_body(body: Body, semaphore: asyncio.Semaphore, limit: int) -> None:
    for number in range(limit):
        body.append(b"%d" % number)
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
    async for data in body:
        semaphore.release()
        assert data == b"%d" % index
        index += 1
    assert b"" == await body


async def test_body_stream_single_chunk() -> None:
    body = Body(None, None)
    body.append(b"data")
    body.set_complete()

    async def _check_data() -> None:
        async for data in body:
            assert data == b"data"

    await asyncio.wait_for(_check_data(), 1)


async def test_body_streaming_no_data() -> None:
    body = Body(None, None)
    semaphore = asyncio.Semaphore(0)
    asyncio.ensure_future(_fill_body(body, semaphore, 0))
    async for _ in body:  # noqa: F841
        raise AssertionError("Should not reach this line")
    assert b"" == await body


async def test_body_exceeds_max_content_length() -> None:
    max_content_length = 5
    body = Body(None, max_content_length)
    body.append(b" " * (max_content_length + 1))
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
    request.body.append(urlencode({"a": "d"}).encode())
    request.body.set_complete()
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
