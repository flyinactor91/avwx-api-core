"""
Remote call handlers
"""

# stdlib
import asyncio as aio

# library
from pymongo.errors import AutoReconnect, OperationFailure


async def mongo_handler(operation: "coroutine") -> object:
    """
    Error handling around the Mongo client connection
    """
    for _ in range(5):
        try:
            resp = await operation
            return resp
        except OperationFailure:
            return
        except AutoReconnect:
            await aio.sleep(0.5)
