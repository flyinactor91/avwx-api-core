"""
API App Management
"""

# stdlib
from ssl import SSLContext

# library
from quart_openapi import Pint


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

    return app
