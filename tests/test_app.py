import asyncio
import os
from typing import NoReturn, Optional, Set

import pytest
from asynctest import Mock as AsyncMock

from quart.app import Quart
from quart.datastructures import CIMultiDict
from quart.globals import session, websocket
from quart.sessions import SecureCookieSession, SessionInterface
from quart.testing import no_op_push, WebsocketResponse
from quart.typing import ResponseReturnValue
from quart.wrappers import Response

TEST_RESPONSE = Response('')


def test_endpoint_overwrite() -> None:
    app = Quart(__name__)

    def route() -> str:
        return ''

    def route2() -> str:
        return ''

    async def route3() -> str:
        return ''

    app.add_url_rule('/a', 'index', route, ['GET'])
    app.add_url_rule('/a/a', 'index', route, ['GET'])  # Should not assert, as same view func
    with pytest.raises(AssertionError):
        app.add_url_rule('/a/b', 'index', route2, ['GET'])
    app.add_url_rule('/b', 'async', route3, ['GET'])
    app.add_url_rule('/b/a', 'async', route3, ['GET'])  # Should not assert, as same view func
    with pytest.raises(AssertionError):
        app.add_url_rule('/b/b', 'async', route2, ['GET'])


@pytest.mark.parametrize(
    'methods, required_methods, automatic_options',
    [
        ({}, {}, False),
        ({}, {}, True),
        ({'GET', 'PUT'}, {}, False),
        ({'GET', 'PUT'}, {}, True),
        ({}, {'GET', 'PUT'}, False),
        ({}, {'GET', 'PUT'}, True),
    ],
)
def test_add_url_rule_methods(
        methods: Set[str], required_methods: Set[str], automatic_options: bool,
) -> None:
    app = Quart(__name__)

    def route() -> str:
        return ''

    route.methods = methods  # type: ignore
    route.required_methods = required_methods  # type: ignore

    non_func_methods = {'PATCH'} if not methods else None
    app.add_url_rule(
        '/', 'end', route, non_func_methods, provide_automatic_options=automatic_options,
    )
    result = {'PATCH'} if not methods else set()
    if automatic_options:
        result.add('OPTIONS')
    result.update(methods)
    result.update(required_methods)
    if 'GET' in result:
        result.add('HEAD')
    assert app.url_map.endpoints['end'][0].methods == result


@pytest.mark.parametrize(
    'methods, arg_automatic, func_automatic, expected_methods, expected_automatic',
    [
        ({'GET'}, True, None, {'HEAD', 'GET', 'OPTIONS'}, True),
        ({'GET'}, None, None, {'HEAD', 'GET', 'OPTIONS'}, True),
        ({'GET'}, None, True, {'HEAD', 'GET', 'OPTIONS'}, True),
        ({'GET', 'OPTIONS'}, None, None, {'HEAD', 'GET', 'OPTIONS'}, False),
        ({'GET'}, False, True, {'HEAD', 'GET'}, False),
        ({'GET'}, None, False, {'HEAD', 'GET'}, False),
    ],
)
def test_add_url_rule_automatic_options(
        methods: Set[str], arg_automatic: Optional[bool], func_automatic: Optional[bool],
        expected_methods: Set[str], expected_automatic: bool,
) -> None:
    app = Quart(__name__)

    def route() -> str:
        return ''

    route.provide_automatic_options = func_automatic  # type: ignore

    app.add_url_rule('/', 'end', route, methods, provide_automatic_options=arg_automatic)
    assert app.url_map.endpoints['end'][0].methods == expected_methods
    assert app.url_map.endpoints['end'][0].provide_automatic_options == expected_automatic


@pytest.mark.asyncio
async def test_host_matching() -> None:
    app = Quart(__name__, static_host='quart.com', host_matching=True)
    app.config['SERVER_NAME'] = 'quart.com'

    @app.route('/')
    def route() -> str:
        return ''

    test_client = app.test_client()
    response = await test_client.get('/', headers={'host': 'quart.com'})
    assert response.status_code == 200

    response = await test_client.get('/', headers={'host': 'localhost'})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_subdomain() -> None:
    app = Quart(__name__, static_host='quart.com', host_matching=True)
    app.config['SERVER_NAME'] = 'quart.com'

    @app.route('/', subdomain='<subdomain>')
    def route(subdomain: str) -> str:
        return subdomain

    test_client = app.test_client()
    response = await test_client.get('/', headers={'host': 'sub.quart.com'})
    assert (await response.get_data(raw=False)) == 'sub'


@pytest.mark.parametrize(
    'host_matching, server_name, subdomain, host, error',
    [
        (False, None, 'foo', None, RuntimeError),
        (False, None, None, 'foo', RuntimeError),
        (True, None, 'foo', 'foo', ValueError),
        (True, None, 'foo', None, RuntimeError),
        (True, None, None, None, RuntimeError),
    ],
    ids=[
        'No host matching with subdomain',
        'No host matching with host',
        'Host and subdomain',
        'No server name with subdomain',
        'No host and no server name with host matching',
    ],
)
def test_add_url_rule_host_and_subdomain_errors(
        host_matching: bool, server_name: Optional[str], subdomain: Optional[str],
        host: Optional[str], error: Exception,
) -> None:
    static_host = 'quart.com' if host_matching else None
    app = Quart(__name__, static_host=static_host, host_matching=host_matching)
    app.config['SERVER_NAME'] = server_name

    def route() -> str:
        return ''

    with pytest.raises(error):
        app.add_url_rule('/', view_func=route, subdomain=subdomain, host=host)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'result, expected, raises',
    [
        (None, None, True),
        ((None, 201), None, True),
        (TEST_RESPONSE, TEST_RESPONSE, False),
        (('hello', {'X-Header': 'bob'}), Response('hello', headers={'X-Header': 'bob'}), False),
        (('hello', 201), Response('hello', 201), False),
        (
            ('hello', 201, {'X-Header': 'bob'}),
            Response('hello', 201, headers={'X-Header': 'bob'}), False,
        ),
    ],
)
async def test_make_response(
        result: ResponseReturnValue, expected: Response, raises: bool,
) -> None:
    app = Quart(__name__)
    app.config['RESPONSE_TIMEOUT'] = None
    try:
        response = await app.make_response(result)
    except TypeError:
        if not raises:
            raise
    else:
        assert response.headers.keys() == expected.headers.keys()
        assert response.status_code == expected.status_code
        assert (await response.get_data()) == (await expected.get_data())


@pytest.mark.parametrize(
    'quart_env, quart_debug, expected_env, expected_debug',
    [
        (None, None, 'production', False),
        ('development', None, 'development', True),
        ('development', False, 'development', False),
    ],
)
def test_env_and_debug_environments(
        quart_env: Optional[str], quart_debug: Optional[bool],
        expected_env: bool, expected_debug: bool,
) -> None:
    if quart_env is None:
        os.environ.pop('QUART_ENV', None)
    else:
        os.environ['QUART_ENV'] = quart_env

    if quart_debug is None:
        os.environ.pop('QUART_DEBUG', None)
    else:
        os.environ['QUART_DEBUG'] = str(quart_debug)

    app = Quart(__name__)
    assert app.env == expected_env
    assert app.debug is expected_debug


@pytest.fixture(name='basic_app')
def _basic_app() -> Quart:
    app = Quart(__name__)

    @app.route('/')
    def route() -> str:
        return ''

    @app.route('/exception/')
    def exception() -> str:
        raise Exception()

    return app


@pytest.mark.asyncio
async def test_app_route_exception(basic_app: Quart) -> None:
    test_client = basic_app.test_client()
    response = await test_client.get('/exception/')
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_app_before_request_exception(basic_app: Quart) -> None:
    @basic_app.before_request
    def before() -> None:
        raise Exception()

    test_client = basic_app.test_client()
    response = await test_client.get('/')
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_app_after_request_exception(basic_app: Quart) -> None:
    @basic_app.after_request
    def after(_: Response) -> None:
        raise Exception()

    test_client = basic_app.test_client()
    response = await test_client.get('/')
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_app_after_request_handler_exception(basic_app: Quart) -> None:
    @basic_app.after_request
    def after(_: Response) -> None:
        raise Exception()

    test_client = basic_app.test_client()
    response = await test_client.get('/exception/')
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_app_handle_request_asyncio_cancelled_error() -> None:
    app = Quart(__name__)

    @app.route("/")
    async def index() -> NoReturn:
        raise asyncio.CancelledError()

    request = app.request_class(
        "GET", "http", "/", b"", CIMultiDict(), send_push_promise=no_op_push,
    )
    with pytest.raises(asyncio.CancelledError):
        await app.handle_request(request)


@pytest.mark.asyncio
async def test_app_handle_websocket_asyncio_cancelled_error() -> None:
    app = Quart(__name__)

    @app.websocket("/")
    async def index() -> NoReturn:
        raise asyncio.CancelledError()

    websocket = app.websocket_class(
        "/", b"", "wss", CIMultiDict(), None, None, None, None,
    )
    with pytest.raises(asyncio.CancelledError):
        await app.handle_websocket(websocket)


@pytest.fixture(name='session_app', scope="function")
def _session_app() -> Quart:
    app = Quart(__name__)
    app.session_interface = AsyncMock(spec=SessionInterface)
    app.session_interface.open_session.return_value = SecureCookieSession()  # type: ignore
    app.session_interface.is_null_session.return_value = False  # type: ignore

    @app.route('/')
    async def route() -> str:
        session["a"] = "b"
        return ''

    @app.websocket('/ws/')
    async def ws() -> None:
        session["a"] = "b"
        await websocket.accept()
        await websocket.send("")

    @app.websocket('/ws_return/')
    async def ws_return() -> str:
        session["a"] = "b"
        return ""

    return app


@pytest.mark.asyncio
async def test_app_session(session_app: Quart) -> None:
    test_client = session_app.test_client()
    await test_client.get('/')
    session_app.session_interface.open_session.assert_called()  # type: ignore
    session_app.session_interface.save_session.assert_called()  # type: ignore


@pytest.mark.asyncio
async def test_app_session_websocket(session_app: Quart) -> None:
    test_client = session_app.test_client()
    async with test_client.websocket('/ws/') as test_websocket:
        await test_websocket.receive()
    session_app.session_interface.open_session.assert_called()  # type: ignore
    session_app.session_interface.save_session.assert_not_called()  # type: ignore


@pytest.mark.asyncio
async def test_app_session_websocket_return(session_app: Quart) -> None:
    test_client = session_app.test_client()
    async with test_client.websocket('/ws_return/') as test_websocket:
        with pytest.raises(WebsocketResponse):
            await test_websocket.receive()
    session_app.session_interface.open_session.assert_called()  # type: ignore
    session_app.session_interface.save_session.assert_called()  # type: ignore
