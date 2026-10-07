"""Seed router: load and clear demo data."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import DriverOffer, RideGroup, RideRequest

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("/")
def seed(db: Session = Depends(get_db)) -> dict:
    """Load demo data into the database."""
    try:
        from backend.seed import seed_demo_data  # noqa: PLC0415
        seed_demo_data(db)
        return {"message": "Demo data loaded successfully"}
    except ImportError:
        return {"message": "Seed module not yet available"}


@router.delete("/")
def clear_seed(db: Session = Depends(get_db)) -> dict:
    """Remove all demo data from the database."""
    db.query(DriverOffer).delete()
    db.query(RideRequest).filter(RideRequest.is_demo == True).delete()  # noqa: E712
    db.query(RideGroup).filter(RideGroup.is_demo == True).delete()  # noqa: E712
    db.commit()
    return {"message": "Demo data cleared"}
