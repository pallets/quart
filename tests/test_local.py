import asyncio

import pytest

from quart.local import TaskLocal


@pytest.mark.asyncio
async def test_task_local() -> None:
    local_ = TaskLocal()
    queue: asyncio.Queue = asyncio.Queue()
    tasks = 2
    for _ in range(tasks):
        queue.put_nowait(None)

    async def _test_local(value: int) -> int:
        local_.test = value
        await queue.get()
        queue.task_done()
        await queue.join()
        return local_.test

    futures = [asyncio.ensure_future(_test_local(value)) for value in range(tasks)]
    asyncio.gather(*futures)
    for value, future in enumerate(futures):
        assert (await future) == value
