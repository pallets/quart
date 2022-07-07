from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from typing import Any, AsyncGenerator

import pytest
from hypothesis import given, strategies as strategies
from py._path.local import LocalPath
from werkzeug.datastructures import Range
from werkzeug.exceptions import RequestedRangeNotSatisfiable

from quart.wrappers.response import DataBody, FileBody, IOBody, IterableBody, Response


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
    "iterable", [[b"abc", b"def"], (data for data in [b"abc", b"def"]), _simple_async_generator()]
)
async def test_iterable_wrapper(iterable: Any) -> None:
    wrapper = IterableBody(iterable)
    results = []
    async with wrapper as response:
        async for data in response:
            results.append(data)
    assert results == [b"abc", b"def"]


async def test_file_wrapper(tmpdir: LocalPath) -> None:
    file_ = tmpdir.join("file_wrapper")
    file_.write("abcdef")
    wrapper = FileBody(Path(file_.realpath()), buffer_size=3)
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
    assert b"Body" == (await response.get_data())  # type: ignore
    # Fetch again to ensure it isn't exhausted
    assert b"Body" == (await response.get_data())  # type: ignore


async def test_response_make_conditional() -> None:
    response = Response(b"abcdef")
    await response.make_conditional(Range("bytes", [(0, 3)]))
    assert b"abc" == (await response.get_data())  # type: ignore
    assert response.status_code == 206
    assert response.accept_ranges == "bytes"
    assert response.content_range.units == "bytes"
    assert response.content_range.start == 0
    assert response.content_range.stop == 2
    assert response.content_range.length == 6


@pytest.mark.parametrize("range_", [Range("", []), Range("bytes", [(0, 6)])])
async def test_response_make_conditional_no_condition(range_: Range) -> None:
    response = Response(b"abcdef")
    await response.make_conditional(range_)
    assert b"abcdef" == (await response.get_data())  # type: ignore
    assert response.status_code == 200
    assert response.accept_ranges == "bytes"


@pytest.mark.parametrize(
    "range_",
    [Range("seconds", [(0, 3)]), Range("bytes", [(0, 2), (3, 5)]), Range("bytes", [(0, 8)])],
)
async def test_response_make_conditional_not_satisfiable(range_: Range) -> None:
    response = Response(b"abcdef")
    with pytest.raises(RequestedRangeNotSatisfiable):
        await response.make_conditional(range_)


def test_response_cache_control() -> None:
    response = Response(b"Body")
    response.cache_control.max_age = 2
    assert response.headers["Cache-Control"] == "max-age=2"
    response.cache_control.no_cache = True
    assert response.headers["Cache-Control"] == "max-age=2, no-cache"


async def test_empty_response() -> None:
    response = Response()
    assert b"" == (await response.get_data())  # type: ignore


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
