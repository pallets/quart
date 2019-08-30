import pytest

from quart import Quart


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'debug, testing, present',
    [(True, True, False), (True, False, True), (False, True, False), (False, False, False)],
)
async def test_debug(debug: bool, testing: bool, present: bool) -> None:
    app = Quart(__name__)
    app.debug = debug
    app.testing = testing

    @app.route('/')
    async def error() -> None:
        raise Exception('Unique error')

    test_client = app.test_client()

    response = await test_client.get('/')
    assert response.status_code == 500
    assert (b'Unique error' in (await response.get_data())) is present  # type: ignore
