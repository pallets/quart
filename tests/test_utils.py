import asyncio
from datetime import datetime
from typing import Union

import pytest

from quart.utils import create_cookie, ensure_coroutine


@pytest.mark.parametrize(
    'expires',
    (0, 0.0, datetime.utcfromtimestamp(0)),
)
def test_create_cookie_with_numeric_expires(expires: Union[int, float, datetime]) -> None:
    cookies = create_cookie('key', 'value', expires=expires)
    assert cookies['key']['expires'] == 'Thu, 01 Jan 1970 00:00:00 GMT'


def test_ensure_coroutine() -> None:
    def sync_func() -> None:
        pass

    async def async_func() -> None:
        pass

    sync_wrapped = ensure_coroutine(sync_func)
    assert asyncio.iscoroutinefunction(sync_wrapped)
    assert sync_wrapped._quart_async_wrapper  # type: ignore

    async_wrapped = ensure_coroutine(async_func)
    assert async_wrapped is async_func
