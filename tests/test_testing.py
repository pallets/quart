from typing import Optional

import pytest

from quart import jsonify, Quart, redirect, request, Response, session
from quart.datastructures import CIMultiDict
from quart.exceptions import BadRequest
from quart.testing import make_test_headers_path_and_query_string, QuartClient as Client


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


@pytest.mark.parametrize(
    'path, query_string, expected_path, expected_query_string',
    [
        ('/path', {'a': 'b'}, '/path', b'a=b'),
        ('/path', {'a': ['b', 'c']}, '/path', b'a=b&a=c'),
        ('/path?b=c', None, '/path', b'b=c'),
        ('/path%20', None, '/path ', b''),
    ],
)
def test_build_headers_path_and_query_string(
        path: str,
        query_string: Optional[dict],
        expected_path: str,
        expected_query_string: bytes,
) -> None:
    headers, result_path, result_qs = make_test_headers_path_and_query_string(
        Quart(__name__), path, None, query_string,
    )
    assert result_path == expected_path
    assert headers['Remote-Addr'] == '127.0.0.1'
    assert headers['User-Agent'] == 'Quart'
    assert headers['host'] == 'localhost'
    assert result_qs == expected_query_string


def test_build_headers_path_and_query_string_with_query_string_error() -> None:
    with pytest.raises(ValueError):
        make_test_headers_path_and_query_string(Quart(__name__), '/?a=b', None, {'c': 'd'})


@pytest.mark.parametrize(
    'headers, expected',
    [
        (
            None,
            CIMultiDict({'Remote-Addr': '127.0.0.1', 'User-Agent': 'Quart', 'host': 'localhost'}),
        ),
        (
            CIMultiDict({'Remote-Addr': '1.2.3.4', 'User-Agent': 'Quarty', 'host': 'quart.com'}),
            CIMultiDict({'Remote-Addr': '1.2.3.4', 'User-Agent': 'Quarty', 'host': 'quart.com'}),
        ),
    ],
)
def test_build_headers_path_and_query_string_headers_defaults(
        headers: CIMultiDict, expected: CIMultiDict,
) -> None:
    result, path, query_string = make_test_headers_path_and_query_string(
        Quart(__name__), '/path', headers,
    )
    assert result == expected
    assert path == '/path'
    assert query_string == b''


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
async def test_data() -> None:
    app = Quart(__name__)

    @app.route('/', methods=['POST'])
    async def echo() -> Response:
        data = await request.get_data(True)
        return data

    client = Client(app)
    headers = {'Content-Type': 'application/octet-stream'}
    response = await client.post('/', data=b'ABCDEFG', headers=headers)
    assert (await response.get_data(True)) == b'ABCDEFG'  # type: ignore


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
async def test_redirect() -> None:
    app = Quart(__name__)

    @app.route('/', methods=['GET'])
    async def echo() -> str:
        return request.method

    @app.route('/redirect', methods=['GET'])
    async def redir() -> Response:
        return redirect('/')

    client = Client(app)
    assert (await client.get('/redirect', follow_redirects=True)).status_code == 200


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
        async with test_client.websocket('/'):
            pass


@pytest.mark.asyncio
async def test_push_promise() -> None:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> str:
        await request.send_push_promise("/")
        return ''

    test_client = app.test_client()
    await test_client.get("/")
    assert test_client.push_promises[0][0] == "/"
