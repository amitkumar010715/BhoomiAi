from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import shapefile


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "vector"
DISTRICT_SHAPEFILE = DATA_DIR / "2011_Dist.shp"


@dataclass(frozen=True)
class DistrictBoundary:
    name: str
    bbox: tuple[float, float, float, float]
    rings: tuple[tuple[tuple[float, float], ...], ...]


@lru_cache(maxsize=1)
def load_up_district_boundaries() -> tuple[DistrictBoundary, ...]:
    if not DISTRICT_SHAPEFILE.exists():
        return ()

    reader = shapefile.Reader(str(DISTRICT_SHAPEFILE), encoding="latin1")
    field_names = [field[0] for field in reader.fields[1:]]
    boundaries: list[DistrictBoundary] = []

    for shape_record in reader.iterShapeRecords():
        record = dict(zip(field_names, shape_record.record, strict=False))
        if record.get("ST_NM") != "Uttar Pradesh":
            continue

        shape = shape_record.shape
        rings = _shape_rings(shape.points, shape.parts)
        boundaries.append(
            DistrictBoundary(
                name=str(record["DISTRICT"]),
                bbox=tuple(shape.bbox),
                rings=rings,
            )
        )

    return tuple(boundaries)


def lookup_up_district(lat: float, lng: float) -> str | None:
    x = lng
    y = lat

    for boundary in load_up_district_boundaries():
        min_x, min_y, max_x, max_y = boundary.bbox
        if not (min_x <= x <= max_x and min_y <= y <= max_y):
            continue

        if _point_in_polygon_parts(x, y, boundary.rings):
            return boundary.name

    return None


def _shape_rings(
    points: list[list[float]],
    parts: list[int],
) -> tuple[tuple[tuple[float, float], ...], ...]:
    part_starts = list(parts) + [len(points)]
    rings = []

    for index, start in enumerate(part_starts[:-1]):
        end = part_starts[index + 1]
        ring = tuple((float(x), float(y)) for x, y in points[start:end])
        if len(ring) >= 3:
            rings.append(ring)

    return tuple(rings)


def _point_in_polygon_parts(
    x: float,
    y: float,
    rings: tuple[tuple[tuple[float, float], ...], ...],
) -> bool:
    inside = False
    for ring in rings:
        if _point_in_ring(x, y, ring):
            inside = not inside
    return inside


def _point_in_ring(
    x: float,
    y: float,
    ring: tuple[tuple[float, float], ...],
) -> bool:
    inside = False
    j = len(ring) - 1

    for i, point in enumerate(ring):
        xi, yi = point
        xj, yj = ring[j]

        intersects = (yi > y) != (yj > y)
        if intersects:
            x_intersection = ((xj - xi) * (y - yi) / (yj - yi)) + xi
            if x < x_intersection:
                inside = not inside

        j = i

    return inside

