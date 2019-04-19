import pytest

from quart import (
    abort, Blueprint, Quart, render_template_string, request, ResponseReturnValue, websocket,
)
from quart.views import MethodView


@pytest.mark.asyncio
async def test_blueprint_route() -> None:
    app = Quart(__name__)
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.route('/page/')
    async def route() -> ResponseReturnValue:
        return 'OK'

    app.register_blueprint(blueprint)

    async with app.test_request_context("/page/"):
        assert request.blueprint == 'blueprint'


@pytest.mark.asyncio
async def test_blueprint_websocket() -> None:
    app = Quart(__name__)
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.websocket('/ws/')
    async def ws() -> None:
        while True:
            await websocket.send(websocket.blueprint.encode())

    app.register_blueprint(blueprint)

    test_client = app.test_client()
    async with test_client.websocket('/ws/') as test_websocket:
        result = await test_websocket.receive()
    assert result == b'blueprint'


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

    async with app.test_request_context("/page/"):
        assert request.blueprint is None

    async with app.test_request_context("/prefix/page/"):
        assert request.blueprint == 'prefix'

    async with app.test_request_context("/blueprint/page/"):
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
    assert b'olleh' in (await response.get_data())  # type: ignore


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
    assert b'Something Unique' in (await response.get_data())  # type: ignore


@pytest.mark.asyncio
async def test_blueprint_method_view() -> None:
    app = Quart(__name__)
    blueprint = Blueprint('blueprint', __name__)

    class Views(MethodView):

        async def get(self) -> ResponseReturnValue:
            return 'GET'

        async def post(self) -> ResponseReturnValue:
            return 'POST'

    blueprint.add_url_rule('/', view_func=Views.as_view('simple'))

    app.register_blueprint(blueprint)

    test_client = app.test_client()
    response = await test_client.get('/')
    assert 'GET' == (await response.get_data(raw=False))
    response = await test_client.post('/')
    assert 'POST' == (await response.get_data(raw=False))
