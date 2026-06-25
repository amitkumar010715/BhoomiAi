from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


SupportedField = Literal[
    "district",
    "elevation_m",
    "nearest_road_distance_m",
    "nearest_water_distance_m",
    "nearest_water_name",
    "nearest_place_name",
]


class FetchRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    fields: list[SupportedField] = Field(..., min_length=1)

    @field_validator("fields")
    @classmethod
    def reject_duplicate_fields(cls, fields: list[SupportedField]) -> list[SupportedField]:
        if len(fields) != len(set(fields)):
            raise ValueError("fields must not contain duplicates")
        return fields


class Location(BaseModel):
    lat: float
    lng: float
    state: str
    district: str | None = None
    inside_service_area: bool


class FieldResult(BaseModel):
    field: str
    value: Any
    unit: str | None = None
    source: str
    source_url: str | None = None
    method: str
    confidence: Literal["low", "medium", "high"]
    fetched_at: str


class Citation(BaseModel):
    source: str
    fields: list[str]


class FetchResponse(BaseModel):
    location: Location
    results: dict[str, FieldResult]
    citations: list[Citation]



class AskRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    question: str = Field(..., min_length=3, max_length=1000)


class AskResponse(BaseModel):
    location: Location
    question: str
    answer: str
    fields_used: list[str]
    results: dict[str, FieldResult]
    citations: list[Citation]
