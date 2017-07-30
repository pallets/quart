import quart.flask_patch  # noqa

import pytest
from flask import Flask


@pytest.mark.asyncio
async def test_flask_app() -> None:
    app = Flask(__name__)

    @app.route('/')
    def index() -> str:
        return 'Hello'

    test_client = app.test_client()
    response = await test_client.get('/')
    assert response.status_code == 200
    assert b'Hello' in (await response.get_data())
