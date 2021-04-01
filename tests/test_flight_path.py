"""
Flight path tests
"""

from avwx_api_core import flight_path

FLIGHT_PATHS = (
    ([(12.34, -12.34), (-43.21, 43.21)], [(12.34, -12.34), (-43.21, 43.21)]),
    ([(12.34, -12.34), "KMCO"], [(12.34, -12.34), (28.43, -81.31)]),
    (["KLEX", "KMCO"], [(38.04, -84.61), (28.43, -81.31)]),
    (["FLL", "ATL"], [(26.07, -80.15), (33.63, -84.44)]),
    (["KMIA", "FLL", "ORL"], [(25.79, -80.29), (26.07, -80.15), (28.54, -81.33)]),
    (["FLL", "ORL", "KMCO"], [(26.07, -80.15), (28.54, -81.33), (28.43, -81.31)]),
    (
        ["KMIA", "FLL", "ORL", "KMCO"],
        [(25.79, -80.29), (26.07, -80.15), (28.54, -81.33), (28.43, -81.31)],
    ),
    (
        ["KLEX", "ATL", "ORL", "KMCO"],
        [(38.04, -84.61), (33.63, -84.44), (28.54, -81.33), (28.43, -81.31)],
    ),
    (
        ["KLEX", "ATL", "KDAB", "ORL", "KMCO"],
        [
            (38.04, -84.61),
            (33.63, -84.44),
            (29.18, -81.06),
            (28.54, -81.33),
            (28.43, -81.31),
        ],
    ),
)


def test_to_coordinates():
    """Test coord routing from coords, stations, and navaids"""
    for source, target in FLIGHT_PATHS:
        coords = flight_path.to_coordinates(source)
        # Round to prevent minor coord changes from breaking tests
        coords = [(round(lat, 2), round(lon, 2)) for lat, lon in coords]
        assert coords == target
