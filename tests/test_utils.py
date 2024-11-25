from __future__ import annotations

from werkzeug.datastructures import Headers

from quart.utils import decode_headers
from quart.utils import encode_headers


def test_encode_headers() -> None:
    assert encode_headers(Headers({"Foo": "Bar"})) == [(b"foo", b"Bar")]


def test_decode_headers() -> None:
    assert decode_headers([(b"foo", b"Bar")]) == Headers({"Foo": "Bar"})
