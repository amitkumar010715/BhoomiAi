import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "vector" / "osm_up_samples.geojson"
EARTH_RADIUS_M = 6_371_008.8

# OSM sample coverage downloaded by scripts/download_osm_samples.py.
# Outside these boxes, OSM fields should be shown as unavailable instead of
# returning the nearest feature from another city.
SAMPLE_AREAS = {
    "lucknow": (26.70, 80.75, 27.00, 81.10),
    "varanasi": (25.20, 82.85, 25.45, 83.10),
    "noida": (28.45, 77.25, 28.65, 77.55),
}


@dataclass(frozen=True)
class NearestFeature:
    name: str | None
    distance_m: float
    source: str
    source_url: str
    method: str
    confidence: str


@lru_cache(maxsize=512)
def nearest_osm_feature(lat: float, lng: float, kind: str) -> NearestFeature | None:
    if not _inside_sample_area(lat, lng):
        return None

    candidates = _features_by_kind(kind)
    if not candidates:
        return None

    best_feature: dict[str, Any] | None = None
    best_distance = math.inf

    for feature in candidates:
        distance = _distance_to_geometry_m(lat, lng, feature.get("geometry") or {})
        if distance < best_distance:
            best_distance = distance
            best_feature = feature

    if best_feature is None or math.isinf(best_distance):
        return None

    props = best_feature.get("properties", {})
    osm_type = props.get("osm_type")
    osm_id = props.get("osm_id")
    source_url = "https://www.openstreetmap.org/"
    if osm_type and osm_id:
        source_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"

    return NearestFeature(
        name=props.get("name"),
        distance_m=round(best_distance, 1),
        source="OpenStreetMap sample extract",
        source_url=source_url,
        method="local_geojson_nearest_geometry_distance",
        confidence="medium",
    )


def osm_sample_coverage_status(lat: float, lng: float) -> str:
    area = _sample_area_name(lat, lng)
    return area or "outside_sample_coverage"


@lru_cache(maxsize=1)
def _load_features() -> tuple[dict[str, Any], ...]:
    if not DATA_PATH.exists():
        return ()

    collection = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return tuple(collection.get("features") or [])


@lru_cache(maxsize=8)
def _features_by_kind(kind: str) -> tuple[dict[str, Any], ...]:
    return tuple(
        feature for feature in _load_features()
        if feature.get("properties", {}).get("kind") == kind
    )


def _inside_sample_area(lat: float, lng: float) -> bool:
    return _sample_area_name(lat, lng) is not None


def _sample_area_name(lat: float, lng: float) -> str | None:
    for name, bbox in SAMPLE_AREAS.items():
        south, west, north, east = bbox
        if south <= lat <= north and west <= lng <= east:
            return name
    return None


def _distance_to_geometry_m(lat: float, lng: float, geometry: dict[str, Any]) -> float:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geometry_type == "Point":
        return _point_distance_m(lat, lng, coordinates[1], coordinates[0])

    if geometry_type == "LineString":
        return _distance_to_line_m(lat, lng, coordinates)

    if geometry_type == "Polygon":
        ring = coordinates[0] if coordinates else []
        if _point_in_ring(lng, lat, ring):
            return 0.0
        return _distance_to_line_m(lat, lng, ring)

    return math.inf


def _distance_to_line_m(lat: float, lng: float, coordinates: list[list[float]]) -> float:
    if len(coordinates) < 2:
        return math.inf

    point = _project(lat, lng, lat, lng)
    best = math.inf

    for start, end in zip(coordinates, coordinates[1:], strict=False):
        a = _project(start[1], start[0], lat, lng)
        b = _project(end[1], end[0], lat, lng)
        best = min(best, _point_segment_distance(point, a, b))

    return best


def _point_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _project(lat: float, lng: float, origin_lat: float, origin_lng: float) -> tuple[float, float]:
    x = EARTH_RADIUS_M * math.radians(lng - origin_lng) * math.cos(math.radians(origin_lat))
    y = EARTH_RADIUS_M * math.radians(lat - origin_lat)
    return x, y


def _point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay

    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)

    t = ((px - ax) * dx + (py - ay) * dy) / ((dx * dx) + (dy * dy))
    t = min(1.0, max(0.0, t))
    nearest_x = ax + (t * dx)
    nearest_y = ay + (t * dy)
    return math.hypot(px - nearest_x, py - nearest_y)


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1

    for i, point in enumerate(ring):
        xi, yi = point
        xj, yj = ring[j]

        if (yi > y) != (yj > y):
            x_intersection = ((xj - xi) * (y - yi) / (yj - yi)) + xi
            if x < x_intersection:
                inside = not inside

        j = i

    return inside
