"""Requests router: ride request CRUD and auto-grouping."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import RideRequest
from backend.schemas import RideRequestCreate, RideRequestOut
from backend.services.geo_service import geocode
from backend.services.matching_service import assign_to_group

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("/", response_model=RideRequestOut, status_code=201)
async def create_request(
    request_data: RideRequestCreate,
    db: Session = Depends(get_db),
) -> RideRequestOut:
    """Submit a new ride request, geocode if needed, and assign to a group."""
    ride_request = RideRequest(
        passenger_name=request_data.passenger_name,
        passenger_phone=request_data.passenger_phone,
        origin_text=request_data.origin,
        destination_text=request_data.destination,
        origin_lat=request_data.origin_lat,
        origin_lon=request_data.origin_lon,
        dest_lat=request_data.dest_lat,
        dest_lon=request_data.dest_lon,
        travel_date=request_data.travel_date,
        preferred_time=request_data.preferred_time,
        passenger_count=request_data.passenger_count,
        language=request_data.language,
        notes=request_data.notes,
        ai_parsed=request_data.ai_parsed,
    )

    # Geocode origin if coords missing
    if ride_request.origin_lat is None and ride_request.origin_text:
        coords = await geocode(ride_request.origin_text, db)
        if coords is not None:
            ride_request.origin_lat, ride_request.origin_lon = coords

    # Geocode destination if coords missing
    if ride_request.dest_lat is None and ride_request.destination_text:
        coords = await geocode(ride_request.destination_text, db)
        if coords is not None:
            ride_request.dest_lat, ride_request.dest_lon = coords

    db.add(ride_request)
    db.flush()  # get ride_request.id before matching

    assign_to_group(ride_request, db)  # commits inside

    return RideRequestOut.model_validate(ride_request)


@router.get("/", response_model=list[RideRequestOut])
def list_requests(db: Session = Depends(get_db)) -> list[RideRequestOut]:
    """Return up to 100 ride requests, newest first."""
    rows = (
        db.query(RideRequest)
        .order_by(RideRequest.created_at.desc())
        .limit(100)
        .all()
    )
    return [RideRequestOut.model_validate(r) for r in rows]


@router.get("/{request_id}", response_model=RideRequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)) -> RideRequestOut:
    """Return a single ride request by ID."""
    row = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return RideRequestOut.model_validate(row)
