"""
Entity schema validation
"""

# pylint: disable=C0103

# stdlib
import re
from typing import Callable

# library
from voluptuous import All, Invalid, Length


def MatchesRE(name: str, pattern: str) -> Callable:
    """Returns a validation function that checks if a string matches a regex pattern"""
    expr = re.compile(pattern)

    def mre(txt: str) -> str:
        """Raises an exception if a string doesn't match the required format"""
        if expr.fullmatch(txt) is None:
            raise Invalid(f"'{txt}' is not a valid {name}")
        return txt

    return mre


Token = All(
    str,
    Length(min=10),
    lambda x: x.strip().split()[-1],
    MatchesRE("token", r"[A-Za-z0-9\-\_]+"),
)
