# 🚐 GaonRide AI

**AI-powered rural shared transportation coordination for Indian villages**

In rural India, millions of villagers rely on infrequent and unreliable shared transport to reach
towns for work, healthcare, and markets. GaonRide AI aggregates travel demand in real-time, uses
AI to group passengers by route and time, and connects them with local drivers — so every seat is
filled and no one is left stranded at a roadside.

---

## Features

- **Voice ride requests** — speak your journey in any natural phrasing; Groq Whisper transcribes it
- **Text ride requests** — type a request like "Gerua to Rangia tomorrow 9 AM" and submit
- **AI extraction** — Llama 3.3 70B parses origin, destination, date, and time from free text
- **Smart passenger matching** — groups passengers travelling the same route at the same time
- **Driver dashboard** — real-time view of demand groups with passenger counts and route map
- **Interactive Leaflet map** — route visualisation on OpenStreetMap (no API key required)
- **Demo seed data** — one-click button populates realistic example groups for instant testing
- **Degraded mode** — the app runs fully without a Groq key; only AI features are disabled

---

## Prerequisites

- **Python 3.11 or higher**
- **A free Groq API key** from <https://console.groq.com> *(required for voice and AI parsing)*
- No other paid services or external databases required

---

## Installation

```bash
git clone <repository-url>
cd gaonride-ai
pip install -r requirements.txt
```

---

## Configuration

```bash
cp .env.example .env
```

Open `.env` and add your Groq API key:

```
GROQ_API_KEY=your_groq_api_key_here
```

> **Note:** The app starts and runs without a key. Voice input and AI parsing will show a
> "Groq API key not configured" message, but manual text entry and all matching logic continue
> to work normally.

---

## Running the app

```bash
python run.py
```

Then open <http://localhost:8000> in your browser.

To verify the service is healthy, visit <http://localhost:8000/api/health> — you should see:

```json
{"ai_available": true, "db_ok": true, "message": "GaonRide AI is fully operational."}
```

---

## Quick demo walkthrough

1. Open <http://localhost:8000>
2. Click **"I'm a Driver"** → click **"Load Demo Data"** to populate example groups on the map
3. Click **"I'm a Passenger"** → type a request, e.g. `Gerua to Rangia tomorrow 9 AM`
4. Submit and see yourself matched into an existing group (or a new one created)
5. If you have a Groq API key: switch to the **Voice** tab and speak your request
6. Return to the Driver Dashboard to see updated passenger counts

---

## Running tests

```bash
python -m pytest tests/ -v
```

---

## Architecture overview

| Layer | Technology |
|---|---|
| Backend framework | FastAPI (Python 3.11+) |
| Database | SQLite via SQLAlchemy (no external DB) |
| AI inference | Groq — Whisper (speech-to-text) + Llama 3.3 70B (NLP parsing) |
| Maps | Leaflet + OpenStreetMap (no API key) |
| Routing | OSRM public API |
| Geocoding | Nominatim public API |
| Frontend | Vanilla HTML / CSS / JavaScript (no build step) |

---

## Degraded mode (no API key)

When `GROQ_API_KEY` is not set:

- The app starts and serves all pages normally
- `/api/health` returns `{"ai_available": false, ...}`
- Submitting text via the **Voice / Parse** tab returns HTTP 503 with a clear message
- Manual text entry on the **Passenger** page and all route-matching logic work fully
- Demo data, maps, and the Driver Dashboard work fully

---

## Project structure

```
gaonride-ai/
├── backend/
│   ├── main.py            # FastAPI app, lifespan, routers, static mount
│   ├── config.py          # Environment variables, AI_AVAILABLE flag
│   ├── database.py        # SQLAlchemy engine and init_db()
│   ├── models.py          # ORM models (RideRequest, RideGroup, Driver)
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── services/
│   │   ├── groq_service.py   # Whisper transcription + Llama NLP parsing
│   │   ├── matching.py       # Passenger-to-group matching logic
│   │   └── geo.py            # Geocoding and distance utilities
│   └── routers/
│       ├── requests.py    # POST /api/requests
│       ├── groups.py      # GET /api/groups
│       ├── drivers.py     # Driver registration
│       ├── voice.py       # POST /api/voice/transcribe, /api/voice/parse
│       ├── geo.py         # POST /api/geo/geocode
│       └── seed.py        # POST /api/seed — loads demo data
├── frontend/
│   ├── index.html         # Landing page
│   ├── passenger.html     # Passenger request page
│   ├── driver.html        # Driver dashboard
│   └── static/
│       ├── css/style.css
│       ├── js/
│       │   ├── app.js
│       │   ├── passenger.js
│       │   ├── driver.js
│       │   ├── map.js
│       │   └── voice.js
│       └── favicon.svg
├── tests/
│   ├── test_health.py
│   ├── test_requests.py
│   ├── test_groups.py
│   └── test_matching.py
├── .env.example
├── requirements.txt
├── pytest.ini
└── run.py
```

---

## Technology credits

- [Groq](https://groq.com) — ultra-fast AI inference (Whisper + Llama 3.3 70B)
- [OpenStreetMap](https://openstreetmap.org) contributors — map data (ODbL licence)
- [Leaflet](https://leafletjs.com) — interactive map rendering
- [OSRM](https://project-osrm.org) — open-source routing engine
- [Nominatim](https://nominatim.openstreetmap.org) — geocoding service
- [FastAPI](https://fastapi.tiangolo.com) — modern Python web framework
- [SQLAlchemy](https://sqlalchemy.org) — SQL toolkit and ORM
