from __future__ import annotations

from quart import Quart
from quart.debug import traceback_response


async def test_debug() -> None:
    app = Quart(__name__)
    async with app.test_request_context("/"):
        response = await traceback_response(Exception("Unique error"))

    assert response.status_code == 500
    assert b"Unique error" in (await response.get_data())
