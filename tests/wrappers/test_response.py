import pytest

from quart.wrappers.response import Response


@pytest.mark.asyncio
async def test_response_body() -> None:
    response = Response(b'Body')
    assert b'Body' == (await response.get_data())  # type: ignore
    # Fetch again to ensure it isn't exhausted
    assert b'Body' == (await response.get_data())  # type: ignore


def test_response_cache_control() -> None:
    response = Response(b'Body')
    response.cache_control.max_age = 2
    assert response.headers['Cache-Control'] == 'max-age=2'
    response.cache_control.no_cache = True
    assert response.headers['Cache-Control'] == 'max-age=2,no-cache'
