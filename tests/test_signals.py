from typing import Any

import pytest

from quart.signals import AsyncNamedSignal


@pytest.mark.asyncio
async def test_async_signal() -> None:
    signal = AsyncNamedSignal('name')
    fired = [False, False]

    def sync_fired(*_: Any) -> None:
        nonlocal fired
        fired[0] = True

    async def async_fired(*_: Any) -> None:
        nonlocal fired
        fired[1] = True

    signal.connect(sync_fired, weak=False)
    signal.connect(async_fired, weak=False)

    await signal.send()
    assert fired == [True, True]
