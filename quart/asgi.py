import asyncio
from functools import partial
from typing import AnyStr, Callable, Set, TYPE_CHECKING

from .datastructures import CIMultiDict
from .wrappers import Request, Response, Websocket  # noqa: F401

if TYPE_CHECKING:
    from .app import Quart  # noqa: F401


class ASGIHTTPConnection:

    def __init__(self, app: 'Quart', scope: dict) -> None:
        self.app = app
        self.scope = scope

    async def __call__(self, receive: Callable, send: Callable) -> None:
        request = self._create_request_from_scope()
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

    def _create_request_from_scope(self) -> Request:
        headers = CIMultiDict()
        headers['Remote-Addr'] = (self.scope.get('client') or ['<local>'])[0]
        for name, value in self.scope['headers']:
            headers.add(name.decode().title(), value.decode())
        if self.scope['http_version'] < '1.1':
            headers.setdefault('Host', self.app.config['SERVER_NAME'] or '')

        return self.app.request_class(
            self.scope['method'], self.scope['scheme'], self.scope['path'],
            self.scope['query_string'], headers,
            max_content_length=self.app.config['MAX_CONTENT_LENGTH'],
            body_timeout=self.app.config['BODY_TIMEOUT'],
        )

    async def handle_request(self, request: Request, send: Callable) -> None:
        response = await self.app.handle_request(request)
        try:
            await asyncio.wait_for(self._send_response(send, response), timeout=response.timeout)
        except asyncio.TimeoutError:
            pass

    async def _send_response(self, send: Callable, response: Response) -> None:
        headers = [
            (key.lower().encode(), value.encode())
            for key, value in response.headers.items()
        ]
        await send({
            'type': 'http.response.start',
            'status': response.status_code,
            'headers': headers,
        })

        if 'http.response.push' in self.scope.get('extensions', {}):
            for path in response.push_promises:
                await send({
                    'type': 'http.response.push',
                    'path': path,
                    'headers': [],
                })

        async for data in response.response:
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

        return self.app.websocket_class(
            self.scope['path'], self.scope['query_string'], self.scope['scheme'],
            headers, self.queue.get, partial(self.send_data, send),
            partial(self.accept_connection, send),
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
            async for data in response.response:
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

    async def accept_connection(self, send: Callable) -> None:
        if not self._accepted:
            await send({
                'type': 'websocket.accept',
            })
            self._accepted = True


class ASGILifespan:

    def __init__(self, app: 'Quart', scope: dict) -> None:
        self.app = app

    async def __call__(self, receive: Callable, send: Callable) -> None:
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                await self.app.startup()
                await send({'type': 'lifespan.startup.complete'})
            elif event['type'] == 'lifespan.shutdown':
                await self.app.shutdown()
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
