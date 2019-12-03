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


TOKEN_QUERY = """
SELECT u.id AS user, u.active_token AS active, p.limit, p.name, p.type
FROM public.user u
JOIN public.plan p
ON u.plan_id = p.id
WHERE apitoken = $1;
"""


def date_key() -> str:
    """
    Returns the current date as a sub POSIX key
    """
    return datetime.now(tz=timezone.utc).strftime(r"%Y-%m-%d")


class TokenCountCache(DelayedCounter):
    """
    Caches and counts user auth tokens
    """

    @staticmethod
    def date_key() -> str:
        """
        Returns the current date as a sub POSIX key
        """
        return datetime.now(tz=timezone.utc).strftime(r"%Y-%m-%d")

    async def _fetch_token_data(self, token: str) -> dict:
        """
        Fetch token data from the cache or primary database
        """
        data = await self._app.cache.get("token", token)
        if data:
            # Remove cache meta
            del data["_id"]
            del data["timestamp"]
        else:
            async with self._app.db.acquire() as conn:
                async with conn.transaction():
                    result = await conn.fetch(TOKEN_QUERY, token)
            if not result:
                return
            data = dict(result[0])
            await self._app.cache.update("token", token, data)
        return data

    async def _fetch_token_usage(self, user: int) -> int:
        """
        Fetch current token usage from counting table
        """
        if self._app.mdb is None:
            return
        key = date_key()
        op = self._app.mdb.counter.token.find_one({"_id": user}, {"_id": 0, key: 1})
        data = await mongo_handler(op)
        if not data:
            return 0
        return data.get(key, 0)

    async def _worker(self):
        """
        Task worker increments ident counters
        """
        while True:
            async with self._queue.get() as value:
                user, count = value
                if self._app.mdb:
                    await self._app.mdb.counter.token.update_one(
                        {"_id": user}, {"$inc": {date_key(): count}}, upsert=True
                    )

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
