from typing import AsyncGenerator

import pytest

from quart import Blueprint, Quart, request
from quart.helpers import flash, get_flashed_messages, make_response, stream_with_context, url_for

SERVER_NAME = 'localhost'


@pytest.fixture
def app() -> Quart:
    app = Quart(__name__)
    app.config['SERVER_NAME'] = SERVER_NAME
    app.secret_key = 'secret'

    @app.route('/')
    async def index() -> str:
        return ''

    async def index_post() -> str:
        return ''

    app.add_url_rule('/post', view_func=index_post, methods=['POST'], endpoint='index_post')

    @app.route('/resource/<int:id>')
    async def resource(id: int) -> str:
        return str(id)

    return app


@pytest.fixture
def host_matched_app() -> Quart:
    app = Quart(__name__, host_matching=True, static_host='localhost')
    app.config['SERVER_NAME'] = SERVER_NAME

    @app.route('/')
    async def index() -> str:
        return ''

    @app.route('/', host='quart.com')
    async def host() -> str:
        return ''

    return app


@pytest.mark.asyncio
async def test_make_response(app: Quart) -> None:
    async with app.app_context():
        response = await make_response('foo', 202)
        assert response.status_code == 202
        assert b'foo' in (await response.get_data())  # type: ignore


@pytest.mark.asyncio
async def test_flash(app: Quart) -> None:
    async with app.test_request_context('/'):
        await flash('message')
        assert get_flashed_messages() == ['message']
        assert get_flashed_messages() == []


@pytest.mark.asyncio
async def test_flash_category(app: Quart) -> None:
    async with app.test_request_context('/'):
        await flash('bar', 'error')
        await flash('foo', 'info')
        assert get_flashed_messages(with_categories=True) == [('error', 'bar'), ('info', 'foo')]
        assert get_flashed_messages() == []


@pytest.mark.asyncio
async def test_flash_category_filter(app: Quart) -> None:
    async with app.test_request_context('/'):
        await flash('bar', 'error')
        await flash('foo', 'info')
        assert get_flashed_messages(category_filter=['error']) == ['bar']
        assert get_flashed_messages() == []


@pytest.mark.asyncio
async def test_url_for(app: Quart) -> None:
    async with app.test_request_context('/'):
        assert url_for('index') == '/'
        assert url_for('index_post', _method='POST') == '/post'
        assert url_for('resource', id=5) == '/resource/5'


@pytest.mark.asyncio
async def test_url_for_host_matching(host_matched_app: Quart) -> None:
    async with host_matched_app.app_context():
        assert url_for('index') == 'http://localhost/'
        assert url_for('host') == 'http://quart.com/'


@pytest.mark.asyncio
async def test_url_for_external(app: Quart) -> None:
    async with app.test_request_context('/'):
        assert url_for('index') == '/'
        assert url_for('index', _external=True) == 'http://localhost/'
        assert url_for('resource', id=5, _external=True) == 'http://localhost/resource/5'
        assert url_for('resource', id=5, _external=False) == '/resource/5'

    async with app.app_context():
        assert url_for('index') == 'http://localhost/'
        assert url_for('index', _external=False) == '/'


@pytest.mark.asyncio
async def test_url_for_scheme(app: Quart) -> None:
    async with app.test_request_context('/'):
        with pytest.raises(ValueError):
            url_for('index', _scheme='https')
        assert url_for('index', _scheme='https', _external=True) == 'https://localhost/'
        assert url_for(
            'resource', id=5, _scheme='https', _external=True,
        ) == 'https://localhost/resource/5'


@pytest.mark.asyncio
async def test_url_for_anchor(app: Quart) -> None:
    async with app.test_request_context('/'):
        assert url_for('index', _anchor='&foo') == '/#%26foo'
        assert url_for('resource', id=5, _anchor='&foo') == '/resource/5#%26foo'


@pytest.mark.asyncio
async def test_url_for_blueprint_relative(app: Quart) -> None:
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.route('/')
    def index() -> str:
        return ''

    app.register_blueprint(blueprint, url_prefix='/blue')

    async with app.test_request_context('/blue/'):
        assert url_for('.index') == '/blue/'
        assert url_for('index') == '/'


@pytest.mark.asyncio
async def test_stream_with_context() -> None:
    app = Quart(__name__)

    @app.route('/')
    def index() -> AsyncGenerator[bytes, None]:

        @stream_with_context
        async def generator() -> AsyncGenerator[bytes, None]:
            yield request.method.encode()
            yield b' '
            yield request.path.encode()

        return generator()

    test_client = app.test_client()
    response = await test_client.get('/')
    result = await response.get_data(raw=True)
    assert result == b'GET /'  # type: ignore
