import asyncio
from functools import partial
from typing import Callable, Optional, TYPE_CHECKING

from ._base import response_headers, Stream, suppress_body
from ..datastructures import CIMultiDict
from ..wrappers import Response, Websocket  # noqa: F401

if TYPE_CHECKING:
    from ..app import Quart  # noqa: F401


class ASGIServer:

    def __init__(self, app: 'Quart') -> None:
        self.app = app

    def __call__(self, scope: dict) -> Callable:
        if scope['type'] == 'http':
            return ASGIHTTPConnection(self.app, scope)
        elif scope['type'] == 'websocket':
            return ASGIWebsocketConnection(self.app, scope)
        else:
            raise RuntimeError('ASGI Scope type is unknown')


class ASGIHTTPConnection:

    def __init__(self, app: 'Quart', scope: dict) -> None:
        self.app = app
        self.scope = scope
        self.stream: Optional[Stream] = None

    async def __call__(self, receive: Callable, send: Callable) -> None:
        event = await receive()
        if event['type'] == 'http.request':
            if self.stream is None:
                headers = CIMultiDict()
                headers['Remote-Addr'] = self.scope['client'][0]
                for name, value in self.scope['headers']:
                    headers.add(name.decode().title(), value.decode())

                request = self.app.request_class(
                    self.scope['method'], self.scope['scheme'],
                    f"{self.scope['path']}?{self.scope['query_string']}", headers,
                    max_content_length=self.app.config['MAX_CONTENT_LENGTH'],
                    body_timeout=self.app.config['BODY_TIMEOUT'],
                )
                self.stream = Stream(asyncio.get_event_loop(), request)
                # It is important that the app handles the request in a unique
                # task as the globals are task locals
                self.stream.task = asyncio.ensure_future(self._handle_request(send))
                self.stream.task.add_done_callback(_cleanup_task)

            self.stream.append(event['body'])
            if not event.get('more_body', False):
                self.stream.complete()

    async def _handle_request(self, send: Callable) -> None:
        response = await self.app.handle_request(self.stream.request)
        suppress_body_ = suppress_body(self.stream.request.method, response.status_code)
        try:
            await asyncio.wait_for(
                self._send_response(send, response, suppress_body_),
                timeout=response.timeout,
            )
        except asyncio.TimeoutError:
            pass

    async def _send_response(
            self, send: Callable, response: Response, suppress_body: bool,
    ) -> None:
        headers = [
            [key.lower().encode(), value.lower().encode()]
            for key, value in response.headers.items()
        ]
        headers.extend((
            [key.lower().encode(), value.lower().encode()]
            for key, value in response_headers('asgi')
        ))
        await send({
            'type': 'http.response.start',
            'status': response.status_code,
            'headers': headers,
        })
        if not suppress_body:
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
        self.task: Optional[asyncio.Future] = None

    async def __call__(self, receive: Callable, send: Callable) -> None:
        while True:
            event = await receive()
            if event['type'] == 'websocket.connect':
                headers = CIMultiDict()
                headers['Remote-Addr'] = self.scope['client'][0]
                for name, value in self.scope['headers']:
                    headers.add(name.decode().title(), value.decode())

                websocket = self.app.websocket_class(
                    f"{self.scope['path']}?{self.scope['query_string']}", self.scope['scheme'],
                    headers, self.queue, partial(self.send_data, send),
                    partial(self.accept_connection, send),
                )
                self.task = asyncio.ensure_future(self.handle_websocket(websocket, send))
                self.task.add_done_callback(_cleanup_task)
            elif event['type'] == 'websocket.receive':
                await self.queue.put(event.get('bytes') or event['text'])
            elif event['type'] == 'websocket.disconnect':
                self.task.cancel()

    async def handle_websocket(self, websocket: Websocket, send: Callable) -> None:
        await self.app.handle_websocket(websocket)
        await send({
            'type': 'websocket.close',
        })

    async def send_data(self, send: Callable, data: bytes) -> None:
        await send({
            'type': 'websocket.send',
            'bytes': data,
        })

    async def accept_connection(self, send: Callable) -> None:
        await send({
            'type': 'websocket.accept',
        })


def _cleanup_task(future: asyncio.Future) -> None:
    """Call after a task (future) to clean up.

    This should be added as a add_done_callback for any protocol task
    to ensure that the proper cleanup is handled on cancellation
    i.e. early connection closing.
    """
    # Fetch the exception (if exists) from the future, without
    # this asyncio will print annoying warnings.
    try:
        future.exception()
    except Exception as error:
        pass
