from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import csv, httpx, math

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "campus_locations.csv"

app = FastAPI(title="GBU CampusGuide API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

def load_locations():
    with DATA.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["latitude"] = float(r["latitude"])
        r["longitude"] = float(r["longitude"])
    return rows

LOCATIONS = load_locations()

class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float

@app.get("/api/health")
def health():
    return {"status": "ok", "project": "GBU CampusGuide"}

@app.get("/api/locations")
def locations():
    return LOCATIONS

@app.post("/api/route")
async def route(req: RouteRequest):
    # OpenStreetMap community foot router. Coverage inside a campus may be incomplete.
    url = (
        "https://routing.openstreetmap.de/routed-foot/route/v1/driving/"
        f"{req.start_lon},{req.start_lat};{req.end_lon},{req.end_lat}"
    )
    try:
        async with httpx.AsyncClient(timeout=18, headers={"User-Agent": "GBU-CampusGuide/1.0"}) as client:
            response = await client.get(url, params={"overview": "full", "geometries": "geojson", "steps": "true"})
            response.raise_for_status()
            data = response.json()
        if data.get("routes"):
            r = data["routes"][0]
            steps = []
            for leg in r.get("legs", []):
                for s in leg.get("steps", []):
                    instruction = s.get("name") or s.get("ref") or "Continue"
                    maneuver = s.get("maneuver", {})
                    typ = maneuver.get("type", "")
                    mod = maneuver.get("modifier", "")
                    if typ == "depart": instruction = "Start walking"
                    elif typ == "arrive": instruction = "You have reached your destination"
                    elif typ: instruction = f"{typ.replace('-', ' ').title()} {mod}".strip()
                    if s.get("name") and typ not in ("depart", "arrive"):
                        instruction += f" onto {s['name']}"
                    steps.append({"instruction": instruction, "distance_m": round(s.get("distance", 0))})
            return {"source": "OpenStreetMap foot routing", "estimated": True,
                    "distance_m": round(r.get("distance", 0)), "duration_s": round(r.get("duration", 0)),
                    "coordinates": r["geometry"]["coordinates"], "steps": steps}
    except Exception:
        pass

    # Safe fallback: straight-line guide, explicitly marked as an estimate, not a walkable route.
    def haversine(a,b,c,d):
        R=6371000
        p1,p2=math.radians(a),math.radians(c)
        dp=math.radians(c-a); dl=math.radians(d-b)
        x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return 2*R*math.asin(math.sqrt(x))
    dist = haversine(req.start_lat, req.start_lon, req.end_lat, req.end_lon)
    return {"source":"Straight-line fallback", "estimated":True, "warning":"Walking route service unavailable. Open Google Maps for turn-by-turn directions.",
            "distance_m":round(dist), "duration_s":round(dist/1.1),
            "coordinates":[[req.start_lon,req.start_lat],[req.end_lon,req.end_lat]],
            "steps":[{"instruction":"Follow Google Maps for the actual walking route","distance_m":round(dist)}]}
