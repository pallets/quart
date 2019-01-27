from typing import Any

import pytest

from quart.signals import AsyncNamedSignal


@pytest.mark.asyncio
@pytest.mark.parametrize("weak", [True, False])
async def test_sync_signal(weak: bool) -> None:
    signal = AsyncNamedSignal('name')
    fired = False

    def sync_fired(*_: Any) -> None:
        nonlocal fired
        fired = True

    signal.connect(sync_fired, weak=weak)

    await signal.send()
    assert fired


@pytest.mark.asyncio
@pytest.mark.parametrize("weak", [True, False])
async def test_async_signal(weak: bool) -> None:
    signal = AsyncNamedSignal('name')
    fired = False

    async def async_fired(*_: Any) -> None:
        nonlocal fired
        fired = True

    signal.connect(async_fired, weak=weak)

    await signal.send()
    assert fired
