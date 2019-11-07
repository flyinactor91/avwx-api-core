"""
API App Management
"""

# stdlib
from datetime import date
from ssl import SSLContext

# library
from quart.json import JSONEncoder
from quart_openapi import Pint


class CustomJSONEncoder(JSONEncoder):
    """
    Customize the JSON date format
    """

    # pylint: disable=method-hidden
    def default(self, obj):
        try:
            if isinstance(obj, date):
                return obj.isoformat() + "Z"
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


CORS_HEADERS = ["Authorization", "Content-Type"]


def add_cors(response):
    """
    Add missing CORS headers

    Fixes CORS bug where headers are not included in OPTIONS
    """
    for key, value in (
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Headers", CORS_HEADERS),
        ("Access-Control-Allow-Methods", list(response.allow)),
    ):
        if key not in response.headers:
            if isinstance(value, list):
                value = ",".join(value)
            response.headers.add(key, value)
    return response


def create_app(
    name: str, psql_uri: str = None, mongo_uri: str = None, psql_pool_args: dict = None
) -> Pint:
    """
    Create the core API app. Supply URIs as necessary
    """
    app = Pint(name)

    @app.before_serving
    async def _startup():
        if psql_uri:
            import asyncpg

            kwargs = {"min_size": 3, "max_size": 8, "command_timeout": 5}
            if "localhost" not in psql_uri:
                kwargs["ssl"] = SSLContext()
            if psql_pool_args:
                kwargs.update(psql_pool_args)
            app.db = await asyncpg.create_pool(psql_uri, **kwargs)
        else:
            app.db = None

        if mongo_uri:
            from motor.motor_asyncio import AsyncIOMotorClient

            app.mdb = AsyncIOMotorClient(mongo_uri)
        else:
            app.mdb = None

    app.json_encoder = CustomJSONEncoder
    app.after_request(add_cors)
    return app
