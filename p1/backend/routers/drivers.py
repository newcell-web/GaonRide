"""Drivers router: driver offer submission and listing."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import DriverOffer, RideGroup
from backend.schemas import DriverOfferCreate, DriverOfferOut

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("/offer", response_model=DriverOfferOut, status_code=201)
def create_offer(
    offer_data: DriverOfferCreate,
    db: Session = Depends(get_db),
) -> DriverOfferOut:
    """Submit a driver offer for a ride group."""
    group = db.query(RideGroup).filter(RideGroup.id == offer_data.group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    offer = DriverOffer(
        group_id=offer_data.group_id,
        driver_name=offer_data.driver_name,
        driver_phone=offer_data.driver_phone,
        vehicle_type=offer_data.vehicle_type,
        available_seats=offer_data.available_seats,
        proposed_departure=offer_data.proposed_departure,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    if offer.available_seats >= group.total_passengers:
        group.status = "confirmed"
        db.commit()

    return DriverOfferOut.model_validate(offer)


@router.get("/offers", response_model=list[DriverOfferOut])
def list_offers(db: Session = Depends(get_db)) -> list[DriverOfferOut]:
    """Return all driver offers, newest first."""
    rows = (
        db.query(DriverOffer)
        .order_by(DriverOffer.created_at.desc())
        .all()
    )
    return [DriverOfferOut.model_validate(r) for r in rows]
