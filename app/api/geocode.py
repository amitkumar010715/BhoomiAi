from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.services.geocode import geocode_place


router = APIRouter()


class GeocodeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=5, ge=1, le=10)


class GeocodeResponse(BaseModel):
    query: str
    results: list[dict]


@router.post("/geocode", response_model=GeocodeResponse)
def geocode(request: GeocodeRequest) -> GeocodeResponse:
    return GeocodeResponse(
        query=request.query,
        results=geocode_place(request.query, request.limit),
    )
