import asyncio
from urllib.parse import urlencode

import pytest

from quart.datastructures import CIMultiDict
from quart.exceptions import RequestEntityTooLarge, RequestTimeout
from quart.wrappers.request import Body, Request


async def _fill_body(body: Body, semaphore: asyncio.Semaphore, limit: int) -> None:
    for number in range(limit):
        body.append(b"%d" % number)
        await semaphore.acquire()
    body.set_complete()


@pytest.mark.asyncio
async def test_full_body() -> None:
    body = Body(None)
    limit = 3
    semaphore = asyncio.Semaphore(limit)
    asyncio.ensure_future(_fill_body(body, semaphore, limit))
    assert b'012' == await body  # type: ignore


@pytest.mark.asyncio
async def test_body_streaming() -> None:
    body = Body(None)
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
async def test_body_streaming_no_data() -> None:
    body = Body(None)
    semaphore = asyncio.Semaphore(0)
    asyncio.ensure_future(_fill_body(body, semaphore, 0))
    async for _ in body:  # type: ignore # noqa: F841
        assert False  # Should not reach this
    assert b'' == await body  # type: ignore


def test_body_exceeds_max_content_length() -> None:
    max_content_length = 5
    body = Body(max_content_length)
    with pytest.raises(RequestEntityTooLarge):
        body.append(b' ' * (max_content_length + 1))


def test_request_exceeds_max_content_length() -> None:
    max_content_length = 5
    headers = CIMultiDict()
    headers['Content-Length'] = str(max_content_length + 1)
    with pytest.raises(RequestEntityTooLarge):
        Request('POST', 'http', '/', b'', headers, max_content_length=max_content_length)


@pytest.mark.asyncio
async def test_request_get_data_timeout() -> None:
    request = Request('POST', 'http', '/', b'', CIMultiDict(), body_timeout=1)
    with pytest.raises(RequestTimeout):
        await request.get_data()


@pytest.mark.asyncio
async def test_request_values() -> None:
    request = Request(
        'GET', 'http', '/', b'a=b&a=c',
        CIMultiDict({'host': 'quart.com', 'Content-Type': 'application/x-www-form-urlencoded'}),
    )
    request.body.append(urlencode({'a': 'd'}).encode())
    request.body.set_complete()
    assert (await request.values).getlist('a') == ['b', 'c', 'd']
