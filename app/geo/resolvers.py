from collections.abc import Callable
from datetime import UTC, datetime

from app.geo.boundaries import lookup_up_district
from app.geo.elevation import lookup_elevation
from app.geo.osm import nearest_osm_feature
from app.models.geo import FieldResult, Location


Resolver = Callable[[float, float], FieldResult]


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def resolve_location(lat: float, lng: float) -> Location:
    district = lookup_up_district(lat, lng)
    return Location(
        lat=lat,
        lng=lng,
        state="Uttar Pradesh",
        district=district,
        inside_service_area=district is not None,
    )


def resolve_district(lat: float, lng: float) -> FieldResult:
    return FieldResult(
        field="district",
        value=lookup_up_district(lat, lng),
        unit=None,
        source="DataMeet India Districts Census 2011",
        source_url="https://github.com/datameet/maps/tree/master/Districts/Census_2011",
        method="shapefile_point_in_polygon",
        confidence="medium",
        fetched_at=_today(),
    )


def resolve_elevation(lat: float, lng: float) -> FieldResult:
    sample = lookup_elevation(lat, lng)
    if sample is None:
        return FieldResult(
            field="elevation_m",
            value=None,
            unit="m",
            source="SRTM DEM via AWS elevation-tiles-prod",
            source_url=None,
            method="hgt_nearest_sample_lookup",
            confidence="low",
            fetched_at=_today(),
        )

    return FieldResult(
        field="elevation_m",
        value=sample.value_m,
        unit="m",
        source=sample.source,
        source_url=sample.source_url,
        method=sample.method,
        confidence="medium",
        fetched_at=_today(),
    )


def resolve_nearest_road_distance(lat: float, lng: float) -> FieldResult:
    feature = nearest_osm_feature(lat, lng, "road")
    return FieldResult(
        field="nearest_road_distance_m",
        value=None if feature is None else feature.distance_m,
        unit="m",
        source="OpenStreetMap sample extract",
        source_url=None if feature is None else feature.source_url,
        method="local_geojson_nearest_geometry_distance",
        confidence="low" if feature is None else "medium",
        fetched_at=_today(),
    )


def resolve_nearest_water_distance(lat: float, lng: float) -> FieldResult:
    feature = nearest_osm_feature(lat, lng, "water")
    return FieldResult(
        field="nearest_water_distance_m",
        value=None if feature is None else feature.distance_m,
        unit="m",
        source="OpenStreetMap sample extract",
        source_url=None if feature is None else feature.source_url,
        method="local_geojson_nearest_geometry_distance",
        confidence="low" if feature is None else "medium",
        fetched_at=_today(),
    )


def resolve_nearest_water_name(lat: float, lng: float) -> FieldResult:
    feature = nearest_osm_feature(lat, lng, "water")
    return FieldResult(
        field="nearest_water_name",
        value=None if feature is None else feature.name,
        unit=None,
        source="OpenStreetMap sample extract",
        source_url=None if feature is None else feature.source_url,
        method="local_geojson_nearest_geometry_name",
        confidence="low" if feature is None else "medium",
        fetched_at=_today(),
    )


def resolve_nearest_place_name(lat: float, lng: float) -> FieldResult:
    feature = nearest_osm_feature(lat, lng, "place")
    return FieldResult(
        field="nearest_place_name",
        value=None if feature is None else feature.name,
        unit=None,
        source="OpenStreetMap sample extract",
        source_url=None if feature is None else feature.source_url,
        method="local_geojson_nearest_place_lookup",
        confidence="low" if feature is None else "medium",
        fetched_at=_today(),
    )


FIELD_RESOLVERS: dict[str, Resolver] = {
    "district": resolve_district,
    "elevation_m": resolve_elevation,
    "nearest_road_distance_m": resolve_nearest_road_distance,
    "nearest_water_distance_m": resolve_nearest_water_distance,
    "nearest_water_name": resolve_nearest_water_name,
    "nearest_place_name": resolve_nearest_place_name,
}


def _roughly_inside_uttar_pradesh(lat: float, lng: float) -> bool:
    return 23.8 <= lat <= 30.5 and 77.0 <= lng <= 84.8


def _mock_district(lat: float, lng: float) -> str | None:
    if not _roughly_inside_uttar_pradesh(lat, lng):
        return None

    known_points = [
        ("Lucknow", 26.8467, 80.9462),
        ("Kanpur Nagar", 26.4499, 80.3319),
        ("Varanasi", 25.3176, 82.9739),
        ("Prayagraj", 25.4358, 81.8463),
        ("Gautam Buddha Nagar", 28.5355, 77.3910),
        ("Gorakhpur", 26.7606, 83.3732),
    ]

    nearest = min(
        known_points,
        key=lambda point: ((lat - point[1]) ** 2) + ((lng - point[2]) ** 2),
    )
    return nearest[0]
