import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "vector" / "osm_up_samples.geojson"

AREAS = {
    "lucknow": (26.70, 80.75, 27.00, 81.10),
    "varanasi": (25.20, 82.85, 25.45, 83.10),
    "noida": (28.45, 77.25, 28.65, 77.55),
}


def main() -> None:
    features: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()

    for area_name, bbox in AREAS.items():
        print(f"Downloading OSM features for {area_name}...")
        data = _overpass_query(_query_for_bbox(bbox))

        for element in data.get("elements", []):
            feature = _element_to_feature(element, area_name)
            if feature is None:
                continue

            key = (
                feature["properties"]["osm_type"],
                feature["properties"]["osm_id"],
                feature["properties"]["kind"],
            )
            if key in seen:
                continue

            seen.add(key)
            features.append(feature)
        _write_features(features)
        time.sleep(3)

    _write_features(features)
    print(f"Wrote {len(features)} features to {OUTPUT_PATH}")


def _write_features(features: list[dict[str, Any]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": features,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _query_for_bbox(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    box = f"{south},{west},{north},{east}"
    return f"""
    [out:json][timeout:120];
    (
      way["highway"]({box});
      way["waterway"]({box});
      way["natural"="water"]({box});
      way["landuse"="reservoir"]({box});
      node["place"]({box});
    );
    out geom tags;
    """


def _overpass_query(query: str) -> dict[str, Any]:
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_error: Exception | None = None

    for url in OVERPASS_URLS:
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "up-geo-api-mvp/0.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:
            last_error = error
            print(f"Overpass endpoint failed: {url} ({error})")
            time.sleep(5)

    raise RuntimeError(f"All Overpass endpoints failed: {last_error}")


def _element_to_feature(element: dict[str, Any], area_name: str) -> dict[str, Any] | None:
    tags = element.get("tags") or {}
    kind = _feature_kind(tags, element.get("type"))
    if kind is None:
        return None

    geometry = _feature_geometry(element, kind)
    if geometry is None:
        return None

    return {
        "type": "Feature",
        "properties": {
            "kind": kind,
            "area": area_name,
            "name": tags.get("name"),
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            "source": "OpenStreetMap",
        },
        "geometry": geometry,
    }


def _feature_kind(tags: dict[str, Any], element_type: str | None) -> str | None:
    if element_type == "node" and tags.get("place"):
        return "place"
    if tags.get("highway"):
        return "road"
    if tags.get("waterway") or tags.get("natural") == "water" or tags.get("landuse") == "reservoir":
        return "water"
    return None


def _feature_geometry(element: dict[str, Any], kind: str) -> dict[str, Any] | None:
    if element.get("type") == "node":
        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            return None
        return {"type": "Point", "coordinates": [lon, lat]}

    raw_points = element.get("geometry") or []
    points = [
        [point["lon"], point["lat"]]
        for point in raw_points
        if "lat" in point and "lon" in point
    ]
    if len(points) < 2:
        return None

    if kind == "water" and len(points) >= 4 and points[0] == points[-1]:
        return {"type": "Polygon", "coordinates": [points]}

    return {"type": "LineString", "coordinates": points}


if __name__ == "__main__":
    main()
