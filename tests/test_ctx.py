import asyncio
from unittest.mock import Mock

import pytest

from quart.app import Quart
from quart.ctx import (
    _AppCtxGlobals, after_this_request, AppContext, copy_current_app_context,
    copy_current_request_context, copy_current_websocket_context, has_app_context,
    has_request_context, RequestContext, WebsocketContext,
)
from quart.datastructures import CIMultiDict
from quart.exceptions import BadRequest, MethodNotAllowed, NotFound, RedirectRequired
from quart.globals import g, request, websocket
from quart.routing import Rule
from quart.wrappers import Request, Websocket


def test_request_context_match() -> None:
    app = Quart(__name__)
    url_adapter = Mock()
    rule = Rule('/', ['GET'], 'index')
    url_adapter.match.return_value = (rule, {'arg': 'value'})
    app.create_url_adapter = lambda *_: url_adapter  # type: ignore
    request = Request('GET', '/', CIMultiDict())
    RequestContext(app, request)
    assert request.url_rule == rule
    assert request.view_args == {'arg': 'value'}


@pytest.mark.parametrize(
    'exception_type, exception_instance',
    [
        (MethodNotAllowed, MethodNotAllowed(['GET'])),
        (NotFound, NotFound()),
        (RedirectRequired, RedirectRequired('/')),
    ],
)
def test_request_context_matching_error(
        exception_type: Exception, exception_instance: Exception,
) -> None:
    app = Quart(__name__)
    url_adapter = Mock()
    url_adapter.match.side_effect = exception_instance
    app.create_url_adapter = lambda *_: url_adapter  # type: ignore
    request = Request('GET', '/', CIMultiDict())
    RequestContext(app, request)
    assert isinstance(request.routing_exception, exception_type)  # type: ignore


@pytest.mark.parametrize(
    'request_factory, context_class, is_websocket',
    [  # type: ignore
        (lambda method, path, headers: Request(method, path, headers), RequestContext, True),
        (
            lambda _, path, headers: Websocket(path, headers, Mock(), Mock()),
            WebsocketContext, False,
        ),
    ],
)
def test_bad_request_if_websocket_missmatch(
        request_factory: object, context_class: object, is_websocket: bool,
) -> None:
    app = Quart(__name__)
    url_adapter = Mock()
    url_adapter.match.return_value = Rule('/', ['GET'], 'index', is_websocket=is_websocket), {}
    app.create_url_adapter = lambda *_: url_adapter  # type: ignore
    request_websocket = request_factory('GET', '/', CIMultiDict())  # type: ignore
    context_class(app, request_websocket)  # type: ignore
    assert isinstance(request_websocket.routing_exception, BadRequest)


def test_bad_request_if_websocket_route() -> None:
    app = Quart(__name__)
    url_adapter = Mock()
    url_adapter.match.return_value = Rule('/', ['GET'], 'index', is_websocket=True), {}
    app.create_url_adapter = lambda *_: url_adapter  # type: ignore
    request = Request('GET', '/', CIMultiDict())
    RequestContext(app, request)
    assert isinstance(request.routing_exception, BadRequest)


@pytest.mark.asyncio
async def test_after_this_request() -> None:
    async with RequestContext(Quart(__name__), Request('GET', '/', CIMultiDict())) as context:
        after_this_request(lambda: 'hello')
        assert context._after_request_functions[0]() == 'hello'


@pytest.mark.asyncio
async def test_has_request_context() -> None:
    async with RequestContext(Quart(__name__), Request('GET', '/', CIMultiDict())):
        assert has_request_context() is True
        assert has_app_context() is True
    assert has_request_context() is False
    assert has_app_context() is False


@pytest.mark.asyncio
async def test_has_app_context() -> None:
    async with AppContext(Quart(__name__)):
        assert has_app_context() is True
    assert has_app_context() is False


def test_app_ctx_globals_get() -> None:
    g = _AppCtxGlobals()
    g.foo = 'bar'  # type: ignore
    assert g.get('foo') == 'bar'
    assert g.get('bar', 'something') == 'something'


def test_app_ctx_globals_pop() -> None:
    g = _AppCtxGlobals()
    g.foo = 'bar'  # type: ignore
    assert g.pop('foo') == 'bar'
    assert g.pop('foo', None) is None
    with pytest.raises(KeyError):
        g.pop('foo')


def test_app_ctx_globals_setdefault() -> None:
    g = _AppCtxGlobals()
    g.setdefault('foo', []).append('bar')
    assert g.foo == ['bar']  # type: ignore


def test_app_ctx_globals_contains() -> None:
    g = _AppCtxGlobals()
    g.foo = 'bar'  # type: ignore
    assert 'foo' in g
    assert 'bar' not in g


def test_app_ctx_globals_iter() -> None:
    g = _AppCtxGlobals()
    g.foo = 'bar'  # type: ignore
    g.bar = 'foo'  # type: ignore
    assert sorted(iter(g)) == ['bar', 'foo']  # type: ignore


@pytest.mark.asyncio
async def test_copy_current_app_context() -> None:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> str:
        g.foo = 'bar'  # type: ignore

        @copy_current_app_context
        async def within_context() -> None:
            assert g.foo == 'bar'

        await asyncio.ensure_future(within_context())
        return ''

    test_client = app.test_client()
    response = await test_client.get('/')
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_copy_current_request_context() -> None:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> str:
        @copy_current_request_context
        async def within_context() -> None:
            assert request.path == '/'

        await asyncio.ensure_future(within_context())
        return ''

    test_client = app.test_client()
    response = await test_client.get('/')
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_fails_without_copy_current_request_context() -> None:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> str:
        async def within_context() -> None:
            assert request.path == '/'

        await asyncio.ensure_future(within_context())
        return ''

    test_client = app.test_client()
    response = await test_client.get('/')
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_copy_current_websocket_context() -> None:
    app = Quart(__name__)

    @app.websocket('/')
    async def index() -> None:
        @copy_current_websocket_context
        async def within_context() -> None:
            return websocket.path

        data = await asyncio.ensure_future(within_context())
        await websocket.send(data.encode())

    test_client = app.test_client()
    with test_client.websocket('/') as test_websocket:
        data = await test_websocket.receive()
    assert data == b'/'
