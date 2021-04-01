"""
Entity schema validation
"""

# pylint: disable=C0103

# stdlib
import re
from typing import Callable

# library
from voluptuous import All, Coerce, Invalid, Length, Range

# module
from avwx_api_core import flight_path
from avwx_api_core.structs import Coord


Latitude = All(Coerce(float), Range(-90, 90))
Longitude = All(Coerce(float), Range(-180, 180))


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


def FlightRoute(values: str) -> list[Coord]:
    """Validates a semicolon-separated string of coordinates or navigation markers"""
    values = values.upper().split(";")
    if not values:
        raise Invalid("Could not find any route components in the request")
    for i, val in enumerate(values):
        if "," in val:
            loc = val.split(",")
            values[i] = (loc[0], loc[1])
    values = flight_path.to_coordinates(values)
    return [(Latitude(lat), Longitude(lon)) for lat, lon in values]
