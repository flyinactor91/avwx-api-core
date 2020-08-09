"""
Manages authentication tokens storage and counting
"""

# stdlib
import time
import asyncio as aio
from datetime import datetime, timezone
from typing import Dict, List, Optional

# library
from bson.objectid import ObjectId
from quart import Quart

# module
from avwx_api_core.counter.base import DelayedCounter
from avwx_api_core.util.handler import mongo_handler


DEV_TOKEN_LIMIT = 4000


class TokenCountCache(DelayedCounter):
    """
    Caches and counts user auth tokens
    """

    def __init__(self, app: Quart, interval: int = 60):
        super().__init__(app, interval)
        self._user = {}

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
        Fetch token data from database
        """
        if self._app.mdb is None:
            return
        search = self._app.mdb.account.user.find_one(
            {"tokens.value": token},
            {
                "tokens._id": 1,
                "tokens.value": 1,
                "tokens.active": 1,
                "plan.limit": 1,
                "plan.name": 1,
                "plan.type": 1,
            },
        )
        data = await mongo_handler(search)
        if not data:
            return
        is_dev = token.startswith("dev-")
        tokens = [t for t in data["tokens"] if is_dev == t["value"].startswith("dev-")]
        ret = {"user": data["_id"], "tokens": tokens, **data["plan"]}
        if is_dev:
            ret["limit"] = DEV_TOKEN_LIMIT
        return ret

    async def _fetch_token_usage(self, user: ObjectId) -> Dict[ObjectId, int]:
        """
        Fetch current token usage from counting table
        """
        if self._app.mdb is None:
            return
        key = self.date_key()
        search = self._app.mdb.account.token.find(
            {"user_id": user, "date": key}, {"_id": 0, "token_id": 1, "count": 1}
        )
        return {t["token_id"]: t["count"] async for t in search}

    async def _set_usage(self, user_id: ObjectId, tokens: List[dict]):
        """
        Set the user's existing token count
        """
        counts = await self._fetch_token_usage(user_id)
        total = 0
        for token in tokens:
            print(token)
            total += counts.get(token["_id"], 0)
        self._user[user_id] = total

    def _set_tokens(self, data: List[dict]):
        """
        Set token data in the counter
        """
        tokens = data.pop("tokens")
        for item in tokens:
            key = item["value"]
            token_id = item.pop("_id")
            item.update(data)
            self._data[key] = {"data": item, "count": 0, "id": token_id}

    async def _worker(self):
        """
        Task worker increments ident counters
        """
        while True:
            async with self._queue.get() as value:
                user, token, count = value
                if self._app.mdb:
                    update = self._app.mdb.account.token.update_one(
                        {"user_id": user, "token_id": token, "date": self.date_key()},
                        {"$inc": {"count": count}},
                        upsert=True,
                    )
                    await mongo_handler(update)

    def gather_data(self) -> dict:
        """
        Returns existing data while locking to prevent missed values
        """
        self.locked = True
        data = self._data
        self._data, self._user = {}, {}
        self.locked = False
        return data

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
            count = item["count"]
            if not count:
                continue
            self._queue.add((item["data"]["user"], item["id"], count))
        self.update_at = time.time() + self.interval

    async def get(self, token: str) -> Optional[dict]:
        """
        Fetch data for a token. Must be called before increment
        """
        await self._pre_add()
        try:
            # Wait for busy thread to add data if not finished fetching
            while self._data[token] is None:
                await aio.sleep(0.0001)
        except KeyError:
            # Set None to indicate data fetch in progress
            self._data[token] = None
            data = await self._fetch_token_data(token)
            if not data:
                try:
                    del self._data[token]
                except KeyError:
                    pass
                return None
            await self._set_usage(data["user"], data["tokens"])
            self._set_tokens(data)
        return self._data[token]["data"]

    # pylint: disable=arguments-differ
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
            total = self._user[item["data"]["user"]]
            return limit >= total + item["count"]
        except KeyError:
            return False
