from __future__ import annotations

import pytest
from werkzeug.datastructures import Headers

from quart.utils import decode_headers
from quart.utils import encode_headers
from quart.utils import run_sync_iterable


def test_encode_headers() -> None:
    assert encode_headers(Headers({"Foo": "Bar"})) == [(b"foo", b"Bar")]


def test_decode_headers() -> None:
    assert decode_headers([(b"foo", b"Bar")]) == Headers({"Foo": "Bar"})


@pytest.mark.anyio
async def test_run_sync_iterable() -> None:
    def gen():
        yield from range(4)

    assert [v async for v in run_sync_iterable(gen())] == [0, 1, 2, 3]
