from __future__ import annotations

import asyncio
import time

from quart import current_app, Quart


async def test_background_task() -> None:
    app = Quart(__name__)
    app.config["DATA"] = "data"

    data = None

    async def background() -> None:
        nonlocal data
        await asyncio.sleep(0.5)
        data = current_app.config["DATA"]

    @app.route("/")
    async def index() -> str:
        app.add_background_task(background)
        return ""

    async with app.test_app():
        test_client = app.test_client()
        await test_client.get("/")

    assert data == "data"


async def test_sync_background_task() -> None:
    app = Quart(__name__)
    app.config["DATA"] = "data"

    data = None

    def background() -> None:
        nonlocal data
        time.sleep(0.5)
        data = current_app.config["DATA"]

    @app.route("/")
    async def index() -> str:
        app.add_background_task(background)
        return ""

    async with app.test_app():
        test_client = app.test_client()
        await test_client.get("/")

    assert data == "data"
