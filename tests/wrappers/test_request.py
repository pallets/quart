import asyncio
from typing import Tuple
from urllib.parse import urlencode

import pytest

from quart.datastructures import CIMultiDict, Headers
from quart.exceptions import RequestEntityTooLarge, RequestTimeout
from quart.testing import no_op_push
from quart.wrappers.request import Body, Request


async def _fill_body(body: Body, semaphore: asyncio.Semaphore, limit: int) -> None:
    for number in range(limit):
        body.append(b"%d" % number)
        await semaphore.acquire()
    body.set_complete()


@pytest.mark.asyncio
async def test_full_body() -> None:
    body = Body(None, None)
    limit = 3
    semaphore = asyncio.Semaphore(limit)
    asyncio.ensure_future(_fill_body(body, semaphore, limit))
    assert b'012' == await body  # type: ignore


@pytest.mark.asyncio
async def test_body_streaming() -> None:
    body = Body(None, None)
    limit = 3
    semaphore = asyncio.Semaphore(0)
    asyncio.ensure_future(_fill_body(body, semaphore, limit))
    index = 0
    async for data in body:  # type: ignore
        semaphore.release()
        assert data == b"%d" % index
        index += 1
    assert b'' == await body  # type: ignore


@pytest.mark.asyncio
async def test_body_stream_single_chunk() -> None:
    body = Body(None, None)
    body.append(b"data")
    body.set_complete()

    async def _check_data() -> None:
        async for data in body:
            assert data == b"data"

    await asyncio.wait_for(_check_data(), 1)


@pytest.mark.asyncio
async def test_body_streaming_no_data() -> None:
    body = Body(None, None)
    semaphore = asyncio.Semaphore(0)
    asyncio.ensure_future(_fill_body(body, semaphore, 0))
    async for _ in body:  # type: ignore # noqa: F841
        assert False  # Should not reach this
    assert b'' == await body  # type: ignore


@pytest.mark.asyncio
async def test_body_exceeds_max_content_length() -> None:
    max_content_length = 5
    body = Body(None, max_content_length)
    body.append(b' ' * (max_content_length + 1))
    with pytest.raises(RequestEntityTooLarge):
        await body


@pytest.mark.asyncio
async def test_request_exceeds_max_content_length() -> None:
    max_content_length = 5
    headers = CIMultiDict()
    headers['Content-Length'] = str(max_content_length + 1)
    request = Request(
        'POST', 'http', '/', b'', headers, max_content_length=max_content_length,
        send_push_promise=no_op_push,
    )
    with pytest.raises(RequestEntityTooLarge):
        await request.get_data()


@pytest.mark.asyncio
async def test_request_get_data_timeout() -> None:
    request = Request(
        'POST', 'http', '/', b'', CIMultiDict(), body_timeout=1, send_push_promise=no_op_push,
    )
    with pytest.raises(RequestTimeout):
        await request.get_data()


@pytest.mark.asyncio
async def test_request_values() -> None:
    request = Request(
        'GET', 'http', '/', b'a=b&a=c',
        CIMultiDict({'host': 'quart.com', 'Content-Type': 'application/x-www-form-urlencoded'}),
        send_push_promise=no_op_push,
    )
    request.body.append(urlencode({'a': 'd'}).encode())
    request.body.set_complete()
    assert (await request.values).getlist('a') == ['b', 'c', 'd']


@pytest.mark.asyncio
async def test_request_send_push_promise() -> None:
    push_promise: Tuple[str, Headers] = None

    async def _push(path: str, headers: Headers) -> None:
        nonlocal push_promise
        push_promise = (path, headers)

    request = Request(
        'GET', 'http', '/', b'a=b&a=c',
        CIMultiDict({
            'host': 'quart.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "User-Agent": "quart",
        }),
        send_push_promise=_push,
    )
    await request.send_push_promise("/")
    assert push_promise[0] == "/"
    valid_headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip",
        "User-Agent": "quart",
    }
    assert len(push_promise[1]) == len(valid_headers)
    for name, value in valid_headers.items():
        assert push_promise[1][name] == value
