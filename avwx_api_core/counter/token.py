"""
Manages authentication tokens storage and counting
"""

# stdlib
import time
import asyncio as aio
from datetime import datetime, timezone

# module
from avwx_api_core.counter.base import DelayedCounter
from avwx_api_core.util.handler import mongo_handler


class TokenCountCache(DelayedCounter):
    """
    Caches and counts user auth tokens
    """

    @staticmethod
    def date_key() -> datetime:
        """
        Returns the current date as a sub POSIX key
        """
        return datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    async def _fetch_token_data(self, token: str) -> dict:
        """
        Fetch token data from the cache or primary database
        """
        if self._app.mdb is None:
            return
        op = self._app.mdb.account.user.find_one(
            {"token.value": token},
            {"token.active": 1, "plan.limit": 1, "plan.name": 1, "plan.type": 1},
        )
        data = await mongo_handler(op)
        if not data:
            return
        return {"user": data["_id"], **data["token"], **data["plan"]}

    async def _fetch_token_usage(self, user: "pymongo.ObjectId") -> int:
        """
        Fetch current token usage from counting table
        """
        if self._app.mdb is None:
            return
        key = self.date_key()
        op = self._app.mdb.account.token.find_one(
            {"user_id": user, "date": key}, {"_id": 0, "count": 1}
        )
        data = await mongo_handler(op)
        try:
            return data["count"]
        except (IndexError, KeyError, TypeError):
            return 0

    async def _worker(self):
        """
        Task worker increments ident counters
        """
        while True:
            async with self._queue.get() as value:
                user, count = value
                if self._app.mdb:
                    op = self._app.mdb.account.token.update_one(
                        {"user_id": user, "date": self.date_key()},
                        {"$inc": {"count": count}},
                        upsert=True,
                    )
                    await mongo_handler(op)

    # NOTE: The user triggering the update will not have the correct total.
    # This means that the cutoff time is at most 2 * self.interval
    def update(self):
        """
        Sends token counts to worker queue
        """
        to_update = self.gather_data()
        for item in to_update.values():
            if not item:
                continue
            self._queue.add((item["data"]["user"], item["count"]))
        self.update_at = time.time() + self.interval

    async def get(self, token: str) -> dict:
        """
        Fetch data for a token. Must be called before increment
        """
        await self._pre_add()
        try:
            # Wait for busy thread to add data if not finished fetching
            item = self._data[token]
            while item is None:
                await aio.sleep(0.0001)
                item = self._data[token]
            return item["data"]
        except KeyError:
            # Set None to indicate data fetch in progress
            self._data[token] = None
            data = await self._fetch_token_data(token)
            if not data:
                try:
                    del self._data[token]
                except KeyError:
                    pass
                return
            total = await self._fetch_token_usage(data["user"])
            self._data[token] = {"data": data, "count": 0, "total": total}
            return data

    async def add(self, token: str) -> bool:
        """
        Increment a token usage counter

        Returns False if token has hit its limit or not found
        """
        try:
            self._data[token]["count"] += 1
            item = self._data[token]
            limit = item["data"]["limit"]
            if limit is None:
                return True
            return limit >= item["total"] + item["count"]
        except KeyError:
            return False
