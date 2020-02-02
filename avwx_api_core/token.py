"""
Token authentication management
"""

# stdlib
from dataclasses import dataclass

# module
from avwx_api_core.counter.token import TokenCountCache


@dataclass
class Token:
    """
    Client auth token
    """

    active: bool
    limit: int
    name: str
    type: str
    value: str
    user: int

    @property
    def is_paid(self) -> bool:
        """
        Returns if a token is an active paid token
        """
        return self.active and self.type != "free"

    def valid_type(self, types: [str]) -> bool:
        """
        Returns True if an active token matches one of the plan types
        """
        return self.active and self.type in types


class TokenManager:
    """
    Handles token fetch and counting
    """

    _app: "Quart"
    _counter = TokenCountCache
    active: bool

    def __init__(self, app: "Quart"):
        self._app = app
        self._counter = TokenCountCache(app)
        self.active = app.mdb is not None

    async def get(self, value: str) -> Token:
        """
        Get a token object by raw value
        """
        data = await self._counter.get(value)
        return Token(value=value, **data) if data else None

    async def increment(self, token: "str/Token") -> bool:
        """
        Increment a token count by Token object or raw value
        """
        if isinstance(token, Token):
            token = token.value
        return await self._counter.add(token)
