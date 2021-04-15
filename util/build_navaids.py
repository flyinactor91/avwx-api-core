"""
Build navaid coordinate map
"""

import json
from pathlib import Path
import httpx

URL = "https://ourairports.com/data/navaids.csv"
FILE_PATH = Path(__file__).parent.parent.joinpath(
    "avwx_api_core", "data", "navaids.json"
)


def main():
    """Build navaid coordinate map"""
    text = httpx.get(URL).text
    lines = text.strip().split("\n")
    lines.pop(0)
    data = {}
    for line in lines:
        line = line.split(",")
        try:
            ident, lat, lon = line[2].strip('"'), float(line[6]), float(line[7])
        except ValueError:
            continue
        if not ident:
            continue
        try:
            data[ident].add((lat, lon))
        except KeyError:
            data[ident] = {(lat, lon)}
    data = {k: list(v) for k, v in data.items()}
    json.dump(data, FILE_PATH.open("w"), indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
