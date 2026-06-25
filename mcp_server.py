"""BhoomiAI MCP server.

Runs over stdio and exposes three tools:
- up_geo_geocode: place/city name -> lat/lng
- up_geo_fetch: lat/lng + fields -> structured facts
- up_geo_ask: lat/lng + question -> LLM-grounded answer
- up_geo_report: lat/lng + optional question -> structured site report

The MCP server acts as a client of the FastAPI app, so the frontend, REST API,
and MCP tools all use the same public backend behavior.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any

import httpx
from dotenv import load_dotenv


SERVER_INFO = {"name": "bhoomiai-up-geo", "version": "0.1.0"}
PROTOCOL_VERSION = "2024-11-05"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8002"

load_dotenv()


TOOLS = [
    {
        "name": "up_geo_geocode",
        "description": "Find latitude/longitude for an Uttar Pradesh city or place name using the BhoomiAI geocode API.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Place query, for example 'Kanpur' or 'Varanasi, Uttar Pradesh'.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "up_geo_fetch",
        "description": "Fetch structured local geospatial facts for a latitude/longitude in Uttar Pradesh using the BhoomiAI fetch API.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "minimum": -90, "maximum": 90},
                "lng": {"type": "number", "minimum": -180, "maximum": 180},
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "district",
                            "elevation_m",
                            "nearest_road_distance_m",
                            "nearest_water_distance_m",
                            "nearest_water_name",
                            "nearest_place_name",
                        ],
                    },
                    "minItems": 1,
                },
            },
            "required": ["lat", "lng", "fields"],
        },
    },
    {
        "name": "up_geo_ask",
        "description": "Ask a natural-language question about a coordinate. The BhoomiAI ask API fetches local facts first, then the LLM explains only supported facts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "minimum": -90, "maximum": 90},
                "lng": {"type": "number", "minimum": -180, "maximum": 180},
                "question": {
                    "type": "string",
                    "description": "Question about this coordinate, for example 'Is this good for warehouse construction?'.",
                },
            },
            "required": ["lat", "lng", "question"],
        },
    },
    {
        "name": "up_geo_report",
        "description": "Generate a structured BhoomiAI site report for a coordinate using the report API.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "minimum": -90, "maximum": 90},
                "lng": {"type": "number", "minimum": -180, "maximum": 180},
                "question": {
                    "type": "string",
                    "description": "Optional report focus, for example 'Generate a report for school construction suitability.'.",
                },
            },
            "required": ["lat", "lng"],
        },
    },]


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_message(message)
            if response is not None:
                write_message(response)
        except Exception as exc:
            write_message(error_response(None, -32603, f"Internal error: {exc}"))
            print(traceback.format_exc(), file=sys.stderr, flush=True)


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    # Notifications do not require responses.
    if request_id is None:
        return None

    if method == "initialize":
        client_version = params.get("protocolVersion") or PROTOCOL_VERSION
        return result_response(
            request_id,
            {
                "protocolVersion": client_version,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )

    if method == "tools/list":
        return result_response(request_id, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            return result_response(request_id, call_tool(tool_name, arguments))
        except Exception as exc:
            return error_response(request_id, -32602, str(exc))

    if method in {"ping", "resources/list", "prompts/list"}:
        empty_key = "resources" if method == "resources/list" else "prompts"
        return result_response(request_id, {} if method == "ping" else {empty_key: []})

    return error_response(request_id, -32601, f"Method not found: {method}")


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "up_geo_geocode":
        data = post_api(
            "/v1/geocode",
            {
                "query": arguments["query"],
                "limit": int(arguments.get("limit", 5)),
            },
        )
    elif name == "up_geo_fetch":
        data = post_api(
            "/v1/fetch",
            {
                "lat": float(arguments["lat"]),
                "lng": float(arguments["lng"]),
                "fields": arguments["fields"],
            },
        )
    elif name == "up_geo_ask":
        data = post_api(
            "/v1/ask",
            {
                "lat": float(arguments["lat"]),
                "lng": float(arguments["lng"]),
                "question": str(arguments["question"]),
            },
        )
    elif name == "up_geo_report":
        payload = {
            "lat": float(arguments["lat"]),
            "lng": float(arguments["lng"]),
        }
        if arguments.get("question"):
            payload["question"] = str(arguments["question"])
        data = post_api("/v1/report", payload)
    else:
        raise ValueError(f"Unknown tool: {name}")

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(data, indent=2, ensure_ascii=False),
            }
        ],
        "structuredContent": data,
    }


def post_api(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    base_url = os.getenv("UP_GEO_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
    url = f"{base_url}{path}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Could not connect to BhoomiAI API at {base_url}. "
            "Start FastAPI first with: python -m uvicorn app.main:app --reload --port 8002"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"BhoomiAI API returned {exc.response.status_code}: {exc.response.text}"
        ) from exc


def result_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def write_message(message: dict[str, Any]) -> None:
    print(json.dumps(message, separators=(",", ":"), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()


