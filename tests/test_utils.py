import asyncio

from quart.utils import ensure_coroutine


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
