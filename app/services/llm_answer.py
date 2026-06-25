import json

from openai import OpenAI, OpenAIError

from app.models.geo import Citation, FieldResult, Location
from app.services.config import get_settings


SYSTEM_PROMPT = """You are BhoomiAI, a careful geospatial assistant for Uttar Pradesh.
Use only the provided resolver facts. Do not invent elevation, road distance,
water distance, district, place names, flood risk, soil, or land suitability facts.
If a value is null/unavailable, say it is unavailable in the current local dataset.
Give a concise, useful answer for the user's question. Mention uncertainty and
missing data clearly. Do not include markdown tables.
"""


def build_llm_answer(
    question: str,
    location: Location,
    results: dict[str, FieldResult],
    citations: list[Citation],
) -> str | None:
    settings = get_settings()
    if not settings.openai_llm_enabled or not settings.openai_api_key:
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    payload = _build_payload(question, location, results, citations)

    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, indent=2)},
            ],
            max_output_tokens=450,
        )
    except OpenAIError:
        return None

    return (response.output_text or "").strip() or None


def _build_payload(
    question: str,
    location: Location,
    results: dict[str, FieldResult],
    citations: list[Citation],
) -> dict:
    return {
        "task": "Answer the user question using only these fetched geospatial facts.",
        "question": question,
        "location": location.model_dump(),
        "facts": {
            field: result.model_dump()
            for field, result in results.items()
        },
        "citations": [citation.model_dump() for citation in citations],
        "answer_rules": [
            "Use only facts in the facts object.",
            "If a fact value is null, say it is unavailable in current local coverage.",
            "Do not claim flood, soil, parcel, or construction suitability unless supported by facts.",
            "Keep the answer short and practical.",
        ],
    }
