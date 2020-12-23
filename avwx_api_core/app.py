"""
API App Management
"""

# stdlib
from datetime import date, datetime

# library
from motor.motor_asyncio import AsyncIOMotorClient
from quart.json import JSONEncoder
from quart_openapi import Pint


class CustomJSONEncoder(JSONEncoder):
    """Customize the JSON date format"""

    # pylint: disable=arguments-differ
    def default(self, obj):
        try:
            if isinstance(obj, datetime):
                new_obj = obj.replace(tzinfo=None)
                return new_obj.isoformat() + "Z"
            if isinstance(obj, date):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


CORS_HEADERS = ["Authorization", "Content-Type"]


def add_cors(response):
    """Add missing CORS headers

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


def create_app(name: str, mongo_uri: str = None) -> Pint:
    """Create the core API app. Supply URIs as necessary"""
    app = Pint(name)

    @app.before_serving
    async def _startup():
        app.mdb = AsyncIOMotorClient(mongo_uri) if mongo_uri else None

    app.json_encoder = CustomJSONEncoder
    app.after_request(add_cors)
    return app
