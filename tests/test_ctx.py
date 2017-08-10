from unittest.mock import Mock

import pytest

from quart.app import Quart
from quart.ctx import (
    _AppCtxGlobals, after_this_request, AppContext, has_app_context, has_request_context,
    RequestContext,
)
from quart.datastructures import CIMultiDict
from quart.exceptions import MethodNotAllowed, NotFound, RedirectRequired
from quart.wrappers import Request


def test_request_context_match() -> None:
    app = Quart(__name__)
    url_adapter = Mock()
    url_adapter.match.return_value = ('Rule', {'arg': 'value'})
    app.create_url_adapter = lambda *_: url_adapter  # type: ignore
    request = Request('GET', '/', CIMultiDict(), None)
    RequestContext(app, request)
    assert request.url_rule == 'Rule'
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
    request = Request('GET', '/', CIMultiDict(), None)
    RequestContext(app, request)
    assert isinstance(request.routing_exception, exception_type)  # type: ignore


def test_after_this_request() -> None:
    with RequestContext(Quart(__name__), Request('GET', '/', CIMultiDict(), None)) as context:
        after_this_request(lambda: 'hello')
        assert context._after_request_functions[0]() == 'hello'


def test_has_request_context() -> None:
    with RequestContext(Quart(__name__), Request('GET', '/', CIMultiDict(), None)):
        assert has_request_context() is True
        assert has_app_context() is True
    assert has_request_context() is False
    assert has_app_context() is False


def test_has_app_context() -> None:
    with AppContext(Quart(__name__)):
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
