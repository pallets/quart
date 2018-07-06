from contextlib import contextmanager
from http.cookies import SimpleCookie
from typing import Generator

import pytest

from quart.app import Quart
from quart.datastructures import CIMultiDict
from quart.sessions import NullSession, SecureCookieSession, SecureCookieSessionInterface
from quart.wrappers import Request, Response


@contextmanager
def _test_secure_cookie_session(attribute: str) -> Generator[SecureCookieSession, None, None]:
    session = SecureCookieSession({'a': 'b'})
    assert hasattr(session, attribute)
    assert not getattr(session, attribute)
    yield session
    assert getattr(session, attribute)


def test_secure_cookie_access() -> None:
    with _test_secure_cookie_session('accessed') as session:
        _ = session['a']
    with _test_secure_cookie_session('accessed') as session:
        _ = session.get('a')  # noqa: F841


def test_secure_cookie_modification() -> None:
    with _test_secure_cookie_session('modified') as session:
        session.clear()
    with _test_secure_cookie_session('modified') as session:
        session.setdefault('a', [])
    with _test_secure_cookie_session('modified') as session:
        session.update({'a': 'b'})
    with _test_secure_cookie_session('modified') as session:
        session['a'] = 'b'
    with _test_secure_cookie_session('modified') as session:
        session.pop('a', None)
    with _test_secure_cookie_session('modified') as session:
        session.popitem()
    with _test_secure_cookie_session('modified') as session:
        del session['a']
    session = SecureCookieSession({'a': 'b'})
    _ = session['a']  # noqa
    assert not session.modified


def test_null_session_no_modification() -> None:
    session = NullSession()
    with pytest.raises(RuntimeError):
        session.setdefault('a', [])
    with pytest.raises(RuntimeError):
        session.update({'a': 'b'})
    with pytest.raises(RuntimeError):
        session['a'] = 'b'


def test_secure_cookie_session_interface_open_session() -> None:
    session = SecureCookieSession()
    session['something'] = 'else'
    interface = SecureCookieSessionInterface()
    app = Quart(__name__)
    app.secret_key = 'secret'
    response = Response('')
    interface.save_session(app, session, response)
    request = Request('GET', 'http', '/', b'', CIMultiDict())
    request.headers['Cookie'] = response.headers['Set-Cookie']
    new_session = interface.open_session(app, request)
    assert new_session == session


def test_secure_cookie_session_interface_save_session() -> None:
    session = SecureCookieSession()
    session['something'] = 'else'
    interface = SecureCookieSessionInterface()
    app = Quart(__name__)
    app.secret_key = 'secret'
    response = Response('')
    interface.save_session(app, session, response)
    cookies = SimpleCookie()  # type: ignore
    cookies.load(response.headers['Set-Cookie'])
    cookie = cookies[app.session_cookie_name]
    assert cookie['path'] == interface.get_cookie_path(app)
    assert cookie['httponly'] == '' if not interface.get_cookie_httponly(app) else True
    assert cookie['secure'] == '' if not interface.get_cookie_secure(app) else True
    assert cookie['domain'] == (interface.get_cookie_domain(app) or '')
    assert cookie['expires'] == (interface.get_expiration_time(app, session) or '')
    assert response.headers['Vary'] == 'Cookie'


def _save_session(session: SecureCookieSession) -> Response:
    interface = SecureCookieSessionInterface()
    app = Quart(__name__)
    app.secret_key = 'secret'
    response = Response('')
    interface.save_session(app, session, response)
    return response


def test_secure_cookie_session_interface_save_session_no_modification() -> None:
    session = SecureCookieSession()
    session['something'] = 'else'
    session.modified = False
    response = _save_session(session)
    assert response.headers.get('Set-Cookie') is None


def test_secure_cookie_session_interface_save_session_no_access() -> None:
    session = SecureCookieSession()
    session['something'] = 'else'
    session.accessed = False
    session.modified = False
    response = _save_session(session)
    assert response.headers.get('Set-Cookie') is None
    assert response.headers.get('Vary') is None
