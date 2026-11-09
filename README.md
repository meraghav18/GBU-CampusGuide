# GBU CampusGuide

React + TypeScript + Vite frontend, FastAPI backend, Leaflet/OpenStreetMap map, browser GPS and browser speech synthesis.

## Requirements
- Python 3.10+
- Node.js 20+
- Internet connection (map tiles, Google Maps directions, and OSM foot-routing service)

## Run on Windows

### 1. Start backend
Open PowerShell in the `backend` folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000. API docs: http://localhost:8000/docs

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

### 2. Start frontend
Open a SECOND PowerShell in the `frontend` folder:

```powershell
npm install
npm run dev
```

Open the URL shown by Vite, normally http://localhost:5173.

## Navigation behavior
- Choose a destination from the homepage search or destination cards.
- Starting point options: manually select one of the five places, detect current location, or start at Gate No. 1.
- If GPS detects the user is outside the campus geofence, Google Maps opens a walking route from the user's coordinates to Gate No. 1. The chosen destination remains selected in CampusGuide.
- After reaching Gate No. 1, return to CampusGuide and press **Start Campus Navigation**. No automatic navigation start.
- Map, route steps, and browser voice are available when the routing service returns a route.
- Hindi/English toggle is in the top navbar.

## Important accuracy notes
- Coordinates are user-provided Google Maps values, not field-surveyed coordinates.
- The five campus locations are loaded from `backend/data/campus_locations.csv`.
- Campus footpath coverage in OpenStreetMap may be incomplete. The backend uses the community OSM foot-routing endpoint and clearly labels the route as estimated. If routing is unavailable, it shows a straight-line fallback warning; use Google Maps for turn-by-turn navigation until campus paths are verified.
- The old Gate No. 1 coordinate in `route_waypoints.csv` is retained as historical supplied data; the application uses the latest `campus_locations.csv` coordinates as its source of truth.
- GPS requires browser permission and a secure context (localhost is allowed). On a deployed site, use HTTPS.
- Google Maps is opened through a Directions URL; no API key is needed for this link-based integration. A paid Google Maps Platform API integration is not configured in this starter version.

## Project structure
```
GBU-CampusGuide/
  backend/
    app/main.py
    data/*.csv
    requirements.txt
  frontend/
    src/App.tsx
    src/style.css
    public/images/
  README.md
```
