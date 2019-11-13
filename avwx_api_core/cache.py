"""
MongoDB document cache management
"""

# stdlib
from copy import copy
from datetime import datetime, timedelta

# module
from avwx_api_core.util.handler import mongo_handler


# Table expiration in minutes
EXPIRES = {"token": 15}
DEFAULT_EXPIRES = 2


def _replace_keys(data: dict, key: str, by_key: str) -> dict:
    """
    Replaces recursively the keys equal to 'key' by 'by_key'

    Some keys in the report data are '$' and this is not accepted by MongoDB
    """
    if data is None:
        return
    for k, v in data.items():
        if k == key:
            data[by_key] = data.pop(key)
        if isinstance(v, dict):
            data[k] = _replace_keys(v, key, by_key)
    return data


class CacheManager:
    """
    Handles expiring updates to/from the document cache
    """

    _app: "Quart"
    expires: dict

    def __init__(self, app: "Quart", expires: dict = None):
        self._app = app
        self.expires = copy(EXPIRES)
        if expires:
            self.expires.update(expires)

    def has_expired(self, time: datetime, table: str) -> bool:
        """
        Returns True if a datetime is older than the number of minutes given
        """
        if not time:
            return True
        minutes = self.expires.get(table, DEFAULT_EXPIRES)
        return datetime.utcnow() > time + timedelta(minutes=minutes)

    async def get(self, table: str, key: str, force: bool = False) -> {str: object}:
        """
        Returns the current cached data for a report type and station or None

        By default, will only return if the cache timestamp has not been exceeded
        Can force the cache to return if force is True
        """
        if self._app.mdb is None:
            return
        op = self._app.mdb.cache[table.lower()].find_one({"_id": key})
        data = await mongo_handler(op)
        data = _replace_keys(data, "_$", "$")
        if force:
            return data
        if isinstance(data, dict) and not self.has_expired(
            data.get("timestamp"), table
        ):
            return data
        return

    async def update(self, table: str, key: str, data: {str: object}):
        """
        Update the cache
        """
        if self._app.mdb is None:
            return
        data = _replace_keys(copy(data), "$", "_$")
        data["timestamp"] = datetime.utcnow()
        op = self._app.mdb.cache[table.lower()].update_one(
            {"_id": key}, {"$set": data}, upsert=True
        )
        await mongo_handler(op)
        return
