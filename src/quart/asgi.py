from __future__ import annotations

import asyncio
import warnings
from functools import partial
from functools import wraps
from typing import cast
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from hypercorn.typing import ASGIReceiveCallable
from hypercorn.typing import ASGISendCallable
from hypercorn.typing import ASGISendEvent
from hypercorn.typing import HTTPResponseBodyEvent
from hypercorn.typing import HTTPResponseStartEvent
from hypercorn.typing import HTTPScope
from hypercorn.typing import LifespanScope
from hypercorn.typing import LifespanShutdownCompleteEvent
from hypercorn.typing import LifespanShutdownFailedEvent
from hypercorn.typing import LifespanStartupCompleteEvent
from hypercorn.typing import LifespanStartupFailedEvent
from hypercorn.typing import WebsocketAcceptEvent
from hypercorn.typing import WebsocketCloseEvent
from hypercorn.typing import WebsocketResponseBodyEvent
from hypercorn.typing import WebsocketResponseStartEvent
from hypercorn.typing import WebsocketScope
from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response as WerkzeugResponse

from .debug import traceback_response
from .signals import websocket_received
from .signals import websocket_sent
from .typing import ResponseTypes
from .utils import encode_headers
from .wrappers import Request  # noqa: F401
from .wrappers import Response  # noqa: F401
from .wrappers import Websocket  # noqa: F401
from .wrappers.base import ClientDisconnectedError

if TYPE_CHECKING:
    from .app import Quart  # noqa: F401


class ASGIHTTPConnection:
    def __init__(self, app: Quart, scope: HTTPScope) -> None:
        self.app = app
        self.scope = scope
        self._disconnected = False

    async def __call__(
        self, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        send = _convert_os_error(send)
        request = self._create_request_from_scope(send)
        async with asyncio.TaskGroup() as task_group:
            request_task = task_group.create_task(self.handle_request(request, send))
            task_group.create_task(self.handle_messages(request, receive, request_task))

    async def handle_messages(
        self, request: Request, receive: ASGIReceiveCallable, request_task: asyncio.Task
    ) -> None:
        while True:
            message = await receive()
            if message["type"] == "http.request":
                await request.body.put(message.get("body", b""))
                if not message.get("more_body", False):
                    request.body.set_complete()
            elif message["type"] == "http.disconnect":
                self._disconnected = True
                request.body.disconnect()
                request_task.cancel()
                return

    def _create_request_from_scope(self, send: ASGISendCallable) -> Request:
        headers = Headers()
        headers["Remote-Addr"] = (self.scope.get("client") or ["<local>"])[0]
        for name, value in self.scope["headers"]:
            headers.add(name.decode("latin1").title(), value.decode("latin1"))
        if self.scope["http_version"] < "1.1":
            headers.setdefault("Host", self.app.config["SERVER_NAME"] or "")

        path = self.scope["path"]
        path = path if path[0] == "/" else urlparse(path).path
        root_path = self.scope.get("root_path", "")
        if root_path != "":
            path = _normalise_path(path, root_path)

        return self.app.request_class(
            self.scope["method"],
            self.scope["scheme"],
            path,
            self.scope["query_string"],
            headers,
            self.scope.get("root_path", ""),
            self.scope["http_version"],
            max_content_length=self.app.config["MAX_CONTENT_LENGTH"],
            body_timeout=self.app.config["BODY_TIMEOUT"],
            send_push_promise=partial(self._send_push_promise, send),
            scope=self.scope,
        )

    async def handle_request(self, request: Request, send: ASGISendCallable) -> None:
        try:
            response = await self.app.handle_request(request)
        except ClientDisconnectedError:
            return
        except Exception as error:
            response = await _handle_exception(self.app, error)

        if isinstance(response, Response) and response.timeout != Ellipsis:
            timeout = cast(float | None, response.timeout)
        else:
            timeout = self.app.config["RESPONSE_TIMEOUT"]
        try:
            await asyncio.wait_for(self._send_response(send, response), timeout=timeout)
        except TimeoutError:
            pass

    async def _send_response(
        self, send: ASGISendCallable, response: ResponseTypes
    ) -> None:
        if self._disconnected:
            raise ClientDisconnectedError()
        await send(
            cast(
                HTTPResponseStartEvent,
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": encode_headers(response.headers),
                },
            )
        )

        if isinstance(response, WerkzeugResponse):
            for data in response.response:
                body = data.encode() if isinstance(data, str) else data
                await send(
                    cast(
                        HTTPResponseBodyEvent,
                        {"type": "http.response.body", "body": body, "more_body": True},
                    )
                )
        else:
            async with response.response as response_body:
                async for data in response_body:
                    body = data.encode() if isinstance(data, str) else data
                    await send(
                        cast(
                            HTTPResponseBodyEvent,
                            {
                                "type": "http.response.body",
                                "body": body,
                                "more_body": True,
                            },
                        )
                    )
        await send(
            cast(
                HTTPResponseBodyEvent,
                {"type": "http.response.body", "body": b"", "more_body": False},
            )
        )

    async def _send_push_promise(
        self, send: ASGISendCallable, path: str, headers: Headers
    ) -> None:
        if self._disconnected:
            raise ClientDisconnectedError()
        extensions = self.scope.get("extensions", {}) or {}
        if "http.response.push" in extensions:
            await send(
                {
                    "type": "http.response.push",
                    "path": path,
                    "headers": encode_headers(headers),
                }
            )


class ASGIWebsocketConnection:
    def __init__(self, app: Quart, scope: WebsocketScope) -> None:
        self.app = app
        self.scope = scope
        self._accepted = False
        self._closed = False
        self._disconnected = False

    async def __call__(
        self, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        send = _convert_os_error(send)
        websocket = self._create_websocket_from_scope(send)
        async with asyncio.TaskGroup() as task_group:
            websocket_task = task_group.create_task(
                self.handle_websocket(websocket, send)
            )
            task_group.create_task(
                self.handle_messages(websocket, receive, websocket_task)
            )

    async def handle_messages(
        self,
        websocket: Websocket,
        receive: ASGIReceiveCallable,
        websocket_task: asyncio.Task,
    ) -> None:
        while True:
            event = await receive()
            if event["type"] == "websocket.receive":
                message = event.get("bytes") or event["text"]
                await websocket_received.send_async(message)
                await websocket.buffer.put(message)
            elif event["type"] == "websocket.disconnect":
                self._disconnected = True
                websocket.buffer.disconnect()
                websocket_task.cancel()
                return

    def _create_websocket_from_scope(self, send: ASGISendCallable) -> Websocket:
        headers = Headers()
        headers["Remote-Addr"] = (self.scope.get("client") or ["<local>"])[0]
        for name, value in self.scope["headers"]:
            headers.add(name.decode("latin1").title(), value.decode("latin1"))

        path = self.scope["path"]
        path = path if path[0] == "/" else urlparse(path).path
        root_path = self.scope.get("root_path", "")
        if root_path != "":
            path = _normalise_path(path, root_path)

        return self.app.websocket_class(
            path,
            self.scope["query_string"],
            self.scope["scheme"],
            headers,
            self.scope.get("root_path", ""),
            self.scope.get("http_version", "1.1"),
            list(self.scope.get("subprotocols", [])),
            partial(self.send_data, send),
            partial(self.accept_connection, send),
            partial(self.close_connection, send),
            scope=self.scope,
        )

    async def handle_websocket(
        self, websocket: Websocket, send: ASGISendCallable
    ) -> None:
        try:
            response = await self.app.handle_websocket(websocket)
        except ClientDisconnectedError:
            return
        except Exception as error:
            response = await _handle_exception(self.app, error)

        if response is not None and not self._accepted:
            extensions = self.scope.get("extensions", {}) or {}
            if "websocket.http.response" in extensions:
                headers = [
                    (key.lower().encode(), value.encode())
                    for key, value in response.headers.items()
                ]
                await send(
                    cast(
                        WebsocketResponseStartEvent,
                        {
                            "type": "websocket.http.response.start",
                            "status": response.status_code,
                            "headers": headers,
                        },
                    )
                )
                if isinstance(response, WerkzeugResponse):
                    for data in response.response:
                        await send(
                            cast(
                                WebsocketResponseBodyEvent,
                                {
                                    "type": "websocket.http.response.body",
                                    "body": data,
                                    "more_body": True,
                                },
                            )
                        )
                elif isinstance(response, Response):
                    async with response.response as body:
                        async for data in body:
                            await send(
                                cast(
                                    WebsocketResponseBodyEvent,
                                    {
                                        "type": "websocket.http.response.body",
                                        "body": data,
                                        "more_body": True,
                                    },
                                )
                            )
                await send(
                    cast(
                        WebsocketResponseBodyEvent,
                        {
                            "type": "websocket.http.response.body",
                            "body": b"",
                            "more_body": False,
                        },
                    )
                )
            elif not self._closed:
                await send(
                    cast(WebsocketCloseEvent, {"type": "websocket.close", "code": 1000})
                )
        elif self._accepted and not self._closed:
            await send(
                cast(WebsocketCloseEvent, {"type": "websocket.close", "code": 1000})
            )

    async def send_data(self, send: ASGISendCallable, data: str | bytes) -> None:
        if self._disconnected:
            raise ClientDisconnectedError()
        if isinstance(data, str):
            await send({"type": "websocket.send", "bytes": None, "text": data})
        else:
            await send({"type": "websocket.send", "bytes": data, "text": None})
        await websocket_sent.send_async(data)

    async def accept_connection(
        self, send: ASGISendCallable, headers: Headers, subprotocol: str | None
    ) -> None:
        if not self._accepted:
            message: WebsocketAcceptEvent = {
                "headers": [],
                "subprotocol": subprotocol,
                "type": "websocket.accept",
            }
            spec_version = _convert_version(
                self.scope.get("asgi", {}).get("spec_version", "2.0")
            )
            if spec_version > [2, 0]:
                message["headers"] = encode_headers(headers)
            elif headers:
                warnings.warn(
                    "The ASGI Server does not support accept headers, headers not sent",
                    stacklevel=1,
                )
            self._accepted = True
            await send(message)

    async def close_connection(
        self, send: ASGISendCallable, code: int, reason: str
    ) -> None:
        if self._closed:
            raise RuntimeError("Cannot close websocket multiple times")

        spec_version = _convert_version(
            self.scope.get("asgi", {}).get("spec_version", "2.0")
        )
        if spec_version >= [2, 3]:
            await send({"type": "websocket.close", "code": code, "reason": reason})
        else:
            await send({"type": "websocket.close", "code": code})  # type: ignore
        self._closed = True


class ASGILifespan:
    def __init__(self, app: Quart, scope: LifespanScope) -> None:
        self.app = app

    async def __call__(
        self, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        while True:
            event = await receive()
            if event["type"] == "lifespan.startup":
                try:
                    await self.app.startup()
                except Exception as error:
                    await send(
                        cast(
                            LifespanStartupFailedEvent,
                            {"type": "lifespan.startup.failed", "message": str(error)},
                        ),
                    )
                else:
                    await send(
                        cast(
                            LifespanStartupCompleteEvent,
                            {"type": "lifespan.startup.complete"},
                        )
                    )
            elif event["type"] == "lifespan.shutdown":
                try:
                    await self.app.shutdown()
                except Exception as error:
                    await send(
                        cast(
                            LifespanShutdownFailedEvent,
                            {"type": "lifespan.shutdown.failed", "message": str(error)},
                        ),
                    )
                else:
                    await send(
                        cast(
                            LifespanShutdownCompleteEvent,
                            {"type": "lifespan.shutdown.complete"},
                        ),
                    )
                break


def _convert_version(raw: str) -> list[int]:
    return list(map(int, raw.split(".")))


async def _handle_exception(app: Quart, error: Exception) -> Response:
    show_error = app.debug or app.testing
    if show_error:
        return await traceback_response(error)
    else:
        raise error


def _normalise_path(path: str, root_path: str) -> str:
    if path == root_path or not path.startswith(root_path):
        return " "  # Invalid in paths, hence will result in 404

    return path.removeprefix(root_path)


def _convert_os_error(send: ASGISendCallable) -> ASGISendCallable:
    @wraps(send)
    async def new_send(message: ASGISendEvent) -> None:
        try:
            await send(message)
        except OSError:
            raise ClientDisconnectedError() from None

    return new_send
