from functools import partial

from quart.utils import is_coroutine_function


def test_is_coroutine_function() -> None:
    async def async_func() -> None:
        pass

    assert is_coroutine_function(async_func)
    assert is_coroutine_function(partial(async_func))
