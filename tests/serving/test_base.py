import asyncio
from unittest.mock import Mock

import pytest

from quart.serving._base import HTTPProtocol


@pytest.mark.asyncio
async def test_timeout(event_loop: asyncio.AbstractEventLoop) -> None:
    timeout = 0.1
    protocol = HTTPProtocol(Mock(), event_loop, Mock(), None, '', timeout)  # type: ignore
    await asyncio.sleep(0.5 * timeout)
    protocol._transport.close.assert_not_called()  # type: ignore
    await asyncio.sleep(2 * timeout)
    protocol._transport.close.assert_called_once()  # type: ignore
