# BhoomiAI UP Geo API

BhoomiAI is an MVP geospatial intelligence system for Uttar Pradesh. It turns a city name or latitude/longitude into sourced local facts such as district, elevation, nearby roads, nearby water, and an AI answer grounded in those facts.

The product has three working surfaces:

```txt
Frontend UI -> FastAPI
MCP server  -> FastAPI
LLM answer  -> local geo facts first, OpenAI answer second
```

## What It Solves

Land and location decisions in India often require checking scattered GIS datasets manually. This MVP gives one simple interface for questions like:

```txt
Which district is this coordinate in?
What is the elevation here?
How close is the nearest road or waterbody?
Would this coordinate be risky for building a school?
What data is available for this point?
```

The language model is not allowed to invent geospatial values. The backend fetches facts first, then the LLM explains only what those facts support.

## Features

- Static web UI served by FastAPI.
- Clickable Leaflet map for selecting latitude/longitude.
- City/place geocoding from a local UP gazetteer.
- District lookup from Census 2011 district boundaries.
- Elevation lookup from SRTM HGT tiles.
- Road/water/place proximity from an OpenStreetMap sample extract.
- `/v1/ask` endpoint with optional OpenAI answer generation.
- Local stdio MCP server for VS Code Copilot and other MCP clients.

## Run Locally

From the project folder:

```powershell
cd <ABSOLUTE_PATH_TO_REPO>
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

Open the web UI:

```txt
http://127.0.0.1:8002/
```

Open the API docs:

```txt
http://127.0.0.1:8002/docs
```

If you cloned the repo fresh, create the virtual environment first:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment

Create `.env` from `.env.example`:

```env
OPENAI_API_KEY=your_real_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_LLM_ENABLED=true
UP_GEO_API_BASE_URL=http://127.0.0.1:8002
```

Important:

```txt
.env is private and ignored by git.
.env.example is safe to commit.
```

If `OPENAI_LLM_ENABLED=false` or no valid key is present, `/v1/ask` returns a local template answer instead of an LLM-written answer.

## API Endpoints

### Health

```txt
GET /health
```

### Geocode

```txt
POST /v1/geocode
```

Example:

```json
{
  "query": "Kanpur",
  "limit": 3
}
```

### Fetch Facts

```txt
POST /v1/fetch
```

Example:

```json
{
  "lat": 26.4499,
  "lng": 80.3319,
  "fields": [
    "district",
    "elevation_m",
    "nearest_road_distance_m",
    "nearest_water_distance_m",
    "nearest_water_name",
    "nearest_place_name"
  ]
}
```

### Ask Question

```txt
POST /v1/ask
```

Example:

```json
{
  "lat": 26.4499,
  "lng": 80.3319,
  "question": "Would this coordinate be risky for building a school? Mention only what the data supports."
}
```

Flow:

```txt
question
  -> deterministic field planner
  -> local geospatial resolvers
  -> sourced facts
  -> OpenAI answer if enabled
  -> template fallback if LLM is unavailable
```
### Generate Site Report

```txt
POST /v1/report
```

Example:

```json
{
  "lat": 26.4499,
  "lng": 80.3319,
  "question": "Generate a site report for this coordinate."
}
```

Returns a structured report with location, summary, available fields, unavailable fields, facts, citations, and `report_markdown`.


## Deploy on Render

This repo includes `render.yaml` for deploying the FastAPI app as a Render Web Service.

Render settings:

```txt
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

After deploy, Render gives a public URL like:

```txt
https://bhoomiai-up-geo.onrender.com
```

That URL opens the BhoomiAI frontend UI because the FastAPI app serves `app/static/index.html` at `/`.

Set this secret in the Render dashboard:

```txt
OPENAI_API_KEY=your_real_key_here
```

Notes:

```txt
The ignored OSM sample file is not deployed to Render.
District lookup and committed SRTM tiles will work.
Road/water/place proximity needs the OSM sample file or a hosted data store.
```

## MCP Server

The MCP server exposes BhoomiAI as tools for AI clients.

Tools:

```txt
up_geo_geocode(query, limit=5)
up_geo_fetch(lat, lng, fields)
up_geo_ask(lat, lng, question)
up_geo_report(lat, lng, question optional)
```

Current MCP behavior:

```txt
up_geo_geocode -> POST /v1/geocode
up_geo_fetch   -> POST /v1/fetch
up_geo_ask     -> POST /v1/ask
up_geo_report  -> POST /v1/report
```

That means the FastAPI server must be running before the MCP client calls tools.

Start FastAPI first:

```powershell
cd <ABSOLUTE_PATH_TO_REPO>
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

Then configure your MCP client.

### VS Code Copilot MCP Config

Use this shape for VS Code/Copilot. Replace `<ABSOLUTE_PATH_TO_REPO>` with your local clone path.

```json
{
  "servers": {
    "bhoomiai-up-geo": {
      "type": "stdio",
      "command": "<ABSOLUTE_PATH_TO_REPO>\\.venv\\Scripts\\python.exe",
      "args": [
        "<ABSOLUTE_PATH_TO_REPO>\\mcp_server.py"
      ],
      "cwd": "<ABSOLUTE_PATH_TO_REPO>"
    }
  }
}
```


### Generic MCP Config

Some MCP clients use `mcpServers` instead of `servers`:

```json
{
  "mcpServers": {
    "bhoomiai-up-geo": {
      "command": "<ABSOLUTE_PATH_TO_REPO>\\.venv\\Scripts\\python.exe",
      "args": [
        "<ABSOLUTE_PATH_TO_REPO>\\mcp_server.py"
      ],
      "cwd": "<ABSOLUTE_PATH_TO_REPO>"
    }
  }
}
```

A clone-safe version is also in `mcp_config.example.json`.

## Data Currently Integrated

### District Boundaries

Files:

```txt
data/vector/2011_Dist.shp
data/vector/2011_Dist.shx
data/vector/2011_Dist.dbf
data/vector/2011_Dist.prj
```

Source:

```txt
DataMeet India Districts Census 2011
https://github.com/datameet/maps/tree/master/Districts/Census_2011
```

Used by:

```txt
district
location.district
location.inside_service_area
```

### Elevation

Files:

```txt
data/raster/srtm/N26E080.hgt.gz
data/raster/srtm/N25E082.hgt.gz
data/raster/srtm/N28E077.hgt.gz
```

Source:

```txt
SRTM DEM via AWS elevation-tiles-prod
https://s3.amazonaws.com/elevation-tiles-prod/skadi/
```

Used by:

```txt
elevation_m
```

Current downloaded tile coverage:

```txt
N26E080: Lucknow/Kanpur area
N25E082: Varanasi area
N28E077: Noida area
```

### OSM Sample Data

File:

```txt
data/vector/osm_up_samples.geojson
```

Contains sample data for roads, water, and places around selected areas such as Lucknow, Varanasi, Noida, Agra, and Gorakhpur depending on the downloaded sample.

Used by:

```txt
nearest_road_distance_m
nearest_water_distance_m
nearest_water_name
nearest_place_name
```

### Local Gazetteer

File:

```txt
data/vector/up_places.json
```

Used by:

```txt
/v1/geocode
up_geo_geocode
city buttons and search-style workflows
```


## Large Data Note

`data/vector/osm_up_samples.geojson` is generated local data and is larger than GitHub's normal single-file limit. It is ignored by git. After cloning, regenerate or download the OSM sample data with the script in `scripts/` before using road/water/place proximity features.

## Known Limitations

- This is an MVP, not a legal land record system.
- OSM road/water/place coverage is sample coverage, not full Uttar Pradesh coverage yet.
- Flood risk, soil, parcel ownership, and official land-use classification are not integrated yet.
- Elevation coverage only works where SRTM tiles have been downloaded.
- LLM answers are explanations of available facts, not independent survey or legal advice.

## Next Steps

Recommended build order:

1. Add a `Generate Site Report` button in the UI.
2. Download remaining SRTM tiles for full UP elevation coverage.
3. Replace sample OSM GeoJSON with a full Uttar Pradesh OSM extract.
4. Add a flood/water-risk dataset.
5. Add soil or land-use/land-cover data.
6. Move large geospatial data into PostGIS for faster nearest-neighbor queries.
7. Prepare GitHub release notes and deployment instructions.




