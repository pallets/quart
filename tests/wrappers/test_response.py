from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

import hypothesis.strategies as strategies
import pytest
from hypothesis import given

from quart.wrappers.response import Response


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


def test_response_cache_control() -> None:
    response = Response(b'Body')
    response.cache_control.max_age = 2
    assert response.headers['Cache-Control'] == 'max-age=2'
    response.cache_control.no_cache = True
    assert response.headers['Cache-Control'] == 'max-age=2,no-cache'


@given(
    value=strategies.datetimes(
        timezones=strategies.just(timezone.utc), min_value=datetime(1900, 1, 1),
    ),
)
@pytest.mark.parametrize('header', ['date', 'expires', 'last_modified', 'retry_after'])
def test_datetime_headers(header: str, value: datetime) -> None:
    response = Response(b'Body')
    value = value.replace(microsecond=0)
    setattr(response, header, value)
    assert response.headers.get(header.title().replace('_', '-'))
    assert getattr(response, header) == value
