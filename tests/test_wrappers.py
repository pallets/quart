import asyncio
from base64 import b64encode

import pytest

from quart.datastructures import CIMultiDict
from quart.exceptions import RequestEntityTooLarge
from quart.wrappers import _BaseRequestResponse, Body, Request


def test_basic_authorization() -> None:
    headers = CIMultiDict()
    headers['Authorization'] = "Basic {}".format(b64encode(b'identity:secret').decode('ascii'))
    request = Request('GET', '/', headers)
    auth = request.authorization
    assert auth.username == 'identity'
    assert auth.password == 'secret'


def test_digest_authorization() -> None:
    headers = CIMultiDict()
    headers['Authorization'] = (
        'Digest '
        'username="identity", '
        'realm="realm@rea.lm", '
        'nonce="abcd1234", '
        'uri="/path", '
        'response="abcd1235", '
        'opaque="abcd1236"'
    )
    request = Request('GET', '/', headers)
    auth = request.authorization
    assert auth.username == 'identity'
    assert auth.realm == 'realm@rea.lm'
    assert auth.nonce == 'abcd1234'
    assert auth.uri == '/path'
    assert auth.response == 'abcd1235'
    assert auth.opaque == 'abcd1236'


def test_mimetype_get_property() -> None:
    base_request_response = _BaseRequestResponse({'Content-Type': 'text/html; charset=utf-8'})
    assert base_request_response.mimetype == 'text/html'
    assert base_request_response.mimetype_params == {'charset': 'utf-8'}


def test_mimetype_set_property() -> None:
    base_request_response = _BaseRequestResponse(None)
    base_request_response.mimetype = 'text/html'
    assert base_request_response.headers['Content-Type'] == 'text/html; charset=utf-8'
    base_request_response.mimetype = 'application/json'
    assert base_request_response.headers['Content-Type'] == 'application/json'


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
        Request('GET', '/', headers, max_content_length=max_content_length)
