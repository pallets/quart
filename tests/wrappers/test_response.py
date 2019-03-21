from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any, AsyncGenerator

import hypothesis.strategies as strategies
import pytest
from hypothesis import given
from py._path.local import LocalPath

from quart.datastructures import ContentRange, Range, RangeSet
from quart.exceptions import RequestRangeNotSatisfiable
from quart.wrappers.response import DataBody, FileBody, IterableBody, Response


@pytest.mark.asyncio
async def test_data_wrapper() -> None:
    wrapper = DataBody(b"abcdef")
    results = []
    async with wrapper as response:
        async for data in response:
            results.append(data)
    assert results == [b"abcdef"]


@pytest.mark.asyncio
async def test_data_wrapper_sequence_conversion() -> None:
    wrapper = DataBody(b"abcdef")
    assert (await wrapper.convert_to_sequence()) == b"abcdef"


async def _simple_async_generator() -> AsyncGenerator[bytes, None]:
    yield b"abc"
    yield b"def"


@pytest.mark.asyncio
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "iterable",
    [[b"abc", b"def"], (data for data in [b"abc", b"def"]), _simple_async_generator()],
)
async def test_iterable_wrapper_sequence_conversion(iterable: Any) -> None:
    wrapper = IterableBody(iterable)
    assert (await wrapper.convert_to_sequence()) == b"abcdef"


@pytest.mark.asyncio
async def test_file_wrapper(tmpdir: LocalPath) -> None:
    file_ = tmpdir.join('file_wrapper')
    file_.write('abcdef')
    wrapper = FileBody(Path(file_.realpath()), buffer_size=3)
    results = []
    async with wrapper as response:
        async for data in response:
            results.append(data)
    assert results == [b"abc", b"def"]


@pytest.mark.asyncio
async def test_file_wrapper_sequence_conversion(tmpdir: LocalPath) -> None:
    file_ = tmpdir.join('file_wrapper')
    file_.write('abcdef')
    wrapper = FileBody(Path(file_.realpath()), buffer_size=3)
    assert (await wrapper.convert_to_sequence()) == b"abcdef"


@pytest.mark.parametrize(
    'status, expected',
    [(201, 201), (None, 200), (HTTPStatus.PARTIAL_CONTENT, 206)],
)
def test_response_status(status: Any, expected: int) -> None:
    response = Response(b'Body', status=status)
    assert response.status_code == expected


def test_response_status_error() -> None:
    with pytest.raises(ValueError) as error_info:
        Response(b'Body', '200 OK')
    assert str(error_info.value) == 'Quart  does not support non-integer status values'


@pytest.mark.asyncio
async def test_response_body() -> None:
    response = Response(b'Body')
    assert b'Body' == (await response.get_data())  # type: ignore
    # Fetch again to ensure it isn't exhausted
    assert b'Body' == (await response.get_data())  # type: ignore


@pytest.mark.asyncio
async def test_response_make_conditional() -> None:
    response = Response(b"abcdef")
    await response.make_conditional(Range("bytes", [RangeSet(0, 3)]))
    assert b"abc" == (await response.get_data())  # type: ignore
    assert response.status_code == 206
    assert response.accept_ranges == "bytes"
    assert response.content_range == ContentRange("bytes", 0, 2, 6)


@pytest.mark.asyncio
@pytest.mark.parametrize("range_", [Range("", {}), Range("bytes", [RangeSet(0, 6)])])
async def test_response_make_conditional_no_condition(range_: Range) -> None:
    response = Response(b"abcdef")
    await response.make_conditional(range_)
    assert b"abcdef" == (await response.get_data())  # type: ignore
    assert response.status_code == 200
    assert response.accept_ranges == "bytes"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "range_",
    [
        Range("seconds", [RangeSet(0, 3)]),
        Range("bytes", [RangeSet(0, 2), RangeSet(3, 5)]),
        Range("bytes", [RangeSet(0, 8)]),
    ],
)
async def test_response_make_conditional_not_satisfiable(range_: Range) -> None:
    response = Response(b"abcdef")
    with pytest.raises(RequestRangeNotSatisfiable):
        await response.make_conditional(range_)


def test_response_cache_control() -> None:
    response = Response(b'Body')
    response.cache_control.max_age = 2
    assert response.headers['Cache-Control'] == 'max-age=2'
    response.cache_control.no_cache = True
    assert response.headers['Cache-Control'] == 'max-age=2,no-cache'


@given(
    value=strategies.datetimes(
        timezones=strategies.just(timezone.utc),
        # The min_value and max_value are needed because
        # wsgiref uses the function time.gmtime on the generated timestamps,
        # which fails on windows with values outside of these bounds
        min_value=datetime(1970, 1, 2), max_value=datetime(3000, 1, 2),
    ),
)
@pytest.mark.parametrize('header', ['date', 'expires', 'last_modified', 'retry_after'])
def test_datetime_headers(header: str, value: datetime) -> None:
    response = Response(b'Body')
    value = value.replace(microsecond=0)
    setattr(response, header, value)
    assert response.headers.get(header.title().replace('_', '-'))
    assert getattr(response, header) == value
