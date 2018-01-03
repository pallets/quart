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
        assert method in (await response.get_data(raw=False))


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
        bar = request.cookies.get('bar')
        session['foo'] = 'bar'
        response = jsonify({'foo': foo, 'bar': bar})
        response.set_cookie('bar', 'foo')
        return response

    client = Client(app)
    response = await client.get('/')
    assert (await response.get_json()) == {'foo': None, 'bar': None}
    response = await client.get('/')
    assert (await response.get_json()) == {'foo': 'bar', 'bar': 'foo'}


@pytest.mark.asyncio
async def test_set_cookie() -> None:
    app = Quart(__name__)

    @app.route('/', methods=['GET'])
    async def echo() -> Response:
        return jsonify({'foo': request.cookies.get('foo')})

    client = Client(app)
    client.set_cookie('foo', 'bar')
    response = await client.get('/')
    assert (await response.get_json()) == {'foo': 'bar'}
