import pytest

from quart import abort, Blueprint, Quart, render_template_string, request, ResponseReturnValue


@pytest.mark.asyncio
async def test_blueprint_route() -> None:
    app = Quart(__name__)
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.route('/page/')
    async def route() -> ResponseReturnValue:
        return 'OK'

    app.register_blueprint(blueprint)

    async with app.test_request_context('GET', '/page/'):
        assert request.blueprint == 'blueprint'


@pytest.mark.asyncio
async def test_blueprint_url_prefix() -> None:
    app = Quart(__name__)
    blueprint = Blueprint('blueprint', __name__)
    prefix = Blueprint('prefix', __name__, url_prefix='/prefix')

    @app.route('/page/')
    @blueprint.route('/page/')
    @prefix.route('/page/')
    async def route() -> ResponseReturnValue:
        return 'OK'

    app.register_blueprint(blueprint, url_prefix='/blueprint')
    app.register_blueprint(prefix)

    async with app.test_request_context('GET', '/page/'):
        assert request.blueprint is None

    async with app.test_request_context('GET', '/prefix/page/'):
        assert request.blueprint == 'prefix'

    async with app.test_request_context('GET', '/blueprint/page/'):
        assert request.blueprint == 'blueprint'


@pytest.mark.asyncio
async def test_blueprint_template_filter() -> None:
    app = Quart(__name__)
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.app_template_filter()
    def reverse(value: str) -> str:
        return value[::-1]

    @blueprint.route('/')
    async def route() -> ResponseReturnValue:
        return await render_template_string("{{ name|reverse }}", name='hello')

    app.register_blueprint(blueprint)

    response = await app.test_client().get('/')
    assert b'olleh' in (await response.get_data())


@pytest.mark.asyncio
async def test_blueprint_error_handler() -> None:
    app = Quart(__name__)
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.route('/error/')
    async def error() -> ResponseReturnValue:
        abort(409)
        return 'OK'

    @blueprint.errorhandler(409)
    async def handler(_: Exception) -> ResponseReturnValue:
        return 'Something Unique', 409

    app.register_blueprint(blueprint)

    response = await app.test_client().get('/error/')
    assert response.status_code == 409
    assert b'Something Unique' in (await response.get_data())
