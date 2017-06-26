import pytest

from quart import jsonify, Quart, request, Response, session
from quart.testing import TestClient as Client


@pytest.mark.asyncio
async def test_methods() -> None:
    app = Quart(__name__)

    methods = ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT', 'TRACE']

    @app.route('/', methods=methods)
    async def echo() -> str:
        return request.method

    client = Client(app)

    for method in methods:
        func = getattr(client, method.lower())
        response = await func('/')
        assert method in response.get_data().decode()


@pytest.mark.asyncio
async def test_json() -> None:
    app = Quart(__name__)

    @app.route('/', methods=['POST'])
    async def echo() -> Response:
        data = await request.get_json()
        return jsonify(data)

    client = Client(app)
    response = await client.post('/', json={'a': 'b'})
    assert (await response.get_json()) == {'a': 'b'}


@pytest.mark.asyncio
async def test_form() -> None:
    app = Quart(__name__)

    @app.route('/', methods=['POST'])
    async def echo() -> Response:
        data = await request.form
        return jsonify(**data)

    client = Client(app)
    response = await client.post('/', form={'a': 'b'})
    assert (await response.get_json()) == {'a': 'b'}


@pytest.mark.asyncio
async def test_query_string() -> None:
    app = Quart(__name__)

    @app.route('/', methods=['GET'])
    async def echo() -> Response:
        data = request.args
        return jsonify(**data)

    client = Client(app)
    response = await client.get('/', query_string={'a': 'b'})
    assert (await response.get_json()) == {'a': 'b'}


@pytest.mark.asyncio
async def test_cookie_jar() -> None:
    app = Quart(__name__)
    app.secret_key = 'secret'

    @app.route('/', methods=['GET'])
    async def echo() -> Response:
        foo = session.get('foo')
        session['foo'] = 'bar'
        return jsonify({'foo': foo})

    client = Client(app)
    response = await client.get('/')
    assert (await response.get_json()) == {'foo': None}
    response = await client.get('/')
    assert (await response.get_json()) == {'foo': 'bar'}


@pytest.mark.asyncio
async def test_set_cookie() -> None:
    app = Quart(__name__)

    @app.route('/', methods=['GET'])
    async def echo() -> Response:
        return jsonify({'foo': request.cookies.get('foo').value})

    client = Client(app)
    client.set_cookie('foo', 'bar')
    response = await client.get('/')
    assert (await response.get_json()) == {'foo': 'bar'}
