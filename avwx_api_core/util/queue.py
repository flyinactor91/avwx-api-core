"""
Task queue management
"""

# stdlib
import asyncio as aio
from contextlib import asynccontextmanager
from typing import Any, Coroutine


class Queue:
    """Asynchronous task queue manager"""

    _queue: aio.Queue
    _workers: list[Coroutine]

    def __init__(self, worker_obj: object, count: int = 3):
        self._queue = aio.Queue()
        self._workers = [aio.create_task(worker_obj._worker()) for _ in range(count)]

    def add(self, value: Any):
        """Add a value to the queue"""
        self._queue.put_nowait(value)

    @asynccontextmanager
    async def get(self) -> Any:
        """Get a value to handle. Used in a 'with' statement"""
        value = await self._queue.get()
        yield value
        self._queue.task_done()

    async def clean(self, wait: bool = True):
        """Clean the queue and wait until all workers are finished"""
        if wait:
            while not self._queue.empty():
                await aio.sleep(0.01)
        for worker_thread in self._workers:
            worker_thread.cancel()
        await aio.gather(*self._workers, return_exceptions=True)
