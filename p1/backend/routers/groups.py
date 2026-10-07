"""Groups router: ride group listing and detail."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import DriverOffer, RideGroup, RideRequest
from backend.schemas import DriverOfferOut, RideGroupOut
from backend.services.geo_service import get_route

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/", response_model=list[RideGroupOut])
def list_groups(db: Session = Depends(get_db)) -> list[RideGroupOut]:
    """Return all active/confirmed groups, newest first."""
    groups = (
        db.query(RideGroup)
        .filter(RideGroup.status != "completed")
        .order_by(RideGroup.created_at.desc())
        .all()
    )

    result: list[RideGroupOut] = []
    for group in groups:
        member_count = (
            db.query(RideRequest)
            .filter(RideRequest.group_id == group.id)
            .count()
        )
        driver_offer_row = (
            db.query(DriverOffer)
            .filter(DriverOffer.group_id == group.id)
            .first()
        )
        driver_offer = DriverOfferOut.model_validate(driver_offer_row) if driver_offer_row else None

        data = {
            "id": group.id,
            "destination_text": group.destination_text,
            "dest_lat": group.dest_lat,
            "dest_lon": group.dest_lon,
            "travel_date": group.travel_date,
            "suggested_departure": group.suggested_departure,
            "total_passengers": group.total_passengers,
            "status": group.status,
            "is_demo": group.is_demo,
            "member_count": member_count,
            "driver_offer": driver_offer,
        }
        result.append(RideGroupOut.model_validate(data))

    return result


@router.get("/{group_id}")
async def get_group(group_id: int, db: Session = Depends(get_db)) -> dict:
    """Return a group with its members and route info."""
    group = db.query(RideGroup).filter(RideGroup.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    members = (
        db.query(RideRequest)
        .filter(RideRequest.group_id == group.id)
        .all()
    )
    driver_offer_row = (
        db.query(DriverOffer)
        .filter(DriverOffer.group_id == group.id)
        .first()
    )
    driver_offer = DriverOfferOut.model_validate(driver_offer_row) if driver_offer_row else None

    route: dict | None = None
    # Use the coords of the first member that has origin coords
    origin_lat = origin_lon = None
    for m in members:
        if m.origin_lat is not None and m.origin_lon is not None:
            origin_lat, origin_lon = m.origin_lat, m.origin_lon
            break

    if (
        origin_lat is not None
        and group.dest_lat is not None
        and group.dest_lon is not None
    ):
        route = await get_route(origin_lat, origin_lon, group.dest_lat, group.dest_lon)

    from backend.schemas import RideRequestOut

    return {
        "id": group.id,
        "destination_text": group.destination_text,
        "dest_lat": group.dest_lat,
        "dest_lon": group.dest_lon,
        "travel_date": group.travel_date,
        "suggested_departure": group.suggested_departure,
        "total_passengers": group.total_passengers,
        "status": group.status,
        "is_demo": group.is_demo,
        "member_count": len(members),
        "driver_offer": driver_offer.model_dump() if driver_offer else None,
        "members": [RideRequestOut.model_validate(m).model_dump() for m in members],
        "route": route,
    }
