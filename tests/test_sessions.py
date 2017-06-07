from contextlib import contextmanager
from typing import Any, Generator

import hypothesis.strategies as strategies
import pytest
from hypothesis import given

from quart.app import Quart
from quart.sessions import (
    NullSession, SecureCookieSession, SecureCookieSessionInterface, TaggedJSONSerializer,
)
from quart.wrappers import Response


@given(
    value=strategies.one_of(
        strategies.datetimes(), strategies.uuids(), strategies.binary(),
        strategies.tuples(strategies.integers()),
    ),
)
def test_jsonserializer(value: Any) -> None:
    serializer = TaggedJSONSerializer()
    assert serializer.loads(serializer.dumps(value)) == value


@contextmanager
def _test_secure_cookie_session() -> Generator[SecureCookieSession, None, None]:
    session = SecureCookieSession({'a': 'b'})
    assert not session.modified
    yield session
    assert session.modified


def test_secure_cookie_modification() -> None:
    with _test_secure_cookie_session() as session:
        session.clear()
    with _test_secure_cookie_session() as session:
        session.setdefault('a', [])
    with _test_secure_cookie_session() as session:
        session.update({'a': 'b'})
    with _test_secure_cookie_session() as session:
        session['a'] = 'b'
    with _test_secure_cookie_session() as session:
        session.pop('a', None)
    with _test_secure_cookie_session() as session:
        session.popitem()
    with _test_secure_cookie_session() as session:
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


def test_secure_cookie_session_interface_save_session() -> None:
    session = SecureCookieSession()
    session['something'] = 'else'
    interface = SecureCookieSessionInterface()
    app = Quart(__name__)
    app.secret_key = 'secret'
    response = Response('')
    interface.save_session(app, session, response)
    assert response.headers['Set-Cookie']
