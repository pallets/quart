import pytest

from quart.exceptions import (
    abort, HTTPException, HTTPStatusException, MethodNotAllowed, RedirectRequired,
)


def test_abort() -> None:
    with pytest.raises(HTTPStatusException):
        abort(400)


def test_abort_with_arguments() -> None:
    with pytest.raises(HTTPException) as exc_info:
        abort(400, "A description", "A name")
    assert exc_info.value.description == "A description"


@pytest.mark.asyncio
async def test_http_exception() -> None:
    error = HTTPException(205, 'Description', 'Name')
    assert error.get_response().status_code == 205
    assert b'Name' in (await error.get_response().get_data())  # type: ignore
    assert b'Description' in (await error.get_response().get_data())  # type: ignore


def test_method_not_allowed() -> None:
    error = MethodNotAllowed(['GET', 'POST'])
    assert 'GET, POST' == error.get_headers()['Allow']


def test_redirect_required() -> None:
    error = RedirectRequired('/redirect')
    assert '/redirect' in error.get_response().headers['Location']
