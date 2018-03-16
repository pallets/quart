import asyncio

import h11
import pytest

from quart import Quart
from quart.serving.websocket import WebsocketServer
from .helpers import MockTransport


@pytest.fixture()
def serving_app() -> Quart:
    app = Quart(__name__)

    @app.websocket('/ws')
    async def ws() -> None:
        return None

    return app


@pytest.mark.asyncio
async def test_not_found(
    serving_app: Quart, event_loop: asyncio.AbstractEventLoop,
) -> None:
    transport = MockTransport()
    request = h11.Request(
        method='GET', target='/not/', headers=[
            ('host', 'quart.com'), ('connection', 'upgrade'), ('upgrade', 'websocket'),
            ('Sec-WebSocket-Key', 'NA63HJnrvVYlgKt6wI58Yw=='), ('Sec-WebSocket-Version', '13'),
        ],
    )
    WebsocketServer(serving_app, event_loop, transport, request)  # type: ignore
    await transport.closed.wait()
    assert transport.data.startswith(b'HTTP/1.1 404')
