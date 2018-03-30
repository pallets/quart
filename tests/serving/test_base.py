import asyncio
from unittest.mock import Mock

import pytest

from quart.serving._base import HTTPServer, RequestResponseServer
from .helpers import MockTransport


@pytest.mark.asyncio
async def test_http_server_drain(event_loop: asyncio.AbstractEventLoop) -> None:
    transport = MockTransport()
    server = HTTPServer(event_loop, transport, Mock(), '')  # type: ignore
    server.pause_writing()

    async def write() -> None:
        server.write(b'Pre drain')
        await server.drain()
        server.write(b'Post drain')

    asyncio.ensure_future(write())
    await transport.updated.wait()
    assert transport.data == b'Pre drain'
    transport.clear()
    server.resume_writing()
    await transport.updated.wait()
    assert transport.data == b'Post drain'


@pytest.mark.asyncio
async def test_timeout(event_loop: asyncio.AbstractEventLoop) -> None:
    timeout = 0.1
    protocol = RequestResponseServer(
        Mock(), event_loop, Mock(), None, '', '', timeout,
    )
    await asyncio.sleep(0.5 * timeout)
    protocol.transport.close.assert_not_called()  # type: ignore
    await asyncio.sleep(2 * timeout)
    protocol.transport.close.assert_called_once()  # type: ignore
