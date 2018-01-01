import quart.flask_patch

import flask  # noqa: I100
import pytest

import quart


@pytest.mark.asyncio
async def test_flask_app() -> None:
    app = flask.Flask(__name__)

    @app.route('/')
    def index() -> str:
        return 'Hello'

    test_client = app.test_client()
    response = await test_client.get('/')
    assert response.status_code == 200
    assert b'Hello' in (await response.get_data())


def test_api_matches() -> None:
    normalised_quart_api = set(dir(quart)) - set([
        '_websocket_ctx_stack', 'copy_current_websocket_context', 'flask_patch',
        'has_websocket_context', 'serving', 'websocket',
    ])
    normalised_flask_api = set(dir(flask)) - set([
        'Flask', 'flask_name', 'builtin_globals', 'new_handle_user_exception', 'name', 'module',
        'quart', 'new_handle_http_exception', 'sys', 'LocalStack', 'old_handle_http_exception',
        'asyncio', 'old_handle_user_exception', 'TaskLocal', 'flask_modules', 'HTTPException',
        '_sync_wait',
    ])
    assert normalised_quart_api == normalised_flask_api
