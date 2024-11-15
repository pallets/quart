import asyncio

from chat import app

from quart.testing.connections import (
    TestWebsocketConnection as _TestWebsocketConnection,
)


async def _receive(test_websocket: _TestWebsocketConnection) -> str:
    return await test_websocket.receive()


async def test_websocket() -> None:
    test_client = app.test_client()
    async with test_client.websocket("/ws") as test_websocket:
        task = asyncio.ensure_future(_receive(test_websocket))
        await test_websocket.send("message")
        result = await task
        assert result == "message"
