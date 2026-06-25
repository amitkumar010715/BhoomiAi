from app.models.geo import SupportedField


DEFAULT_FIELDS: list[SupportedField] = [
    "district",
    "elevation_m",
    "nearest_road_distance_m",
    "nearest_water_distance_m",
    "nearest_place_name",
]


QUESTION_FIELD_RULES: list[tuple[tuple[str, ...], list[SupportedField]]] = [
    (
        ("road", "access", "transport", "warehouse", "construction", "site"),
        ["district", "elevation_m", "nearest_road_distance_m", "nearest_water_distance_m"],
    ),
    (
        ("water", "river", "canal", "pond", "lake", "flood", "flooding"),
        ["district", "elevation_m", "nearest_water_distance_m", "nearest_water_name"],
    ),
    (
        ("farm", "farming", "agriculture", "crop", "rural", "land"),
        ["district", "elevation_m", "nearest_water_distance_m", "nearest_road_distance_m"],
    ),
    (
        ("where", "place", "near", "nearest", "location"),
        ["district", "nearest_place_name", "nearest_road_distance_m", "nearest_water_distance_m"],
    ),
]


def plan_fields(question: str) -> list[SupportedField]:
    normalized = question.lower()
    selected: list[SupportedField] = []

    for keywords, fields in QUESTION_FIELD_RULES:
        if any(keyword in normalized for keyword in keywords):
            selected.extend(fields)

    if not selected:
        selected = DEFAULT_FIELDS.copy()

    return _dedupe(selected)


def _dedupe(fields: list[SupportedField]) -> list[SupportedField]:
    seen: set[SupportedField] = set()
    result: list[SupportedField] = []

    for field in fields:
        if field in seen:
            continue
        seen.add(field)
        result.append(field)

    return result
