"""Geo utilities: Haversine distance, Nominatim geocoding, OSRM routing."""

import asyncio
import math
import time

import httpx
from sqlalchemy.orm import Session

from backend.models import GeocodeCache

# ---------------------------------------------------------------------------
# Module-level rate-limiting state for Nominatim
# ---------------------------------------------------------------------------
_nominatim_lock: asyncio.Lock = asyncio.Lock()
_last_nominatim_call: float = 0.0


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres between two points."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def geocode(place_name: str, db: Session) -> tuple[float, float] | None:
    """Return (lat, lon) for *place_name*, using the DB cache when possible.

    Returns None on any failure — never raises.
    """
    global _last_nominatim_call
    try:
        key = place_name.lower().strip()

        # --- cache hit ---
        row = db.query(GeocodeCache).filter_by(query_text=key).first()
        if row is not None:
            return (row.lat, row.lon)

        # --- cache miss: call Nominatim with rate limiting ---
        async with _nominatim_lock:
            elapsed = time.monotonic() - _last_nominatim_call
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": place_name, "format": "json", "limit": 1, "addressdetails": 0},
                    headers={"User-Agent": "GaonRide-AI/1.0", "Accept-Language": "en"},
                )

            _last_nominatim_call = time.monotonic()

        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None

        hit = results[0]
        lat = float(hit["lat"])
        lon = float(hit["lon"])
        display_name: str = hit.get("display_name", "")

        db.add(GeocodeCache(query_text=key, lat=lat, lon=lon, display_name=display_name))
        db.commit()

        return (lat, lon)

    except Exception:
        return None


async def get_route(
    origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float
) -> dict:
    """Return routing info between two coordinate pairs.

    Tries OSRM first; falls back to Haversine on any failure.
    """
    try:
        url = (
            f"http://router.project-osrm.org/route/v1/driving/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        route = data["routes"][0]
        return {
            "distance_km": route["distance"] / 1000,
            "duration_min": route["duration"] / 60,
            "routing_method": "osrm",
        }
    except Exception:
        return {
            "distance_km": haversine(origin_lat, origin_lon, dest_lat, dest_lon),
            "duration_min": None,
            "routing_method": "haversine",
        }
