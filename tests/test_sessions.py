from __future__ import annotations

from http.cookies import SimpleCookie

from hypercorn.typing import HTTPScope
from werkzeug.datastructures import Headers

from quart.app import Quart
from quart.sessions import SecureCookieSession
from quart.sessions import SecureCookieSessionInterface
from quart.testing import no_op_push
from quart.wrappers import Request
from quart.wrappers import Response


async def test_secure_cookie_session_interface_open_session(
    http_scope: HTTPScope,
) -> None:
    session = SecureCookieSession()
    session["something"] = "else"
    interface = SecureCookieSessionInterface()
    app = Quart(__name__)
    app.secret_key = "secret"
    response = Response("")
    await interface.save_session(app, session, response)
    request = Request(
        "GET",
        "http",
        "/",
        b"",
        Headers(),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )
    request.headers["Cookie"] = response.headers["Set-Cookie"]
    new_session = await interface.open_session(app, request)
    assert new_session == session


async def test_secure_cookie_session_interface_save_session() -> None:
    session = SecureCookieSession()
    session["something"] = "else"
    interface = SecureCookieSessionInterface()
    app = Quart(__name__)
    app.secret_key = "secret"
    response = Response("")
    await interface.save_session(app, session, response)
    cookies: SimpleCookie = SimpleCookie()
    cookies.load(response.headers["Set-Cookie"])
    cookie = cookies[app.config["SESSION_COOKIE_NAME"]]
    assert cookie["path"] == interface.get_cookie_path(app)
    assert cookie["httponly"] == "" if not interface.get_cookie_httponly(app) else True
    assert cookie["secure"] == "" if not interface.get_cookie_secure(app) else True
    assert cookie["samesite"] == (interface.get_cookie_samesite(app) or "")
    assert cookie["domain"] == (interface.get_cookie_domain(app) or "")
    assert cookie["expires"] == (interface.get_expiration_time(app, session) or "")
    assert response.headers["Vary"] == "Cookie"


async def _save_session(session: SecureCookieSession) -> Response:
    interface = SecureCookieSessionInterface()
    app = Quart(__name__)
    app.secret_key = "secret"
    response = Response("")
    await interface.save_session(app, session, response)
    return response


async def test_secure_cookie_session_interface_save_session_no_modification() -> None:
    session = SecureCookieSession()
    session["something"] = "else"
    session.modified = False
    response = await _save_session(session)
    assert response.headers.get("Set-Cookie") is None


async def test_secure_cookie_session_interface_save_session_no_access() -> None:
    session = SecureCookieSession()
    session["something"] = "else"
    session.accessed = False
    session.modified = False
    response = await _save_session(session)
    assert response.headers.get("Set-Cookie") is None
    assert response.headers.get("Vary") is None
