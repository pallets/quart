import asyncio
from unittest.mock import Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch

import quart.serving._base
from quart import Quart
from quart.serving import Server
from .helpers import MockTransport


@pytest.fixture()
def serving_app() -> Quart:
    app = Quart(__name__)

    @app.route('/')
    async def index() -> str:
        return 'index'

    @app.websocket('/ws')
    async def ws() -> None:
        return None

    return app


@pytest.mark.asyncio
async def test_invalid_upgrade(
        event_loop: asyncio.AbstractEventLoop, monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(quart.serving._base, 'time', lambda: 1512229395)
    server = Server(Mock(), event_loop, None, '', 5)  # type: ignore
    transport = MockTransport()
    server.connection_made(transport)  # type: ignore
    server.data_received(
        b'GET / HTTP/1.1\r\n'
        b'Host: localhost\r\n'
        b'Upgrade: pigeon\r\n'
        b'\r\n',
    )
    await transport.closed.wait()
    assert transport.data == (
        b'HTTP/1.1 400 \r\ncontent-length: 0\r\nconnection: close\r\n'
        b'date: Sat, 02 Dec 2017 15:43:15 GMT\r\nserver: quart-h11\r\n\r\n'
    )


@pytest.mark.asyncio
async def test_h2c_upgrade(
        serving_app: Quart, event_loop: asyncio.AbstractEventLoop, monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(quart.serving._base, 'time', lambda: 1512229395)
    server = Server(serving_app, event_loop, None, '', 5)  # type: ignore
    transport = MockTransport()
    server.connection_made(transport)  # type: ignore
    server.data_received(
        b'GET / HTTP/1.1\r\n'
        b'Host: localhost\r\n'
        b'Upgrade: h2c\r\n'
        b'\r\n',
    )
    await transport.updated.wait()
    assert transport.data.startswith(
        b'HTTP/1.1 101 \r\nupgrade: h2c\r\n'
        b'date: Sat, 02 Dec 2017 15:43:15 GMT\r\nserver: quart-h11\r\n\r\n'
    )


@pytest.mark.asyncio
async def test_websocket_upgrade(
        serving_app: Quart, event_loop: asyncio.AbstractEventLoop, monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(quart.serving._base, 'time', lambda: 1512229395)
    server = Server(serving_app, event_loop, None, '', 5)  # type: ignore
    transport = MockTransport()
    server.connection_made(transport)  # type: ignore
    server.data_received(
        b'GET /ws HTTP/1.1\r\n'
        b'Host: localhost\r\n'
        b'Upgrade: websocket\r\n'
        b'Connection: Upgrade\r\n'
        b'Sec-WebSocket-Key: NA63HJnrvVYlgKt6wI58Yw==\r\n'
        b'Sec-WebSocket-Version: 13\r\n'
        b'\r\n',
    )
    await transport.updated.wait()
    assert transport.data == (
        b'HTTP/1.1 101 \r\nupgrade: WebSocket\r\nconnection: Upgrade\r\n'
        b'sec-websocket-accept: 3jdXMDZiy2+b842JYmwUB4ilUxc=\r\n\r\n'
    )
