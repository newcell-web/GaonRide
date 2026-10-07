# GaonRide AI — Implementation Plan

## Top-Level Overview

Build a complete, fully-runnable hackathon project called **GaonRide AI**: an AI-powered rural shared transportation coordination platform for Indian villages.

The system lets villagers submit travel requests (by voice or text), groups them with others travelling to the same destination at similar times, and lets drivers see and claim those demand groups. It is NOT a ride-hailing clone — it is a demand-coordination platform.

**Single external secret required:** `GROQ_API_KEY` only.

**Stack:**
- Backend: Python, FastAPI, SQLite, SQLAlchemy, Pydantic, Groq SDK
- Frontend: HTML, CSS, Vanilla JavaScript, Leaflet
- Maps: OpenStreetMap tiles (no key), Nominatim geocoding (server-side, cached), OSRM routing (with Haversine fallback)

**Startup:** `pip install -r requirements.txt` → `python run.py`

**Implementation order is strict** — each sub-task depends on the ones before it.

---

## Sub-Task 1 — Project Scaffold and Configuration ✅

### Intent
Create the project directory structure, dependency manifest, environment configuration, and application entry points. Everything else builds on top of this skeleton.

### Expected Outcomes
- All directories exist
- `requirements.txt` lists every dependency
- `.env.example` documents the only required key
- `.gitignore` excludes `.env`, `__pycache__`, SQLite file, temp audio files
- `run.py` starts the app with one command
- `backend/config.py` loads `GROQ_API_KEY` from `.env` and exposes an `AI_AVAILABLE` boolean flag
- `backend/main.py` creates the FastAPI app, registers routers (stubs for now), mounts `frontend/` as static files, and includes a `/api/health` endpoint returning DB status and `ai_available`

### Todo List
- [ ] Create directory tree: `backend/routers/`, `backend/services/`, `frontend/static/css/`, `frontend/static/js/`, `tests/`
- [ ] Write `requirements.txt` with: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic`, `python-dotenv`, `groq`, `httpx`, `pytest`, `pytest-anyio`, `aiofiles`
- [ ] Write `.env.example` with `GROQ_API_KEY=your_groq_api_key_here`
- [ ] Write `.gitignore` excluding `.env`, `*.db`, `__pycache__`, `*.pyc`, `tmp_audio/`, `.pytest_cache/`
- [ ] Write `backend/config.py` — load dotenv, expose `GROQ_API_KEY`, `AI_AVAILABLE`, `TIME_TOLERANCE_MIN=90`, `DEST_MATCH_KM=5.0`, `ORIGIN_RADIUS_KM=10.0`, `GROUP_SCORE_THRESHOLD=0.55`
- [ ] Write `run.py` — calls `uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)`
- [ ] Write `backend/main.py` — create app, placeholder router includes, mount `frontend/` as StaticFiles at `/`, add `/api/health` endpoint
- [ ] Create `backend/__init__.py`, `backend/routers/__init__.py`, `backend/services/__init__.py`

### Relevant Context
- `backend/config.py` is imported by every service — it must exist before any other backend file
- `AI_AVAILABLE = bool(GROQ_API_KEY)` — no key means AI features return 503 with a human-readable message
- Static file mount: `app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")` — must be added LAST, after all API routes

### Status
[x] done

---

## Sub-Task 2 — Database Models and Initialization

### Intent
Define all SQLAlchemy ORM models, create the SQLite engine, and write the table initialization logic. All routers and services depend on these models.

### Expected Outcomes
- `backend/database.py` provides `engine`, `SessionLocal`, and `get_db` dependency
- `backend/models.py` defines all five tables with correct columns, types, foreign keys, and defaults
- Running `backend/database.py` directly (or importing `main.py`) creates the SQLite file and all tables
- Tables: `ride_requests`, `ride_groups`, `driver_offers`, `geocode_cache`, and a `demo_meta` marker

### Todo List
- [ ] Write `backend/database.py` — `create_engine` with `gaonride.db`, `check_same_thread=False`, `SessionLocal`, `Base`, `get_db` FastAPI dependency, `init_db()` function that calls `Base.metadata.create_all`
- [ ] Write `backend/models.py` with these tables:
  - `RideGroup`: id, destination_text, dest_lat, dest_lon, travel_date, suggested_departure, total_passengers, status (active/completed), is_demo, created_at
  - `RideRequest`: id, passenger_name, passenger_phone, origin_text, destination_text, origin_lat, origin_lon, dest_lat, dest_lon, travel_date, preferred_time, passenger_count, language, notes, status (pending/grouped/confirmed), group_id (FK to RideGroup), is_demo, created_at, ai_parsed (bool)
  - `DriverOffer`: id, group_id (FK), driver_name, driver_phone, vehicle_type, available_seats, proposed_departure, status (pending/confirmed), created_at
  - `GeocodeCache`: id, query_text (unique), lat, lon, display_name, cached_at
- [ ] Call `init_db()` from `backend/main.py` on startup

### Relevant Context
- `is_demo` flag on `RideRequest` and `RideGroup` allows the "Clear Demo Data" button to delete only seeded rows
- `ai_parsed` on `RideRequest` signals the frontend to show the AI interpretation badge
- Use `SQLite` with `StaticPool` only in tests; production uses the default pool
- All datetime/date/time columns should use Python-native types via SQLAlchemy `Date`, `Time`, `DateTime`

### Status
[x] done

---

## Sub-Task 3 — Pydantic Schemas

### Intent
Define all request and response shapes used by the API. Schemas act as the contract between frontend and backend and as the validation layer for LLM-generated output.

### Expected Outcomes
- `backend/schemas.py` contains all Pydantic models
- Every router can import the schema it needs without circular imports
- The `RideRequestParsed` schema is the authoritative shape that Groq LLM output is validated against

### Todo List
- [x] Write `backend/schemas.py` with:
  - `RideRequestParsed` — origin, destination, travel_date (date), preferred_time (time), passenger_count (int, default 1), language (str, default "en"), notes (str, optional) — this is what the LLM must return
  - `RideRequestCreate` — all fields of `RideRequestParsed` plus passenger_name, passenger_phone (optional)
  - `RideRequestOut` — full request including id, status, group_id, ai_parsed, created_at
  - `RideGroupOut` — group id, destination, travel_date, suggested_departure, total_passengers, status, member count, associated driver offer if any
  - `DriverOfferCreate` — group_id, driver_name, driver_phone, vehicle_type, available_seats, proposed_departure
  - `DriverOfferOut` — full offer including id, status, created_at
  - `TranscribeResponse` — text (str)
  - `ParseResponse` — parsed RideRequestParsed + raw_text (str) + confidence note
  - `HealthResponse` — ai_available (bool), db_ok (bool), message (str)

### Relevant Context
- `RideRequestParsed` must have validators: `travel_date` cannot be in the past, `passenger_count` must be between 1 and 20
- Do not use `orm_mode` — use `model_config = ConfigDict(from_attributes=True)` (Pydantic v2 style)
- `preferred_time` should accept strings like "09:00", "9 AM", and be coerced to a `datetime.time`

### Status
[x] done

---

## Sub-Task 4 — Geo Service

### Intent
Implement the geocoding and routing service: Nominatim lookup with SQLite caching, OSRM routing, and a Haversine fallback. This service is used by both the matching service and the geo router.

### Expected Outcomes
- `backend/services/geo_service.py` provides three public functions: `geocode(place: str, db) -> tuple[float,float] | None`, `get_route(origin_coords, dest_coords) -> dict`, `haversine(lat1, lon1, lat2, lon2) -> float`
- Geocoding checks the `GeocodeCache` table first; only calls Nominatim on a cache miss
- Nominatim requests include `User-Agent: GaonRide-AI/1.0` and a 1-second minimum interval between calls
- OSRM call has a 5-second timeout; if it fails for any reason, the function returns Haversine distance and `routing_method: "haversine"`
- All external HTTP is done with `httpx` (async)

### Todo List
- [x] Implement `haversine(lat1, lon1, lat2, lon2) -> float` — returns distance in kilometres using the Haversine formula
- [x] Implement `geocode(place_name, db_session)` — check cache, then call `https://nominatim.openstreetmap.org/search` with `q=`, `format=json`, `limit=1`, `User-Agent` header; store result in `GeocodeCache`; return `(lat, lon)` or `None` on failure; enforce 1-second rate limit using a module-level asyncio lock and timestamp
- [x] Implement `get_route(origin_lat, origin_lon, dest_lat, dest_lon)` — call OSRM `http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false`; parse distance (metres → km) and duration (seconds → minutes); on any error return `{"distance_km": haversine(...), "duration_min": None, "routing_method": "haversine"}`
- [x] Add module-level `_last_nominatim_call` float and `_nominatim_lock` asyncio.Lock to enforce rate limiting

### Relevant Context
- `geocode` is called only after the user confirms a request — never on keystrokes or autocomplete
- If both lat/lon in a request are already provided (seed data), `geocode` is not called again
- The function must never raise an exception that propagates to the router — always catch and return `None` or a fallback dict

### Status
[x] done

---

## Sub-Task 5 — Matching Service

### Intent
Implement the deterministic ride-grouping algorithm. Given a new RideRequest, find compatible existing requests and either add the new request to an existing group or create a new group. This is the core "AI coordination" logic of the platform (though it uses no LLM).

### Expected Outcomes
- `backend/services/matching_service.py` provides one public function: `assign_to_group(request: RideRequest, db: Session) -> RideGroup`
- The function is fully deterministic and unit-testable without a database (pure scoring logic is extracted into a separate function)
- Scoring weights and thresholds come from `config.py`
- The algorithm is simple enough to explain in 2 minutes at a hackathon

### Todo List
- [x] Implement `score_compatibility(r1: dict, r2: dict) -> float` — pure function that takes two dicts of `{dest_lat, dest_lon, origin_lat, origin_lon, travel_date, preferred_time, passenger_count}` and returns a score 0.0–1.0 using:
  - destination score (0.5 weight): 1.0 if dest strings match; else `max(0, 1 - haversine(dest1, dest2) / DEST_MATCH_KM)`
  - time score (0.3 weight): `1.0 - abs(delta_minutes) / TIME_TOLERANCE_MIN`, clamped to 0
  - origin score (0.2 weight): 1.0 if `haversine(origin1, origin2) <= ORIGIN_RADIUS_KM` else 0.5 if within 2× else 0
- [x] Implement `assign_to_group(request, db)`:
  1. Fetch all `RideRequest` rows with `status != 'confirmed'` and `travel_date == request.travel_date` and `|preferred_time - request.preferred_time| <= TIME_TOLERANCE_MIN`
  2. For each existing `RideGroup` containing at least one of those requests, compute average compatibility score of the new request against all group members
  3. If best group score >= `GROUP_SCORE_THRESHOLD`, add request to that group
  4. Else create a new `RideGroup` with `destination_text` and coords from the request
  5. Update `request.group_id`, `request.status = 'grouped'`
  6. Recalculate group `suggested_departure` = average preferred_time of all members, `total_passengers` = sum of passenger_counts
  7. Commit and return the group
- [x] Handle the edge case where `origin_lat`/`origin_lon` or `dest_lat`/`dest_lon` are None — fall back to string comparison for destination, skip origin scoring

### Relevant Context
- `score_compatibility` should be imported and tested directly in `tests/test_matching.py` — keep it a pure function
- The `suggested_departure` calculation: average the minutes-since-midnight of all member `preferred_time` values, convert back to a `datetime.time`
- Config constants: `TIME_TOLERANCE_MIN`, `DEST_MATCH_KM`, `ORIGIN_RADIUS_KM`, `GROUP_SCORE_THRESHOLD` from `backend/config.py`

### Status
[x] done

---

## Sub-Task 6 — Groq Service ✅

### Intent
Implement the two AI operations: speech-to-text (Groq Whisper) and natural-language-to-structured-JSON (Groq chat LLM). Both operations must degrade gracefully when `GROQ_API_KEY` is absent.

### Expected Outcomes
- `backend/services/groq_service.py` provides `transcribe_audio(file_path: str) -> str` and `parse_request_text(text: str, today: date) -> RideRequestParsed`
- Both functions raise a specific `AIUnavailableError` if `AI_AVAILABLE` is False
- LLM output is parsed with Pydantic — if it fails, the function retries once with a stricter prompt; if still invalid, raises `AIParseError`
- Temp audio file is always deleted after `transcribe_audio` returns, success or failure

### Todo List
- [ ] Define `AIUnavailableError` and `AIParseError` as custom exceptions at the top of the file
- [ ] Implement `transcribe_audio(file_path)`:
  - Check `AI_AVAILABLE`; raise `AIUnavailableError` if False
  - Open file in binary mode, call `groq_client.audio.transcriptions.create(model="whisper-large-v3", file=audio_file)`
  - Delete temp file in `finally` block
  - Return `transcription.text`
- [ ] Implement `parse_request_text(text, today)`:
  - Check `AI_AVAILABLE`; raise `AIUnavailableError` if False
  - Build system prompt: instruct model to return ONLY valid JSON matching the `RideRequestParsed` schema, with today's date as context, supporting English/Hindi/Assamese input
  - Call `groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[...], temperature=0.1, max_tokens=300)`
  - Extract JSON from response (strip markdown code fences if present)
  - Validate with `RideRequestParsed.model_validate_json(json_str)`
  - On `ValidationError`: retry once with a stricter prompt that includes the error message
  - On second failure: raise `AIParseError`
- [ ] Instantiate `groq_client = Groq(api_key=GROQ_API_KEY)` only if `AI_AVAILABLE`, else set to `None`

### Relevant Context
- System prompt must include: today's date (for resolving "tomorrow", "next Monday"), the exact JSON schema shape, and language instruction
- `temperature=0.1` keeps output deterministic enough to always be valid JSON
- Never pass LLM-generated content to `eval()`, `exec()`, or any interpreter — only Pydantic parsing

### Status
[x] done

---

## Sub-Task 7 — API Routers

### Intent
Implement all five FastAPI routers. Each router wires together the services and exposes the REST API consumed by the frontend.

### Expected Outcomes
- `/api/voice/transcribe` and `/api/voice/parse` work end-to-end
- `/api/requests/` POST saves a request and triggers matching
- `/api/groups/` GET returns all groups with member counts and driver offers
- `/api/drivers/offer` POST saves a driver offer and updates group status
- `/api/geo/geocode` and `/api/geo/route` proxy external services
- `/api/seed` POST loads demo data; DELETE clears it
- All endpoints return appropriate HTTP status codes and structured error responses

### Todo List
- [ ] Write `backend/routers/voice.py`:
  - `POST /api/voice/transcribe` — accept `UploadFile`, validate MIME type starts with `audio/`, size <= 10 MB, save to `tempfile.NamedTemporaryFile`, call `transcribe_audio`, return `TranscribeResponse`; on `AIUnavailableError` return 503 with message
  - `POST /api/voice/parse` — accept `{text: str}`, call `parse_request_text`, return `ParseResponse`; handle `AIUnavailableError` (503) and `AIParseError` (422)
- [ ] Write `backend/routers/requests.py`:
  - `POST /api/requests/` — accept `RideRequestCreate`, geocode origin+destination if coords not provided, create `RideRequest` row, call `assign_to_group`, return `RideRequestOut` with group summary
  - `GET /api/requests/` — return list of all requests (newest first, limit 100)
  - `GET /api/requests/{id}` — return single request with group info
- [ ] Write `backend/routers/groups.py`:
  - `GET /api/groups/` — return all active groups with member list and driver offer if any
  - `GET /api/groups/{id}` — group detail with full member list and route info
- [ ] Write `backend/routers/drivers.py`:
  - `POST /api/drivers/offer` — accept `DriverOfferCreate`, validate group exists and has capacity, save offer, update group status to "confirmed" if offer covers all passengers, return `DriverOfferOut`
  - `GET /api/drivers/offers` — return all offers
- [ ] Write `backend/routers/geo.py`:
  - `GET /api/geo/geocode?q=` — proxy to `geo_service.geocode`, return `{lat, lon, display_name}` or 404
  - `GET /api/geo/route?olat=&olon=&dlat=&dlon=` — proxy to `geo_service.get_route`
- [ ] Write `backend/routers/seed.py`:
  - `POST /api/seed` — if no demo data exists, insert seed records; return summary
  - `DELETE /api/seed` — delete all rows where `is_demo=True` from `ride_requests`, `ride_groups`, `driver_offers`
- [ ] Register all routers in `backend/main.py` with prefix `/api`

### Relevant Context
- All routers use `db: Session = Depends(get_db)` for the database session
- Error responses should always be `{"detail": "human-readable message"}` to match FastAPI's default shape
- The seed router does NOT require Groq — it inserts hardcoded Python dicts directly

### Status
[x] done

---

## Sub-Task 8 — Demo Seed Data

### Intent
Create realistic Assam-style demo data that makes the platform look alive on first open, without depending on geocoding or external services. Every demo record has hardcoded coordinates.

### Expected Outcomes
- `backend/seed.py` contains a `seed_demo_data(db)` function
- Calling `POST /api/seed` inserts 10 ride requests, 3 ride groups, and 1 driver offer
- All seed locations have hardcoded `lat/lon` values so the map shows pins immediately
- Seed data is clearly labelled with `is_demo=True`
- Running seed twice does not create duplicates (check if demo data already exists)

### Todo List
- [ ] Define a list of 8–10 realistic Assam locations with hardcoded coordinates: Gerua village, Rangia town, Nalbari, Barpeta Road, Kamrup, Guwahati Railway Station, Jalukbari, Mirza — all real places in Kamrup/Barpeta districts
- [ ] Define seed ride requests with varied names, times, passenger counts, and languages (mix of English and Hindi notes)
- [ ] Define 3 seed groups: "Rangia Morning Group", "Nalbari Market Group", "Guwahati Station Group"
- [ ] Define 1 seed driver offer on the Rangia Morning Group
- [ ] The `seed_demo_data(db)` function checks `db.query(RideRequest).filter_by(is_demo=True).first()` and returns early if demo data already exists

### Relevant Context
- Real coordinates for Assam locations: Rangia approx (26.47°N, 91.62°E), Nalbari (26.44°N, 91.44°E), Guwahati (26.19°N, 91.74°E), Barpeta Road (26.50°N, 91.00°E)
- Use plausible Assamese names: Priya Devi, Ranjit Das, Mohan Boro, Anita Kalita, Subhash Nath, etc.
- travel_dates in seed data should be set to `date.today() + timedelta(days=1)` so they are always "tomorrow"

### Status
[x] done

---

## Sub-Task 9 — Frontend HTML Pages

### Intent
Build the three HTML pages that form the complete user interface: landing page, passenger dashboard, and driver dashboard. Pages use semantic HTML, link to the shared stylesheet and page-specific JS files.

### Expected Outcomes
- `frontend/index.html` — landing page with hero, two CTA buttons, how-it-works section
- `frontend/passenger.html` — passenger dashboard with new request form, voice input UI, AI result card, and group suggestion display
- `frontend/driver.html` — driver dashboard with demand group cards and offer form modal

### Todo List
- [x] Write `frontend/index.html`:
  - Full-page hero with tagline ("Smart rides. Shared journeys."), two large CTAs: "I'm a Passenger" → `passenger.html` and "I'm a Driver" → `driver.html`
  - How-it-works section: 3 steps with icons (Request, Match, Ride)
  - Footer with OpenStreetMap attribution
- [x] Write `frontend/passenger.html`:
  - Header with back link to index
  - Two-tab interface: "Text Request" and "Voice Request"
  - Text tab: form fields for name, phone, origin, destination, date, time, passenger count, notes — with a Submit button
  - Voice tab: large mic button, recording status indicator, waveform animation (CSS), transcription display area, "Use this text" button
  - AI result card: shown after parsing, displays extracted fields with an AI badge/indicator, and Confirm/Edit buttons
  - Group suggestion card: shown after confirmation, displays group name, date, departure time, passenger count, map placeholder
  - Leaflet map section for showing origin and destination pins
  - Loading overlays for voice processing and AI parsing
- [x] Write `frontend/driver.html`:
  - Header with title "Driver Dashboard"
  - Stats bar: total demand groups, total passengers waiting, groups with offers
  - Grid of demand group cards — each card shows: group name, destination, date, time range, passenger count, route distance, "Offer a Ride" button
  - Offer modal (hidden by default): group name display, vehicle type select, available seats input, proposed departure time, driver name, driver phone, Submit Offer button
  - Leaflet map section showing all group destination pins
  - Empty state when no groups exist
  - "Load Demo Data" button that calls `POST /api/seed`

### Relevant Context
- All pages link to `static/css/style.css` and their respective JS file
- Leaflet is loaded from CDN: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`
- No build step — all JS is vanilla `<script>` tags
- Pages must include `<meta name="viewport" content="width=device-width, initial-scale=1">` for mobile

### Status
[x] done

---

## Sub-Task 10 — CSS Styling ✅

### Intent
Create a cohesive, modern visual design appropriate for a hackathon demo. The style should evoke rural India — warm earthy tones, clear typography, mobile-first layout.

### Expected Outcomes
- `frontend/static/css/style.css` styles all three pages
- The interface looks like a real product, not a classroom form
- Works correctly on mobile screens (375px+) and desktop
- Includes styles for: AI badge, loading spinner, recording animation, empty states, success/error messages, demand cards, offer modal

### Todo List
- [ ] Define CSS custom properties (variables): primary color (warm amber/saffron `#E8720C`), secondary (forest green `#2D6A4F`), background (off-white `#FDF6EC`), card background (white), text dark/medium/light, border radius, shadow
- [ ] Reset and base styles: box-sizing border-box, system font stack, smooth scroll
- [ ] Layout utilities: `.container`, `.grid-2`, `.grid-3`, flex helpers
- [ ] Header and navigation styles
- [ ] Hero section with gradient background
- [ ] Button styles: primary (saffron), secondary (outline), danger (red), disabled state
- [ ] Form styles: input, select, textarea — clean borders, focus states
- [ ] Card component: white background, shadow, border-radius — used for group cards and request cards
- [ ] AI badge: small pill with sparkle icon, distinct color (purple/indigo) to visually mark AI-interpreted content
- [ ] Recording indicator: pulsing red dot animation
- [ ] Mic button: large circular button with mic icon, active/inactive states
- [ ] Loading spinner overlay: semi-transparent backdrop with spinning indicator
- [ ] Empty state: centered illustration placeholder + message
- [ ] Status badges: pending (yellow), grouped (blue), confirmed (green)
- [ ] Alert/toast component for success and error messages
- [ ] Demand card layout: icon-led rows for destination, passengers, time, distance
- [ ] Modal overlay and dialog styles
- [ ] Responsive breakpoints at 768px and 480px

### Relevant Context
- Use CSS Grid and Flexbox; no CSS framework (Bootstrap/Tailwind not permitted)
- Icons: use Unicode emoji or simple SVG inline — no icon library dependency
- Color palette should evoke Assam: saffron, forest green, terracotta, warm white

### Status
[x] done

---

## Sub-Task 11 — JavaScript Modules

### Intent
Implement all client-side JavaScript: shared utilities, passenger flow (text + voice), driver dashboard, and Leaflet map integration. All JS is vanilla — no framework, no bundler.

### Expected Outcomes
- `frontend/static/js/app.js` — shared fetch wrapper, toast/alert system, loading overlay toggle, date formatting helpers
- `frontend/static/js/voice.js` — MediaRecorder setup, recording lifecycle, audio blob creation, transcription and parse API calls
- `frontend/static/js/passenger.js` — text form submission, AI result display, confirmation flow, group suggestion display
- `frontend/static/js/driver.js` — load and render group cards, offer modal logic, seed data button
- `frontend/static/js/map.js` — Leaflet map initialization, add/remove markers, route line drawing

### Todo List
- [x] Write `frontend/static/js/app.js`:
  - `apiFetch(path, options)` — wraps `fetch('/api' + path)`, throws on non-2xx with parsed error message
  - `showToast(message, type)` — appends a toast div, auto-removes after 4 seconds
  - `showLoading(message)` / `hideLoading()` — show/hide the loading overlay
  - `formatDate(dateStr)`, `formatTime(timeStr)` — human-friendly display helpers
  - `API_BASE = ''` (same origin)
- [x] Write `frontend/static/js/voice.js`:
  - Check `navigator.mediaDevices` support; hide voice tab if unsupported
  - `startRecording()` — request mic permission, create `MediaRecorder`, collect chunks
  - `stopRecording()` — stop recorder, create Blob, call `uploadAudio(blob)`
  - `uploadAudio(blob)` — POST to `/api/voice/transcribe` as `multipart/form-data`, show loading, display transcription text
  - `parseTranscription(text)` — POST to `/api/voice/parse`, show loading, call `showAIResult(parsed)`
  - `showAIResult(parsed)` — populate and show the AI result card with AI badge
  - Handle `AIUnavailableError` 503 response by showing the Groq key missing message
- [x] Write `frontend/static/js/passenger.js`:
  - Text form: collect fields, POST to `/api/requests/`, show group suggestion card
  - AI confirm button: take pre-filled values from AI result card, POST to `/api/requests/`
  - `renderGroupSuggestion(group)` — populate group card with name, date, departure, passenger count
  - Load existing groups for the passenger's date on page load (call `GET /api/groups/`)
  - Tab switching between Text and Voice tabs
- [x] Write `frontend/static/js/driver.js`:
  - On page load: `GET /api/groups/`, render demand cards
  - `renderGroupCard(group)` — create card DOM element with all fields, "Offer a Ride" button
  - Offer modal: open with group pre-filled, `POST /api/drivers/offer`, close modal, refresh cards
  - "Load Demo Data" button: `POST /api/seed`, reload cards
  - Stats bar update function
- [x] Write `frontend/static/js/map.js`:
  - `initMap(elementId, center, zoom)` — initialize Leaflet map with OSM tiles and attribution
  - `addMarker(map, lat, lon, label, color)` — add named marker
  - `drawRouteLine(map, points)` — draw a polyline between coordinate array
  - `fitMarkers(map, markers)` — fit map bounds to show all markers
  - Export functions for use by passenger.js and driver.js

### Relevant Context
- All Groq API calls go through FastAPI — no direct Groq calls from JS
- The AI result card must show an AI badge and allow the user to edit fields before confirming
- `MediaRecorder` produces `audio/webm` in Chrome/Firefox; send as-is to backend since Groq Whisper accepts it
- If `AI_AVAILABLE` is false (from `/api/health`), the voice tab should show the "add GROQ_API_KEY" message instead of the mic button

### Status
[x] done

---

## Sub-Task 12 — Tests

### Intent
Write tests covering the matching algorithm, geo calculations, schema validation, API endpoints, and missing-API-key behaviour. Tests must run with `pytest` and require no external services.

### Expected Outcomes
- All tests in `tests/` pass with `pytest`
- No test makes real HTTP calls to Nominatim, OSRM, or Groq
- Missing `GROQ_API_KEY` behaviour is explicitly tested
- The matching algorithm is tested with known inputs and expected scores

### Todo List
- [ ] Write `tests/test_matching.py`:
  - Test `score_compatibility` with identical destinations → score near 1.0
  - Test with destinations 3 km apart → destination score > 0
  - Test with time difference exactly at tolerance → time score = 0
  - Test with time difference over tolerance → time score = 0
  - Test `assign_to_group` with in-memory SQLite and two compatible requests → both end up in same group
  - Test `assign_to_group` with incompatible requests → separate groups created
- [ ] Write `tests/test_geo.py`:
  - Test `haversine` with known coordinates (Rangia to Nalbari ≈ 20 km)
  - Test `get_route` when OSRM call fails → returns Haversine result with `routing_method: "haversine"` (mock httpx)
  - Test `geocode` returns cached result without calling Nominatim (mock httpx, pre-populate cache)
- [ ] Write `tests/test_schemas.py`:
  - Test `RideRequestParsed` rejects past dates
  - Test `RideRequestParsed` rejects `passenger_count = 0`
  - Test `RideRequestParsed` accepts valid JSON from a sample LLM response string
  - Test that a malformed JSON string raises `ValidationError`
- [ ] Write `tests/test_api.py`:
  - Use FastAPI `TestClient` with an in-memory SQLite database
  - Test `GET /api/health` returns `ai_available: false` when key is missing
  - Test `POST /api/requests/` with valid data returns 200 and a group
  - Test `POST /api/voice/transcribe` without Groq key returns 503 with correct message
  - Test `POST /api/seed` then `GET /api/groups/` returns non-empty list
  - Test `DELETE /api/seed` clears demo data
- [ ] Add `tests/conftest.py` with a `test_db` fixture that creates an in-memory SQLite database and overrides the `get_db` dependency

### Relevant Context
- Use `pytest-anyio` for any async tests; use `anyio_mode = "asyncio"` in `conftest.py`
- Override `get_db` in tests by using `app.dependency_overrides[get_db] = lambda: test_db`
- Mock external HTTP with `httpx`'s built-in transport mock or `unittest.mock.patch`

### Status
[x] done

---

## Sub-Task 13 — README and Final Polish

### Intent
Write the README so any person can clone the repo, install dependencies, add their Groq key, and have the application running in under 5 minutes. Also add any final touches — favicon, meta tags, page titles, 404 handling.

### Expected Outcomes
- `README.md` fully explains setup, usage, architecture, and demo instructions
- `.env.example` is correct
- All HTML pages have correct `<title>` tags and a favicon reference
- FastAPI returns a clean JSON 404 for unknown `/api/` routes
- The application is fully runnable from a cold clone with only `GROQ_API_KEY`

### Todo List
- [ ] Write `README.md` with: project description, prerequisites (Python 3.11+), installation steps, `.env` setup, startup command, usage walkthrough (passenger + driver), architecture overview, demo data instructions, running tests, technology credits
- [ ] Add a simple favicon: a small SVG of a vehicle or map pin, saved to `frontend/static/favicon.svg`, linked from all HTML pages
- [ ] Add a 404 handler in `backend/main.py` for unmatched `/api/` routes
- [ ] Verify all imports are correct across all files
- [ ] Add `__all__` exports where needed for clarity
- [ ] Final review: confirm `.env` is in `.gitignore`, confirm no API key appears in any JS or HTML file

### Relevant Context
- README should include a section explaining what happens when `GROQ_API_KEY` is missing (degraded mode)
- Include the exact `curl` or browser steps to test the health endpoint
- Note the demo seed button on the driver dashboard as the fastest way to see the app working

### Status
[x] done

---

## Implementation Order Summary

```
Sub-task 1  → scaffold + config
Sub-task 2  → DB models
Sub-task 3  → Pydantic schemas
Sub-task 4  → geo service
Sub-task 5  → matching service
Sub-task 6  → Groq service
Sub-task 7  → API routers
Sub-task 8  → seed data
Sub-task 9  → HTML pages
Sub-task 10 → CSS
Sub-task 11 → JavaScript
Sub-task 12 → tests
Sub-task 13 → README + polish
```

Each sub-task can be handed to Agent mode as a focused, self-contained unit. After each sub-task, verify it does not break the previous ones before proceeding.

---

## Implementation Complete

All 13 sub-tasks have been implemented. The project is fully runnable:

1. `pip install -r requirements.txt`
2. `cp .env.example .env` (add GROQ_API_KEY)
3. `python run.py`
4. Open http://localhost:8000

Run tests: `python -m pytest tests/ -v`
