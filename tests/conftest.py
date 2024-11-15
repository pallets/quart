from __future__ import annotations

import pytest
from hypercorn.typing import HTTPScope
from hypercorn.typing import WebsocketScope


@pytest.fixture(name="http_scope")
def _http_scope() -> HTTPScope:
    return {
        "type": "http",
        "asgi": {},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"a=b",
        "root_path": "",
        "headers": [
            (b"User-Agent", b"Hypercorn"),
            (b"X-Hypercorn", b"Hypercorn"),
            (b"Referer", b"hypercorn"),
        ],
        "client": ("127.0.0.1", 80),
        "server": None,
        "state": {},  # type: ignore[typeddict-item]
        "extensions": {},
    }


@pytest.fixture(name="websocket_scope")
def _websocket_scope() -> WebsocketScope:
    return {
        "type": "websocket",
        "asgi": {},
        "http_version": "1.1",
        "scheme": "https",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"a=b",
        "root_path": "",
        "headers": [
            (b"User-Agent", b"Hypercorn"),
            (b"X-Hypercorn", b"Hypercorn"),
            (b"Referer", b"hypercorn"),
        ],
        "client": ("127.0.0.1", 80),
        "server": None,
        "subprotocols": [],
        "state": {},  # type: ignore[typeddict-item]
        "extensions": {},
    }
