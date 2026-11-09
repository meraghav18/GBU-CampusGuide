
import os
import csv
import httpx
import math

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# -----------------------------
# Paths and Configuration
# -----------------------------

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "campus_locations.csv"

app = FastAPI(
    title="GBU CampusGuide API",
    version="1.0.0"
)


# -----------------------------
# CORS Configuration
# -----------------------------

frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

if frontend_origin:
    allowed_origins.append(frontend_origin.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Load Campus Locations
# -----------------------------

def load_locations():
    with DATA.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        row["latitude"] = float(row["latitude"])
        row["longitude"] = float(row["longitude"])

    return rows


LOCATIONS = load_locations()


# -----------------------------
# Route Request Model
# -----------------------------

class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float


# -----------------------------
# Health Check API
# -----------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "project": "GBU CampusGuide"
    }


# -----------------------------
# Campus Locations API
# -----------------------------

@app.get("/api/locations")
def locations():
    return LOCATIONS


# -----------------------------
# Campus Route API
# -----------------------------

@app.post("/api/route")
async def route(req: RouteRequest):

    # OpenStreetMap community foot routing service
    url = (
        "https://routing.openstreetmap.de/routed-foot/route/v1/driving/"
        f"{req.start_lon},{req.start_lat};"
        f"{req.end_lon},{req.end_lat}"
    )

    try:
        async with httpx.AsyncClient(
            timeout=18,
            headers={"User-Agent": "GBU-CampusGuide/1.0"}
        ) as client:

            response = await client.get(
                url,
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "true"
                }
            )

            response.raise_for_status()
            data = response.json()

        if data.get("routes"):

            route_data = data["routes"][0]
            steps = []

            for leg in route_data.get("legs", []):

                for step in leg.get("steps", []):

                    instruction = (
                        step.get("name")
                        or step.get("ref")
                        or "Continue"
                    )

                    maneuver = step.get("maneuver", {})
                    maneuver_type = maneuver.get("type", "")
                    modifier = maneuver.get("modifier", "")

                    if maneuver_type == "depart":
                        instruction = "Start walking"

                    elif maneuver_type == "arrive":
                        instruction = "You have reached your destination"

                    elif maneuver_type:
                        instruction = (
                            f"{maneuver_type.replace('-', ' ').title()} "
                            f"{modifier}"
                        ).strip()

                    if (
                        step.get("name")
                        and maneuver_type not in ("depart", "arrive")
                    ):
                        instruction += f" onto {step['name']}"

                    steps.append({
                        "instruction": instruction,
                        "distance_m": round(step.get("distance", 0))
                    })

            return {
                "source": "OpenStreetMap foot routing",
                "estimated": True,
                "distance_m": round(route_data.get("distance", 0)),
                "duration_s": round(route_data.get("duration", 0)),
                "coordinates": route_data["geometry"]["coordinates"],
                "steps": steps
            }

    except Exception:
        pass


    # -----------------------------
    # Straight-Line Fallback
    # -----------------------------

    def haversine(lat1, lon1, lat2, lon2):

        earth_radius = 6371000

        p1 = math.radians(lat1)
        p2 = math.radians(lat2)

        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        x = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(p1)
            * math.cos(p2)
            * math.sin(delta_lon / 2) ** 2
        )

        return 2 * earth_radius * math.asin(math.sqrt(x))


    distance = haversine(
        req.start_lat,
        req.start_lon,
        req.end_lat,
        req.end_lon
    )

    return {
        "source": "Straight-line fallback",
        "estimated": True,
        "warning": (
            "Walking route service unavailable. "
            "Open Google Maps for turn-by-turn directions."
        ),
        "distance_m": round(distance),
        "duration_s": round(distance / 1.1),
        "coordinates": [
            [req.start_lon, req.start_lat],
            [req.end_lon, req.end_lat]
        ],
        "steps": [
            {
                "instruction": (
                    "Follow Google Maps for the actual walking route"
                ),
                "distance_m": round(distance)
            }
        ]
    }
