import pytest

from quart import abort, Blueprint, Quart, request, ResponseReturnValue


def test_blueprint_routes() -> None:
    app = Quart(__name__)
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.route('/page/')
    async def route() -> ResponseReturnValue:
        return 'OK'

    app.register_blueprint(blueprint)

    with app.test_request_context('GET', '/page/'):
        assert request.blueprint == 'blueprint'


def test_blueprint_url_prefix() -> None:
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

    with app.test_request_context('GET', '/page/'):
        assert request.blueprint is None

    with app.test_request_context('GET', '/prefix/page/'):
        assert request.blueprint == 'prefix'

    with app.test_request_context('GET', '/blueprint/page/'):
        assert request.blueprint == 'blueprint'


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
    assert b'Something Unique' in response.get_data()
