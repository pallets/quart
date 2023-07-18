from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from http.cookiejar import CookieJar
from types import TracebackType
from typing import Any, AnyStr, AsyncGenerator, TYPE_CHECKING
from urllib.request import Request as U2Request

from werkzeug.datastructures import Authorization, Headers
from werkzeug.http import dump_cookie

from .connections import TestHTTPConnection, TestWebsocketConnection
from .utils import (
    make_test_body_with_headers,
    make_test_headers_path_and_query_string,
    make_test_scope,
    sentinel,
)
from ..datastructures import FileStorage
from ..globals import _cv_request
from ..sessions import SessionMixin
from ..typing import TestHTTPConnectionProtocol, TestWebsocketConnectionProtocol
from ..wrappers import Response

if TYPE_CHECKING:
    from ..app import Quart  # noqa


class _TestWrapper:
    def __init__(self, headers: Headers) -> None:
        self.headers = headers

    def get_all(self, name: str, default: Any | None = None) -> list[str]:
        name = name.lower()
        result = []
        for key, value in self.headers:
            if key.lower() == name:
                result.append(value)
        return result or default or []


class _TestCookieJarResponse:
    def __init__(self, headers: Headers) -> None:
        self.headers = headers

    def info(self) -> _TestWrapper:
        return _TestWrapper(self.headers)


class QuartClient:
    http_connection_class: type[TestHTTPConnectionProtocol]
    websocket_connection_class: type[TestWebsocketConnectionProtocol]

    http_connection_class = TestHTTPConnection
    websocket_connection_class = TestWebsocketConnection

    def __init__(self, app: Quart, use_cookies: bool = True) -> None:
        self.app = app
        self.cookie_jar: CookieJar | None
        if use_cookies:
            self.cookie_jar = CookieJar()
        else:
            self.cookie_jar = None
        self.preserve_context = False
        self.push_promises: list[tuple[str, Headers]] = []

    async def open(
        self,
        path: str,
        *,
        method: str = "GET",
        headers: dict | Headers | None = None,
        data: AnyStr | None = None,
        form: dict | None = None,
        files: dict[str, FileStorage] | None = None,
        query_string: dict | None = None,
        json: Any = sentinel,
        scheme: str = "http",
        follow_redirects: bool = False,
        root_path: str = "",
        http_version: str = "1.1",
        scope_base: dict | None = None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> Response:
        self.push_promises = []
        response = await self._make_request(
            path,
            method,
            headers,
            data,
            form,
            files,
            query_string,
            json,
            scheme,
            root_path,
            http_version,
            scope_base,
            auth,
            subdomain,
        )
        if follow_redirects:
            while response.status_code >= 300 and response.status_code <= 399:
                # Most browsers respond to an HTTP 302 with a GET request to the new location,
                # despite what the HTTP spec says. HTTP 303 should always be responded to with
                # a GET request.
                if response.status_code == 302 or response.status_code == 303:
                    method = "GET"
                response = await self._make_request(
                    response.location,
                    method,
                    headers,
                    data,
                    form,
                    files,
                    query_string,
                    json,
                    scheme,
                    root_path,
                    http_version,
                    scope_base,
                    auth,
                    subdomain,
                )
        if self.preserve_context:
            _cv_request.set(self.app._preserved_context)  # type: ignore
        return response

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        headers: dict | Headers | None = None,
        query_string: dict | None = None,
        scheme: str = "http",
        root_path: str = "",
        http_version: str = "1.1",
        scope_base: dict | None = None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> TestHTTPConnectionProtocol:
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app,
            path,
            headers,
            query_string,
            auth,
            subdomain,
        )
        if self.cookie_jar is not None:
            for cookie in self.cookie_jar:
                headers.add("cookie", f"{cookie.name}={cookie.value}")
        scope = make_test_scope(
            "http",
            path,
            method,
            headers,
            query_string_bytes,
            scheme,
            root_path,
            http_version,
            scope_base,
            _preserve_context=self.preserve_context,
        )
        return self.http_connection_class(self.app, scope, _preserve_context=self.preserve_context)

    def websocket(
        self,
        path: str,
        *,
        headers: dict | Headers | None = None,
        query_string: dict | None = None,
        scheme: str = "ws",
        subprotocols: list[str] | None = None,
        root_path: str = "",
        http_version: str = "1.1",
        scope_base: dict | None = None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> TestWebsocketConnectionProtocol:
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app,
            path,
            headers,
            query_string,
            auth,
            subdomain,
        )
        if self.cookie_jar is not None:
            for cookie in self.cookie_jar:
                headers.add("cookie", f"{cookie.name}={cookie.value}")
        scope = make_test_scope(
            "websocket",
            path,
            "GET",
            headers,
            query_string_bytes,
            scheme,
            root_path,
            http_version,
            scope_base,
            _preserve_context=self.preserve_context,
        )
        return self.websocket_connection_class(self.app, scope)

    async def delete(self, *args: Any, **kwargs: Any) -> Response:
        """Make a DELETE request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="DELETE", **kwargs)

    async def get(self, *args: Any, **kwargs: Any) -> Response:
        """Make a GET request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="GET", **kwargs)

    async def head(self, *args: Any, **kwargs: Any) -> Response:
        """Make a HEAD request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="HEAD", **kwargs)

    async def options(self, *args: Any, **kwargs: Any) -> Response:
        """Make a OPTIONS request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="OPTIONS", **kwargs)

    async def patch(self, *args: Any, **kwargs: Any) -> Response:
        """Make a PATCH request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="PATCH", **kwargs)

    async def post(self, *args: Any, **kwargs: Any) -> Response:
        """Make a POST request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="POST", **kwargs)

    async def put(self, *args: Any, **kwargs: Any) -> Response:
        """Make a PUT request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="PUT", **kwargs)

    async def trace(self, *args: Any, **kwargs: Any) -> Response:
        """Make a TRACE request.

        See :meth:`~quart.testing.QuartClient.open` for argument
        details.
        """
        return await self.open(*args, method="TRACE", **kwargs)

    def set_cookie(
        self,
        server_name: str,
        key: str,
        value: str = "",
        max_age: int | timedelta | None = None,
        expires: int | float | datetime | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str = None,
    ) -> None:
        """Set a cookie in the cookie jar.

        The arguments are the standard cookie morsels and this is a
        wrapper around the stdlib SimpleCookie code.
        """
        cookie = dump_cookie(
            key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )
        self.cookie_jar.extract_cookies(
            _TestCookieJarResponse(Headers([("set-cookie", cookie)])),  # type: ignore
            U2Request(f"http://{server_name}{path}"),
        )

    def delete_cookie(
        self, server_name: str, key: str, path: str = "/", domain: str | None = None
    ) -> None:
        """Delete a cookie (set to expire immediately)."""
        self.set_cookie(server_name, key, expires=0, max_age=0, path=path, domain=domain)

    @asynccontextmanager
    async def session_transaction(
        self,
        path: str = "/",
        *,
        method: str = "GET",
        headers: dict | Headers | None = None,
        query_string: dict | None = None,
        scheme: str = "http",
        data: AnyStr | None = None,
        form: dict | None = None,
        json: Any = sentinel,
        root_path: str = "",
        http_version: str = "1.1",
        auth: Authorization | tuple[str, str] | None = None,
    ) -> AsyncGenerator[SessionMixin, None]:
        if self.cookie_jar is None:
            raise RuntimeError("Session transactions only make sense with cookies enabled.")

        if headers is None:
            headers = Headers()
        elif isinstance(headers, Headers):
            headers = headers
        elif headers is not None:
            headers = Headers(headers)
        for cookie in self.cookie_jar:
            headers.add("cookie", f"{cookie.name}={cookie.value}")

        original_request_ctx = _cv_request.get(None)
        async with self.app.test_request_context(
            path,
            method=method,
            headers=headers,
            query_string=query_string,
            scheme=scheme,
            data=data,
            form=form,
            json=json,
            root_path=root_path,
            http_version=http_version,
            auth=auth,
        ) as ctx:
            session_interface = self.app.session_interface
            session = await session_interface.open_session(self.app, ctx.request)
            if session is None:
                raise RuntimeError("Error opening the session. Check the secret_key?")

            token = _cv_request.set(original_request_ctx)
            try:
                yield session
            finally:
                _cv_request.reset(token)

            response = self.app.response_class(b"")
            if not session_interface.is_null_session(session):
                await session_interface.save_session(self.app, session, response)
            self.cookie_jar.extract_cookies(
                _TestCookieJarResponse(response.headers),  # type: ignore
                U2Request(ctx.request.url),
            )

    async def __aenter__(self) -> QuartClient:
        if self.preserve_context:
            raise RuntimeError("Cannot nest client invocations")
        self.preserve_context = True
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        self.preserve_context = False

        while True:
            top = _cv_request.get(None)

            if top is not None and top.preserved:
                await top.pop(None)
            else:
                break

    async def _make_request(
        self,
        path: str,
        method: str,
        headers: dict | Headers | None,
        data: AnyStr | None,
        form: dict | None,
        files: dict[str, FileStorage] | None,
        query_string: dict | None,
        json: Any,
        scheme: str,
        root_path: str,
        http_version: str,
        scope_base: dict | None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> Response:
        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app, path, headers, query_string, auth, subdomain
        )
        request_data, body_headers = make_test_body_with_headers(
            data=data, form=form, files=files, json=json, app=self.app
        )
        headers.update(**body_headers)

        if self.cookie_jar is not None:
            for cookie in self.cookie_jar:
                headers.add("cookie", f"{cookie.name}={cookie.value}")

        scope = make_test_scope(
            "http",
            path,
            method,
            headers,
            query_string_bytes,
            scheme,
            root_path,
            http_version,
            scope_base,
            _preserve_context=self.preserve_context,
        )
        async with self.http_connection_class(
            self.app, scope, _preserve_context=self.preserve_context
        ) as connection:
            await connection.send(request_data)
            await connection.send_complete()
        response = await connection.as_response()
        if self.cookie_jar is not None:
            self.cookie_jar.extract_cookies(
                _TestCookieJarResponse(response.headers),  # type: ignore
                U2Request(f"{scheme}://{headers['host']}{path}"),
            )
        self.push_promises.extend(connection.push_promises)
        return response
