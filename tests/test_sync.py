import pytest

from quart import Quart, request, ResponseReturnValue


@pytest.fixture(name="app")
def _app() -> Quart:
    app = Quart(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index() -> ResponseReturnValue:
        return request.method

    return app


@pytest.mark.asyncio
async def test_sync_request_context(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get("/")
    assert b"GET" in (await response.get_data())  # type: ignore
    response = await test_client.post("/")
    assert b"POST" in (await response.get_data())  # type: ignore
