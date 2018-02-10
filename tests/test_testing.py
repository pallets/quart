import pytest

from quart import jsonify, Quart, request, Response, session
from quart.datastructures import CIMultiDict
from quart.exceptions import BadRequest
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


def test_build_headers_and_path() -> None:
    client = Client(Quart(__name__))
    headers, path = client._build_headers_and_path('/path', None, {'a': 'b'})
    assert path == '/path?a=b'
    assert headers['Remote-Addr'] == '127.0.0.1'
    assert headers['User-Agent'] == 'Quart'
    assert headers['host'] == 'localhost'


@pytest.mark.parametrize(
    'headers, expected',
    [
        (
            None,
            CIMultiDict({'Remote-Addr': '127.0.0.1', 'User-Agent': 'Quart',  'host': 'localhost'}),
        ),
        (
            CIMultiDict({'Remote-Addr': '1.2.3.4', 'User-Agent': 'Quarty', 'host': 'quart.com'}),
            CIMultiDict({'Remote-Addr': '1.2.3.4', 'User-Agent': 'Quarty', 'host': 'quart.com'}),
        ),
    ],
)
def test_build_headers_and_path_headers_defaults(
        headers: CIMultiDict, expected: CIMultiDict,
) -> None:
    client = Client(Quart(__name__))
    result, _ = client._build_headers_and_path('/path', headers)
    assert result == expected


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


@pytest.mark.asyncio
async def test_websocket_bad_request() -> None:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> str:
        return ''

    test_client = app.test_client()
    with pytest.raises(BadRequest):
        with test_client.websocket('/'):
            pass
