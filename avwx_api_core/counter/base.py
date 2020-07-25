"""
Local counter to aggregate calls to databases
"""

# stdlib
import time
import asyncio as aio

# library
from quart import Quart

# module
from avwx_api_core.util.queue import Queue


class DelayedCounter:
    """
    Manages counts to limit calls to database
    """

    _app: Quart
    _data: dict
    _queue: Queue
    update_at: int
    interval: int  # seconds
    locked: bool = False

    def __init__(self, app: Quart, interval: int = 60):
        self._app = app
        self._queue = Queue(self)
        self._data = {}
        self.interval = interval
        self.update_at = time.time() + self.interval
        self._app.after_serving(self.clean)

    async def _pre_add(self):
        """
        Checks if the counts should be flushed and waits for lock
        """
        if time.time() > self.update_at:
            self.update()
        while self.locked:
            await aio.sleep(0.000001)

    async def _worker(self):
        """
        Task worker
        """
        raise NotImplementedError()

    def gather_data(self) -> dict:
        """
        Returns existing data while locking to prevent missed values
        """
        self.locked = True
        to_update = self._data
        self._data = {}
        self.locked = False
        return to_update

    def update(self):
        """
        Send counts to worker queue
        """
        raise NotImplementedError()

    async def add(self, *args, **kwargs):
        """
        Add element to counter
        """
        raise NotImplementedError()

    async def clean(self):
        """
        Finish processing
        """
        self.update()
        await self._queue.clean()
