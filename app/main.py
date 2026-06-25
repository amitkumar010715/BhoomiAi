from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.ask import router as ask_router

from app.api.fetch import router as fetch_router
from app.api.geocode import router as geocode_router
from app.api.report import router as report_router


STATIC_DIR = Path(__file__).resolve().parent / "static"


app = FastAPI(
    title="UP Geo API",
    description="Coordinate-level land intelligence API for Uttar Pradesh.",
    version="0.1.0",
)

app.include_router(fetch_router, prefix="/v1", tags=["fetch"])
app.include_router(ask_router, prefix="/v1", tags=["ask"])
app.include_router(geocode_router, prefix="/v1", tags=["geocode"])
app.include_router(report_router, prefix="/v1", tags=["report"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}




@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


