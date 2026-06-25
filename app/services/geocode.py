import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PLACES_PATH = Path(__file__).resolve().parents[2] / "data" / "vector" / "up_places.json"


@lru_cache(maxsize=1)
def load_places() -> tuple[dict[str, Any], ...]:
    if not PLACES_PATH.exists():
        return ()
    return tuple(json.loads(PLACES_PATH.read_text(encoding="utf-8-sig")))


def geocode_place(query: str, limit: int = 5) -> list[dict[str, Any]]:
    normalized = _normalize(query)
    if not normalized:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for place in load_places():
        names = [place.get("name", ""), place.get("district", ""), *(place.get("aliases") or [])]
        score = max(_score(normalized, _normalize(name)) for name in names if name)
        if score > 0:
            scored.append((score, place))

    scored.sort(key=lambda item: (-item[0], item[1].get("name", "")))
    return [
        {
            "name": place["name"],
            "district": place["district"],
            "state": place["state"],
            "lat": place["lat"],
            "lng": place["lng"],
            "source": "local UP gazetteer",
            "confidence": _confidence(score),
        }
        for score, place in scored[: max(1, min(limit, 10))]
    ]


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace(",", " ").split())


def _score(query: str, candidate: str) -> int:
    if query == candidate:
        return 100
    if query in candidate:
        return 80
    if candidate in query:
        return 70
    query_tokens = set(query.split())
    candidate_tokens = set(candidate.split())
    overlap = query_tokens & candidate_tokens
    if overlap:
        return 40 + (10 * len(overlap))
    return 0


def _confidence(score: int) -> str:
    if score >= 90:
        return "high"
    if score >= 70:
        return "medium"
    return "low"

