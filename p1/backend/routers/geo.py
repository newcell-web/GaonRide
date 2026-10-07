"""Geo router: geocoding and routing endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.geo_service import geocode, get_route

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/geocode")
async def geocode_place(q: str, db: Session = Depends(get_db)) -> dict:
    """Geocode a place name and return its coordinates."""
    result = await geocode(q, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Location not found")
    lat, lon = result
    return {"lat": lat, "lon": lon}


@router.get("/route")
async def route(olat: float, olon: float, dlat: float, dlon: float) -> dict:
    """Return driving distance and duration between two coordinate pairs."""
    return await get_route(olat, olon, dlat, dlon)
