from fastapi import APIRouter, HTTPException

from app.geo.resolvers import FIELD_RESOLVERS, resolve_location
from app.models.geo import FetchRequest, FetchResponse


router = APIRouter()


@router.post("/fetch", response_model=FetchResponse)
def fetch_location_facts(request: FetchRequest) -> FetchResponse:
    location = resolve_location(request.lat, request.lng)

    unsupported_fields = [field for field in request.fields if field not in FIELD_RESOLVERS]
    if unsupported_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported field requested.",
                "unsupported_fields": unsupported_fields,
                "supported_fields": sorted(FIELD_RESOLVERS.keys()),
            },
        )

    results = {}
    citations_by_source: dict[str, set[str]] = {}

    for field in request.fields:
        result = FIELD_RESOLVERS[field](request.lat, request.lng)
        results[field] = result

        if result.source not in citations_by_source:
            citations_by_source[result.source] = set()
        citations_by_source[result.source].add(field)

    citations = [
        {"source": source, "fields": sorted(fields)}
        for source, fields in sorted(citations_by_source.items())
    ]

    return FetchResponse(location=location, results=results, citations=citations)

