from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.api.fetch import fetch_location_facts
from app.models.geo import Citation, FetchRequest, FieldResult, Location
from app.services.answer import build_answer
from app.services.llm_answer import build_llm_answer


router = APIRouter()

REPORT_FIELDS = [
    "district",
    "elevation_m",
    "nearest_road_distance_m",
    "nearest_water_distance_m",
    "nearest_water_name",
    "nearest_place_name",
]

DEFAULT_REPORT_QUESTION = (
    "Generate a concise site intelligence report for this coordinate. "
    "Mention only what the provided data supports and clearly say what is unavailable."
)


class ReportRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    question: str | None = Field(default=None, max_length=1000)


class ReportResponse(BaseModel):
    location: Location
    question: str
    summary: str
    available_fields: list[str]
    unavailable_fields: list[str]
    results: dict[str, FieldResult]
    citations: list[Citation]
    report_markdown: str


@router.post("/report", response_model=ReportResponse)
def generate_site_report(request: ReportRequest) -> ReportResponse:
    question = (request.question or DEFAULT_REPORT_QUESTION).strip() or DEFAULT_REPORT_QUESTION
    fetch_response = fetch_location_facts(
        FetchRequest(lat=request.lat, lng=request.lng, fields=REPORT_FIELDS)
    )

    available_fields = [
        field for field, result in fetch_response.results.items() if is_available(result)
    ]
    unavailable_fields = [
        field for field, result in fetch_response.results.items() if not is_available(result)
    ]

    summary = build_llm_answer(
        question=question,
        location=fetch_response.location,
        results=fetch_response.results,
        citations=fetch_response.citations,
    )
    if summary is None:
        summary = build_answer(
            question=question,
            location=fetch_response.location,
            results=fetch_response.results,
        )

    report_markdown = build_report_markdown(
        location=fetch_response.location,
        question=question,
        summary=summary,
        results=fetch_response.results,
        citations=fetch_response.citations,
        available_fields=available_fields,
        unavailable_fields=unavailable_fields,
    )

    return ReportResponse(
        location=fetch_response.location,
        question=question,
        summary=summary,
        available_fields=available_fields,
        unavailable_fields=unavailable_fields,
        results=fetch_response.results,
        citations=fetch_response.citations,
        report_markdown=report_markdown,
    )


def is_available(result: FieldResult) -> bool:
    return result.value is not None and result.value != ""


def build_report_markdown(
    *,
    location: Location,
    question: str,
    summary: str,
    results: dict[str, FieldResult],
    citations: list[Citation],
    available_fields: list[str],
    unavailable_fields: list[str],
) -> str:
    lines = [
        "# BhoomiAI Site Report",
        "",
        "## Location",
        f"- Latitude: {location.lat}",
        f"- Longitude: {location.lng}",
        f"- State: {location.state}",
        f"- District: {location.district or 'Unavailable'}",
        f"- Inside service area: {'Yes' if location.inside_service_area else 'No'}",
        "",
        "## Question",
        question,
        "",
        "## Summary",
        summary,
        "",
        "## Facts",
    ]

    for field, result in results.items():
        value = format_value(result)
        source = result.source or "Unknown source"
        confidence = result.confidence
        lines.append(f"- {label_for(field)}: {value} | Source: {source} | Confidence: {confidence}")

    lines.extend(
        [
            "",
            "## Data Coverage",
            f"- Available: {', '.join(map(label_for, available_fields)) or 'None'}",
            f"- Unavailable: {', '.join(map(label_for, unavailable_fields)) or 'None'}",
            "",
            "## Sources",
        ]
    )

    if citations:
        for citation in citations:
            lines.append(f"- {citation.source}: {', '.join(map(label_for, citation.fields))}")
    else:
        lines.append("- No sources returned.")

    lines.extend(
        [
            "",
            "## Disclaimer",
            "This MVP report is generated from currently integrated datasets only. It is not a legal land record, survey, flood certificate, or construction approval.",
        ]
    )

    return "\n".join(lines)


def format_value(result: FieldResult) -> str:
    if result.value is None or result.value == "":
        return "Unavailable"
    return f"{result.value} {result.unit}" if result.unit else str(result.value)


def label_for(field: str) -> str:
    return field.replace("_", " ")
