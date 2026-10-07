from __future__ import annotations

import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIME_FORMATS = ["%H:%M", "%I:%M %p", "%I %p"]


def _coerce_time(v: object) -> datetime.time:
    """Accept a datetime.time or a string such as '09:00', '9 AM', '9:00 AM'."""
    if isinstance(v, datetime.time):
        return v
    if isinstance(v, str):
        for fmt in _TIME_FORMATS:
            try:
                return datetime.datetime.strptime(v.strip(), fmt).time()
            except ValueError:
                continue
        raise ValueError(
            f"Cannot parse time '{v}'. Expected formats: HH:MM, HH:MM AM/PM, or H AM/PM."
        )
    raise ValueError(f"Invalid type for time field: {type(v)}")


# ---------------------------------------------------------------------------
# LLM output contract
# ---------------------------------------------------------------------------

class RideRequestParsed(BaseModel):
    origin: str
    destination: str
    travel_date: datetime.date
    preferred_time: datetime.time
    passenger_count: int = 1
    language: str = "en"
    notes: Optional[str] = None

    @field_validator("travel_date")
    @classmethod
    def travel_date_not_in_past(cls, v: datetime.date) -> datetime.date:
        if v is not None and v < datetime.date.today():
            raise ValueError(
                f"travel_date {v} is in the past. Please provide a future date."
            )
        return v

    @field_validator("passenger_count")
    @classmethod
    def passenger_count_range(cls, v: int) -> int:
        if not (1 <= v <= 20):
            raise ValueError("passenger_count must be between 1 and 20 (inclusive).")
        return v

    @field_validator("preferred_time", mode="before")
    @classmethod
    def coerce_preferred_time(cls, v: object) -> datetime.time:
        return _coerce_time(v)


# ---------------------------------------------------------------------------
# Passenger submission
# ---------------------------------------------------------------------------

class RideRequestCreate(RideRequestParsed):
    passenger_name: str
    passenger_phone: Optional[str] = None

    # Pre-geocoded coordinates — backend geocodes if these are absent
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None

    ai_parsed: bool = False


# ---------------------------------------------------------------------------
# API responses
# ---------------------------------------------------------------------------

class RideRequestOut(RideRequestCreate):
    id: int
    status: str
    group_id: Optional[int] = None
    created_at: datetime.datetime

    # Re-declare these with aliases so model_validate() can read origin_text /
    # destination_text directly off the ORM object (from_attributes mode).
    origin: str = Field(validation_alias=AliasChoices("origin", "origin_text"))
    destination: str = Field(validation_alias=AliasChoices("destination", "destination_text"))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DriverOfferOut(BaseModel):
    id: int
    group_id: int
    driver_name: str
    driver_phone: str
    vehicle_type: str
    available_seats: int
    proposed_departure: datetime.time
    status: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class RideGroupOut(BaseModel):
    id: int
    destination_text: str
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    travel_date: datetime.date
    suggested_departure: Optional[datetime.time] = None
    total_passengers: int
    status: str
    is_demo: bool
    member_count: int
    driver_offer: Optional[DriverOfferOut] = None

    model_config = ConfigDict(from_attributes=True)


# Resolve the forward reference now that DriverOfferOut is fully defined
RideGroupOut.model_rebuild()


# ---------------------------------------------------------------------------
# Driver offer submission
# ---------------------------------------------------------------------------

class DriverOfferCreate(BaseModel):
    group_id: int
    driver_name: str
    driver_phone: str
    vehicle_type: str
    available_seats: int
    proposed_departure: datetime.time

    @field_validator("available_seats")
    @classmethod
    def seats_at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("available_seats must be >= 1.")
        return v

    @field_validator("proposed_departure", mode="before")
    @classmethod
    def coerce_proposed_departure(cls, v: object) -> datetime.time:
        return _coerce_time(v)


# ---------------------------------------------------------------------------
# Voice / AI endpoints
# ---------------------------------------------------------------------------

class TranscribeResponse(BaseModel):
    text: str


class ParseResponse(BaseModel):
    parsed: RideRequestParsed
    raw_text: str
    note: Optional[str] = None  # e.g. "Interpreted from Assamese voice request"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    ai_available: bool
    db_ok: bool
    message: str
