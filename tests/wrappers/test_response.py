from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
from datetime import timezone
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as strategies
from werkzeug.datastructures import Headers
from werkzeug.exceptions import RequestedRangeNotSatisfiable

from quart.testing import no_op_push
from quart.typing import HTTPScope
from quart.wrappers import Request
from quart.wrappers.response import DataBody
from quart.wrappers.response import FileBody
from quart.wrappers.response import IOBody
from quart.wrappers.response import IterableBody
from quart.wrappers.response import Response


async def test_data_wrapper() -> None:
    wrapper = DataBody(b"abcdef")
    results = []
    async with wrapper as response:
        async for data in response:
            results.append(data)
    assert results == [b"abcdef"]


async def _simple_async_generator() -> AsyncGenerator[bytes, None]:
    yield b"abc"
    yield b"def"


@pytest.mark.parametrize(
    "iterable",
    [[b"abc", b"def"], (data for data in [b"abc", b"def"]), _simple_async_generator()],
)
async def test_iterable_wrapper(iterable: Any) -> None:
    wrapper = IterableBody(iterable)
    results = []
    async with wrapper as response:
        async for data in response:
            results.append(data)
    assert results == [b"abc", b"def"]


async def test_file_wrapper(tmp_path: Path) -> None:
    file_ = tmp_path / "file_wrapper"
    file_.write_text("abcdef")
    wrapper = FileBody(Path(file_), buffer_size=3)
    results = []
    async with wrapper as response:
        async for data in response:
            results.append(data)
    assert results == [b"abc", b"def"]


async def test_io_wrapper() -> None:
    wrapper = IOBody(BytesIO(b"abcdef"), buffer_size=3)
    results = []
    async with wrapper as response:
        async for data in response:
            results.append(data)
    assert results == [b"abc", b"def"]


@pytest.mark.parametrize(
    "status, expected", [(201, 201), (None, 200), (HTTPStatus.PARTIAL_CONTENT, 206)]
)
def test_response_status(status: Any, expected: int) -> None:
    response = Response(b"Body", status=status)
    assert response.status_code == expected


async def test_response_body() -> None:
    response = Response(b"Body")
    assert b"Body" == (await response.get_data())
    # Fetch again to ensure it isn't exhausted
    assert b"Body" == (await response.get_data())


async def test_response_make_conditional(http_scope: HTTPScope) -> None:
    request = Request(
        "GET",
        "https",
        "/",
        b"",
        Headers([("Range", "bytes=0-3")]),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    response = Response(b"abcdef")
    await response.make_conditional(request, accept_ranges=True, complete_length=6)
    assert b"abcd" == (await response.get_data())
    assert response.status_code == 206
    assert response.accept_ranges == "bytes"
    assert response.content_range.units == "bytes"
    assert response.content_range.start == 0
    assert response.content_range.stop == 4
    assert response.content_range.length == 6


async def test_response_make_conditional_no_condition(http_scope: HTTPScope) -> None:
    request = Request(
        "GET",
        "https",
        "/",
        b"",
        Headers(),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    response = Response(b"abcdef")
    await response.make_conditional(request, complete_length=6)
    assert b"abcdef" == (await response.get_data())
    assert response.status_code == 200


async def test_response_make_conditional_out_of_bound(http_scope: HTTPScope) -> None:
    request = Request(
        "GET",
        "https",
        "/",
        b"",
        Headers([("Range", "bytes=0-666")]),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    response = Response(b"abcdef")
    await response.make_conditional(request, complete_length=6)
    assert b"abcdef" == (await response.get_data())
    assert response.status_code == 206


async def test_response_make_conditional_not_modified(http_scope: HTTPScope) -> None:
    response = Response(b"abcdef")
    await response.add_etag()
    request = Request(
        "GET",
        "https",
        "/",
        b"",
        Headers([("If-None-Match", response.get_etag()[0])]),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    await response.make_conditional(request)
    assert response.status_code == 304
    assert b"" == (await response.get_data())
    assert "content-length" not in response.headers


@pytest.mark.parametrize(
    "range_",
    ["second=0-3", "bytes=0-2,3-5", "bytes=8-16"],
)
async def test_response_make_conditional_not_satisfiable(
    range_: str, http_scope: HTTPScope
) -> None:
    request = Request(
        "GET",
        "https",
        "/",
        b"",
        Headers([("Range", range_)]),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    response = Response(b"abcdef")
    with pytest.raises(RequestedRangeNotSatisfiable):
        await response.make_conditional(request, complete_length=6)


def test_response_cache_control() -> None:
    response = Response(b"Body")
    response.cache_control.max_age = 2
    assert response.headers["Cache-Control"] == "max-age=2"
    response.cache_control.no_cache = True
    assert response.headers["Cache-Control"] == "max-age=2, no-cache"


async def test_empty_response() -> None:
    response = Response()
    assert b"" == (await response.get_data())


@given(
    value=strategies.datetimes(
        timezones=strategies.just(timezone.utc),
        # The min_value and max_value are needed because
        # wsgiref uses the function time.gmtime on the generated timestamps,
        # which fails on windows with values outside of these bounds
        min_value=datetime(1970, 1, 2),
        max_value=datetime(3000, 1, 2),
    )
)
@pytest.mark.parametrize("header", ["date", "expires", "last_modified", "retry_after"])
def test_datetime_headers(header: str, value: datetime) -> None:
    response = Response(b"Body")
    value = value.replace(microsecond=0)
    setattr(response, header, value)
    assert response.headers.get(header.title().replace("_", "-"))
    assert getattr(response, header) == value
