from typing import Callable

import pytest

from quart.utils import create_cookie


@pytest.mark.parametrize(
    'numeric_type',
    (int, float),
)
def test_create_cookie_with_numeric_expires(numeric_type: Callable) -> None:
    cookies = create_cookie('key', 'value', expires=numeric_type(0))
    assert cookies['key']['expires'] == 'Thu, 01-Jan-1970 00:00:00'
