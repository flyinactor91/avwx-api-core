"""
Token authentication management
"""

# pylint: disable=too-many-instance-attributes

# stdlib
from dataclasses import dataclass
from typing import Union

# library
from bson import ObjectId
from quart import Quart

# module
from avwx_api_core.counter.token import TokenCountCache


@dataclass
class Token:
    """Client auth token"""

    user: ObjectId

    # Token
    active: bool
    value: str

    # Plan
    limit: int
    name: str
    type: str

    overage: bool = False  # Plan
    user_overage: bool = False  # User

    @property
    def is_developer(self) -> bool:
        """Returns if a token is an active development token"""
        return self.active and self.type == "dev"

    @property
    def is_paid(self) -> bool:
        """Returns if a token is an active paid token"""
        return self.active and self.type not in ("free", "dev")

    def valid_type(self, types: tuple[str]) -> bool:
        """Returns True if an active token matches one of the plan types"""
        return self.active and self.type in types


class TokenManager:
    """Handles token fetch and counting"""

    _app: Quart
    _counter = TokenCountCache
    active: bool

    def __init__(self, app: Quart):
        self._app = app
        self._counter = TokenCountCache(app)
        self._dev = TokenCountCache(app)
        self.active = app.mdb is not None

    async def get(self, value: str) -> Token:
        """Get a token object by raw value"""
        counter = self._dev if value.startswith("dev-") else self._counter
        data = await counter.get(value)
        return Token(**data) if data else None

    async def increment(self, token: Union[str, Token]) -> bool:
        """Increment a token count by Token object or raw value"""
        if isinstance(token, Token):
            token = token.value
        counter = self._dev if token.startswith("dev-") else self._counter
        return await counter.add(token)
