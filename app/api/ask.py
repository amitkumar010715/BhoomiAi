from fastapi import APIRouter

from app.api.fetch import fetch_location_facts
from app.models.geo import AskRequest, AskResponse, FetchRequest
from app.services.answer import build_answer
from app.services.llm_answer import build_llm_answer
from app.services.planner import plan_fields


router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask_location_question(request: AskRequest) -> AskResponse:
    fields = plan_fields(request.question)
    fetch_response = fetch_location_facts(
        FetchRequest(lat=request.lat, lng=request.lng, fields=fields)
    )

    answer = build_llm_answer(
        question=request.question,
        location=fetch_response.location,
        results=fetch_response.results,
        citations=fetch_response.citations,
    )
    if answer is None:
        answer = build_answer(
            question=request.question,
            location=fetch_response.location,
            results=fetch_response.results,
        )

    return AskResponse(
        location=fetch_response.location,
        question=request.question,
        answer=answer,
        fields_used=fields,
        results=fetch_response.results,
        citations=fetch_response.citations,
    )
