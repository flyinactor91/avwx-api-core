"""
Manages authentication tokens storage and counting
"""

# stdlib
import time
import asyncio as aio
from contextlib import suppress
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# library
from bson.objectid import ObjectId
from pymongo import UpdateOne
from quart import Quart

# module
from avwx_api_core.counter.base import DelayedCounter
from avwx_api_core.util.handler import mongo_handler


DEV_TOKEN_LIMIT = 4000


class TokenCountCache(DelayedCounter):
    """Caches and counts user auth tokens"""

    def __init__(self, app: Quart, interval: int = 60):
        super().__init__(app, interval)
        self._user = {}

    @staticmethod
    def date_key() -> datetime:
        """Returns the current date as a sub POSIX key"""
        return datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    async def _fetch_token_data(self, token: str) -> Optional[dict]:
        """Fetch token data from database"""
        if self._app.mdb is None:
            return None
        search = self._app.mdb.account.user.find_one(
            {"tokens.value": token},
            {
                "tokens._id": 1,
                "tokens.value": 1,
                "tokens.active": 1,
                "plan.limit": 1,
                "plan.name": 1,
                "plan.type": 1,
                "plan.overage": 1,
                "allow_overage": 1,
            },
        )
        data = await mongo_handler(search)
        if not data:
            return None
        is_dev = token.startswith("dev-")
        tokens = [t for t in data["tokens"] if is_dev == t["value"].startswith("dev-")]
        ret = {
            "user": data["_id"],
            "user_overage": data.get("allow_overage", False),
            "tokens": tokens,
            **data["plan"],
        }
        if is_dev:
            ret["limit"] = DEV_TOKEN_LIMIT
        return ret

    async def _fetch_token_usage(self, user: ObjectId) -> Dict[ObjectId, int]:
        """Fetch current token usage from counting table"""
        if self._app.mdb is None:
            return
        key = self.date_key()
        search = self._app.mdb.account.token.find(
            {"user_id": user, "date": key}, {"_id": 0, "token_id": 1, "count": 1}
        )
        return {t["token_id"]: t["count"] async for t in search}

    async def _set_usage(self, user_id: ObjectId, tokens: List[dict]):
        """Set the user's existing token count"""
        counts = await self._fetch_token_usage(user_id)
        total = 0
        for token in tokens:
            total += counts.get(token["_id"], 0)
        self._user[user_id] = total

    def _set_tokens(self, data: List[dict]):
        """Set token data in the counter"""
        tokens = data.pop("tokens")
        for item in tokens:
            key = item["value"]
            token_id = item.pop("_id")
            item.update(data)
            self._data[key] = {"data": item, "count": 0, "overage": 0, "id": token_id}

    @staticmethod
    def _update_counts(match: dict, count: int, overage: int) -> UpdateOne:
        """Create counter increment operation"""
        counts = {"$inc": {"count": count}}
        if overage > 0:
            counts["$inc"]["overage"] = overage
        return UpdateOne(match, counts, upsert=True)

    @staticmethod
    def _update_timestamps(match: dict, overage: int) -> List[UpdateOne]:
        """Create timestamp usage operations"""
        now = datetime.now(tz=timezone.utc)
        updates = [UpdateOne(match, {"$set": {"updated": now}}, upsert=True)]
        if overage:
            excluding = {**match, "overage_started": {"$exists": False}}
            updates.append(UpdateOne(excluding, {"$set": {"overage_started": now}}))
        return updates

    async def _process_queue_value(self, value: Tuple[ObjectId, str, int, int]):
        """Updates token counts and timestamps from queued value"""
        user, token, count, overage = value
        match = {"user_id": user, "token_id": token, "date": self.date_key()}
        updates = [self._update_counts(match, count, overage)]
        updates += self._update_timestamps(match, overage)
        await mongo_handler(self._app.mdb.account.token.bulk_write(updates))

    async def _worker(self):
        """Task worker main"""
        while True:
            async with self._queue.get() as value:
                if self._app.mdb:
                    await self._process_queue_value(value)

    def gather_data(self) -> dict:
        """Returns existing data while locking to prevent missed values"""
        self.locked = True
        data = self._data
        self._data, self._user = {}, {}
        self.locked = False
        return data

    def update(self):
        """Sends token counts to worker queue

        NOTE: The user triggering the update will not have the correct total.
        This means that the cutoff time is at most 2 * self.interval
        """
        to_update = self.gather_data()
        for item in to_update.values():
            if not item:
                continue
            count = item["count"]
            if not count:
                continue
            self._queue.add((item["data"]["user"], item["id"], count, item["overage"]))
        self.update_at = time.time() + self.interval

    async def get(self, token: str) -> Optional[dict]:
        """Fetch data for a token. Must be called before increment"""
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
                with suppress(KeyError):
                    del self._data[token]
                return None
            await self._set_usage(data["user"], data["tokens"])
            self._set_tokens(data)
        return self._data[token]["data"]

    # pylint: disable=arguments-differ
    async def add(self, token: str) -> bool:
        """Increment a token usage counter

        Returns False if token has hit its limit or not found
        """
        try:
            self._data[token]["count"] += 1
            item = self._data[token]
            data = item["data"]
            limit = data["limit"]
            if limit is None:
                return True
            total, current = self._user[data["user"]], item["count"]
            if limit >= total + current:
                return True
            if data.get("overage") and data.get("user_overage"):
                self._data[token]["overage"] += 1
                return True
            return False
        except KeyError:
            return False
