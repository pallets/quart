import asyncio
import warnings
from functools import partial
from typing import Any, AnyStr, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
from urllib.parse import urlparse

from .datastructures import CIMultiDict, Headers
from .wrappers import Request, Response, Websocket  # noqa: F401

if TYPE_CHECKING:
    from .app import Quart  # noqa: F401


class ASGIHTTPConnection:

    def __init__(self, app: 'Quart', scope: dict) -> None:
        self.app = app
        self.scope = scope

    async def __call__(self, receive: Callable, send: Callable) -> None:
        request = self._create_request_from_scope(send)
        receiver_task = asyncio.ensure_future(self.handle_messages(request, receive))
        handler_task = asyncio.ensure_future(self.handle_request(request, send))
        _, pending = await asyncio.wait(
            [handler_task, receiver_task], return_when=asyncio.FIRST_COMPLETED,
        )
        await _cancel_tasks(pending)

    async def handle_messages(self, request: Request, receive: Callable) -> None:
        while True:
            message = await receive()
            if message['type'] == 'http.request':
                request.body.append(message['body'])
                if not message.get('more_body', False):
                    request.body.set_complete()
            elif message['type'] == 'http.disconnect':
                return

    def _create_request_from_scope(self, send: Callable) -> Request:
        headers = CIMultiDict()
        headers['Remote-Addr'] = (self.scope.get('client') or ['<local>'])[0]
        for name, value in self.scope['headers']:
            headers.add(name.decode().title(), value.decode())
        if self.scope['http_version'] < '1.1':
            headers.setdefault('Host', self.app.config['SERVER_NAME'] or '')

        path = self.scope["path"]
        path = path if path[0] == "/" else urlparse(path).path

        return self.app.request_class(
            self.scope['method'], self.scope['scheme'], path,
            self.scope['query_string'], headers,
            max_content_length=self.app.config['MAX_CONTENT_LENGTH'],
            body_timeout=self.app.config['BODY_TIMEOUT'],
            send_push_promise=partial(self._send_push_promise, send),
        )

    async def handle_request(self, request: Request, send: Callable) -> None:
        response = await self.app.handle_request(request)
        try:
            await asyncio.wait_for(self._send_response(send, response), timeout=response.timeout)
        except asyncio.TimeoutError:
            pass

    async def _send_response(self, send: Callable, response: Response) -> None:
        await send({
            'type': 'http.response.start',
            'status': response.status_code,
            'headers': _encode_headers(response.headers),
        })

        async with response.response as body:
            async for data in body:
                await send({
                    'type': 'http.response.body',
                    'body': data,
                    'more_body': True,
                })
        await send({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False,
        })

    async def _send_push_promise(self, send: Callable, path: str, headers: Headers) -> None:
        if 'http.response.push' in self.scope.get('extensions', {}):
            await send({
                'type': 'http.response.push',
                'path': path,
                'headers': _encode_headers(headers),
            })


class ASGIWebsocketConnection:

    def __init__(self, app: 'Quart', scope: dict) -> None:
        self.app = app
        self.scope = scope
        self.queue: asyncio.Queue = asyncio.Queue()
        self._accepted = False

    async def __call__(self, receive: Callable, send: Callable) -> None:
        websocket = self._create_websocket_from_scope(send)
        receiver_task = asyncio.ensure_future(self.handle_messages(receive))
        handler_task = asyncio.ensure_future(self.handle_websocket(websocket, send))
        _, pending = await asyncio.wait(
            [handler_task, receiver_task], return_when=asyncio.FIRST_COMPLETED,
        )
        await _cancel_tasks(pending)

    async def handle_messages(self, receive: Callable) -> None:
        while True:
            event = await receive()
            if event['type'] == 'websocket.receive':
                await self.queue.put(event.get('bytes') or event['text'])
            elif event['type'] == 'websocket.disconnect':
                return

    def _create_websocket_from_scope(self, send: Callable) -> Websocket:
        headers = CIMultiDict()
        headers['Remote-Addr'] = (self.scope.get('client') or ['<local>'])[0]
        for name, value in self.scope['headers']:
            headers.add(name.decode().title(), value.decode())

        path = self.scope["path"]
        path = path if path[0] == "/" else urlparse(path).path

        return self.app.websocket_class(
            path, self.scope['query_string'], self.scope['scheme'],
            headers, self.scope.get('subprotocols', []), self.queue.get,
            partial(self.send_data, send), partial(self.accept_connection, send),
        )

    async def handle_websocket(self, websocket: Websocket, send: Callable) -> None:
        response = await self.app.handle_websocket(websocket)
        if (
                response is not None and not self._accepted
                and 'websocket.http.response' in self.scope.get('extensions', {})
        ):
            headers = [
                (key.lower().encode(), value.encode())
                for key, value in response.headers.items()
            ]
            await send({
                'type': 'websocket.http.response.start',
                'status': response.status_code,
                'headers': headers,
            })
            async with response.response as body:
                async for data in body:
                    await send({
                        'type': 'websocket.http.response.body',
                        'body': data,
                        'more_body': True,
                    })
            await send({
                'type': 'websocket.http.response.body',
                'body': b'',
                'more_body': False,
            })
        elif self._accepted:
            await send({
                'type': 'websocket.close',
                'code': 1000,
            })

    async def send_data(self, send: Callable, data: AnyStr) -> None:
        if isinstance(data, str):
            await send({
                'type': 'websocket.send',
                'text': data,
            })
        else:
            await send({
                'type': 'websocket.send',
                'bytes': data,
            })

    async def accept_connection(
            self, send: Callable, headers: Headers, subprotocol: Optional[str],
    ) -> None:
        if not self._accepted:
            message: Dict[str, Any] = {
                'subprotocol': subprotocol,
                'type': 'websocket.accept',
            }
            spec_version = _convert_version(self.scope.get("asgi", {}).get("spec_version", "2.0"))
            if spec_version > [2, 0]:
                message["headers"] = _encode_headers(headers)
            elif headers:
                warnings.warn("The ASGI Server does not support accept headers, headers not sent")
            await send(message)
            self._accepted = True


class ASGILifespan:

    def __init__(self, app: 'Quart', scope: dict) -> None:
        self.app = app

    async def __call__(self, receive: Callable, send: Callable) -> None:
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                try:
                    await self.app.startup()
                except Exception as error:
                    await send({'type': 'lifespan.startup.failed', "message": str(error)})
                else:
                    await send({'type': 'lifespan.startup.complete'})
            elif event['type'] == 'lifespan.shutdown':
                try:
                    await self.app.shutdown()
                except Exception as error:
                    await send({'type': 'lifespan.shutdown.failed', "message": str(error)})
                else:
                    await send({'type': 'lifespan.shutdown.complete'})
                break


async def _cancel_tasks(tasks: Set[asyncio.Future]) -> None:
    # Cancel any pending, and wait for the cancellation to
    # complete i.e. finish any remaining work.
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    # Raise any unexcepted exceptions
    for task in tasks:
        if not task.cancelled() and task.exception() is not None:
            raise task.exception()


def _encode_headers(headers: Headers) -> List[Tuple[bytes, bytes]]:
    return [
        (key.lower().encode(), value.encode())
        for key, value in headers.items()
    ]


def _convert_version(raw: str) -> List[int]:
    return list(map(int, raw.split(".")))
