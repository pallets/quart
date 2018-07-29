from datetime import datetime
from typing import Union

import pytest

from quart.utils import create_cookie


@pytest.mark.parametrize(
    'expires',
    (0, 0.0, datetime.utcfromtimestamp(0)),
)
def test_create_cookie_with_numeric_expires(expires: Union[int, float, datetime]) -> None:
    cookies = create_cookie('key', 'value', expires=expires)
    assert cookies['key']['expires'] == 'Thu, 01 Jan 1970 00:00:00 GMT'
