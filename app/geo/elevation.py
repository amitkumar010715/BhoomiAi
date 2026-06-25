import gzip
import math
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raster" / "srtm"
VOID_ELEVATION = -32768


@dataclass(frozen=True)
class ElevationSample:
    value_m: int
    tile: str
    source: str
    source_url: str
    method: str
    confidence: str


def lookup_elevation(lat: float, lng: float) -> ElevationSample | None:
    tile_name = _tile_name(lat, lng)
    tile_path = DATA_DIR / f"{tile_name}.hgt.gz"
    if not tile_path.exists():
        return None

    tile = _load_hgt_tile(tile_path)
    size = tile["size"]
    data = tile["data"]

    tile_lat = math.floor(lat)
    tile_lng = math.floor(lng)

    row = round((tile_lat + 1 - lat) * (size - 1))
    col = round((lng - tile_lng) * (size - 1))
    row = min(max(row, 0), size - 1)
    col = min(max(col, 0), size - 1)

    offset = ((row * size) + col) * 2
    value = struct.unpack_from(">h", data, offset)[0]
    if value == VOID_ELEVATION:
        return None

    return ElevationSample(
        value_m=int(value),
        tile=tile_name,
        source="SRTM DEM via AWS elevation-tiles-prod",
        source_url=f"https://s3.amazonaws.com/elevation-tiles-prod/skadi/{tile_name[:3]}/{tile_name}.hgt.gz",
        method="hgt_nearest_sample_lookup",
        confidence="medium",
    )


@lru_cache(maxsize=64)
def _load_hgt_tile(tile_path: Path) -> dict[str, bytes | int]:
    with gzip.open(tile_path, "rb") as file:
        data = file.read()

    samples = len(data) // 2
    size = int(math.sqrt(samples))
    if size * size != samples:
        raise ValueError(f"Invalid HGT tile size: {tile_path}")

    return {"data": data, "size": size}


def _tile_name(lat: float, lng: float) -> str:
    south_west_lat = math.floor(lat)
    south_west_lng = math.floor(lng)

    lat_prefix = "N" if south_west_lat >= 0 else "S"
    lng_prefix = "E" if south_west_lng >= 0 else "W"

    return (
        f"{lat_prefix}{abs(south_west_lat):02d}"
        f"{lng_prefix}{abs(south_west_lng):03d}"
    )

