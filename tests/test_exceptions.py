from __future__ import annotations

from http import HTTPStatus

import pytest
from werkzeug.exceptions import abort
from werkzeug.exceptions import HTTPException

from quart import Response


@pytest.mark.parametrize("status", [400, HTTPStatus.BAD_REQUEST])
def test_abort(status: int | HTTPStatus) -> None:
    with pytest.raises(HTTPException) as exc_info:
        abort(status)
    assert exc_info.value.get_response().status_code == 400


def test_abort_with_response() -> None:
    with pytest.raises(HTTPException) as exc_info:
        abort(Response("Message", 205))
    assert exc_info.value.get_response().status_code == 205
