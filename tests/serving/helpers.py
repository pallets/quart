import asyncio
from typing import Optional


class MockTransport:

    def __init__(self) -> None:
        self.data = bytearray()
        self.closed = asyncio.Event()
        self.updated = asyncio.Event()

    def get_extra_info(self, name: str) -> Optional[tuple]:
        if name == 'peername':
            return ('127.0.0.1',)
        return None

    def write(self, data: bytes) -> None:
        assert not self.closed.is_set()
        if data == b'':
            return
        self.data.extend(data)
        self.updated.set()

    def close(self) -> None:
        self.updated.set()
        self.closed.set()

    def clear(self) -> None:
        self.data = bytearray()
        self.updated.clear()
