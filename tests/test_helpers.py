import pytest

from quart import Blueprint, Quart
from quart.helpers import flash, get_flashed_messages, make_response, url_for

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

    app.add_url_rule('/post', index_post, methods=['POST'], endpoint='index_post')

    @app.route('/resource/<int:id>')
    async def resource(id: int) -> str:
        return str(id)

    return app


@pytest.mark.asyncio
async def test_make_response(app: Quart) -> None:
    async with app.app_context():
        response = await make_response('foo', 202)
        assert response.status_code == 202
        assert b'foo' in (await response.get_data())


@pytest.mark.asyncio
async def test_flash(app: Quart) -> None:
    async with app.test_request_context('GET', '/'):
        await flash('message')
        assert get_flashed_messages() == ['message']
        assert get_flashed_messages() == []


@pytest.mark.asyncio
async def test_flash_category(app: Quart) -> None:
    async with app.test_request_context('GET', '/'):
        await flash('bar', 'error')
        await flash('foo', 'info')
        assert get_flashed_messages(with_categories=True) == [('error', 'bar'), ('info', 'foo')]
        assert get_flashed_messages() == []


@pytest.mark.asyncio
async def test_flash_category_filter(app: Quart) -> None:
    async with app.test_request_context('GET', '/'):
        await flash('bar', 'error')
        await flash('foo', 'info')
        assert get_flashed_messages(category_filter=['error']) == ['bar']
        assert get_flashed_messages() == []


@pytest.mark.asyncio
async def test_url_for(app: Quart) -> None:
    async with app.app_context():
        assert url_for('index') == '/'
        assert url_for('index_post', _method='POST') == '/post'
        assert url_for('resource', id=5) == '/resource/5'


@pytest.mark.asyncio
async def test_url_for_external(app: Quart) -> None:
    async with app.app_context():
        assert url_for('index', _external=True) == 'http://localhost/'
        assert url_for('resource', id=5, _external=True) == 'http://localhost/resource/5'


@pytest.mark.asyncio
async def test_url_for_scheme(app: Quart) -> None:
    async with app.app_context():
        with pytest.raises(ValueError):
            url_for('index', _scheme='https')
        assert url_for('index', _scheme='https', _external=True) == 'https://localhost/'
        assert url_for(
            'resource', id=5, _scheme='https', _external=True,
        ) == 'https://localhost/resource/5'


@pytest.mark.asyncio
async def test_url_for_anchor(app: Quart) -> None:
    async with app.app_context():
        assert url_for('index', _anchor='&foo') == '/#%26foo'
        assert url_for('resource', id=5, _anchor='&foo') == '/resource/5#%26foo'


@pytest.mark.asyncio
async def test_url_for_blueprint_relative(app: Quart) -> None:
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.route('/')
    def index() -> str:
        return ''

    app.register_blueprint(blueprint, url_prefix='/blue')

    async with app.test_request_context('GET', '/blue/'):
        assert url_for('.index') == '/blue/'
        assert url_for('index') == '/'
