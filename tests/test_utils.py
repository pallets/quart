from __future__ import annotations

from functools import partial

from werkzeug.datastructures import Headers

from quart.utils import decode_headers, encode_headers, is_coroutine_function


def test_is_coroutine_function() -> None:
    async def async_func() -> None:
        pass

    assert is_coroutine_function(async_func)
    assert is_coroutine_function(partial(async_func))


def test_encode_headers() -> None:
    assert encode_headers(Headers({"Foo": "Bar"})) == [(b"foo", b"Bar")]


def test_decode_headers() -> None:
    assert decode_headers([(b"foo", b"Bar")]) == Headers({"Foo": "Bar"})
