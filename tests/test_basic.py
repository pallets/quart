import pytest

from quart import abort, jsonify, Quart, request, Response, ResponseReturnValue, websocket
from quart.testing import WebsocketResponse


@pytest.fixture
def app() -> Quart:
    app = Quart(__name__)

    @app.route('/')
    def index() -> ResponseReturnValue:
        return 'index'

    @app.route('/json/', methods=['POST'])
    async def json() -> ResponseReturnValue:
        data = await request.get_json()
        return jsonify(data['value'])

    @app.route('/error/')
    async def error() -> ResponseReturnValue:
        abort(409)
        return 'OK'

    @app.errorhandler(409)
    async def generic_http_handler(_: Exception) -> ResponseReturnValue:
        return 'Something Unique', 409

    @app.errorhandler(404)
    async def not_found_handler(_: Exception) -> ResponseReturnValue:
        return 'Not Found', 404

    @app.websocket('/ws/')
    async def ws() -> None:
        # async for message in websocket:
        while True:
            message = await websocket.receive()
            await websocket.send(message)

    @app.websocket('/ws/abort/')
    async def ws_abort() -> None:
        abort(401)

    return app


@pytest.mark.asyncio
async def test_index(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get('/')
    assert response.status_code == 200
    assert b'index' in (await response.get_data())


@pytest.mark.asyncio
async def test_options(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.options('/')
    assert response.status_code == 200
    assert {method.strip() for method in response.headers['Allow'].split(',')} == {
        'HEAD', 'OPTIONS', 'GET',
    }


@pytest.mark.asyncio
async def test_json(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.post('/json/', json={'value': 'json'})
    assert response.status_code == 200
    assert b'json' in (await response.get_data())


@pytest.mark.asyncio
async def test_generic_error(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get('/error/')
    assert response.status_code == 409
    assert b'Something Unique' in (await response.get_data())


@pytest.mark.asyncio
async def test_not_found_error(app: Quart) -> None:
    test_client = app.test_client()
    response = await test_client.get('/not_found/')
    assert response.status_code == 404
    assert b'Not Found' in (await response.get_data())


@pytest.mark.asyncio
async def test_make_response_str(app: Quart) -> None:
    response = await app.make_response('Result')
    assert response.status_code == 200
    assert (await response.get_data()) == b'Result'

    response = await app.make_response(('Result', {'name': 'value'}))
    assert response.status_code == 200
    assert (await response.get_data()) == b'Result'
    assert response.headers['name'] == 'value'

    response = await app.make_response(('Result', 404, {'name': 'value'}))
    assert response.status_code == 404
    assert (await response.get_data()) == b'Result'
    assert response.headers['name'] == 'value'


@pytest.mark.asyncio
async def test_make_response_response(app: Quart) -> None:
    response = await app.make_response(Response('Result'))
    assert response.status_code == 200
    assert (await response.get_data()) == b'Result'

    response = await app.make_response((Response('Result'), {'name': 'value'}))
    assert response.status_code == 200
    assert (await response.get_data()) == b'Result'
    assert response.headers['name'] == 'value'

    response = await app.make_response((Response('Result'), 404, {'name': 'value'}))
    assert response.status_code == 404
    assert (await response.get_data()) == b'Result'
    assert response.headers['name'] == 'value'


@pytest.mark.asyncio
async def test_websocket(app: Quart) -> None:
    test_client = app.test_client()
    data = b'bob'
    with test_client.websocket('/ws/') as test_websocket:
        await test_websocket.send(data)
        result = await test_websocket.receive()
    assert result == data


@pytest.mark.asyncio
async def test_websocket_abort(app: Quart) -> None:
    test_client = app.test_client()
    with test_client.websocket('/ws/abort/') as test_websocket:
        try:
            await test_websocket.receive()
        except WebsocketResponse as error:
            assert error.response.status_code == 401
