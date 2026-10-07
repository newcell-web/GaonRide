from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class RideGroup(Base):
    __tablename__ = "ride_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    destination_text = Column(String, nullable=False)
    dest_lat = Column(Float, nullable=True)
    dest_lon = Column(Float, nullable=True)
    travel_date = Column(Date, nullable=False)
    suggested_departure = Column(Time, nullable=True)
    total_passengers = Column(Integer, default=0)
    status = Column(String, default="active")  # active / confirmed / completed
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    requests = relationship("RideRequest", back_populates="group")
    driver_offers = relationship("DriverOffer", back_populates="group")


class RideRequest(Base):
    __tablename__ = "ride_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_name = Column(String, nullable=False)
    passenger_phone = Column(String, nullable=True)
    origin_text = Column(String, nullable=False)
    destination_text = Column(String, nullable=False)
    origin_lat = Column(Float, nullable=True)
    origin_lon = Column(Float, nullable=True)
    dest_lat = Column(Float, nullable=True)
    dest_lon = Column(Float, nullable=True)
    travel_date = Column(Date, nullable=False)
    preferred_time = Column(Time, nullable=False)
    passenger_count = Column(Integer, default=1)
    language = Column(String, default="en")
    notes = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending / grouped / confirmed
    group_id = Column(Integer, ForeignKey("ride_groups.id"), nullable=True)
    is_demo = Column(Boolean, default=False)
    ai_parsed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("RideGroup", back_populates="requests")


class DriverOffer(Base):
    __tablename__ = "driver_offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("ride_groups.id"), nullable=False)
    driver_name = Column(String, nullable=False)
    driver_phone = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)
    available_seats = Column(Integer, nullable=False)
    proposed_departure = Column(Time, nullable=False)
    status = Column(String, default="pending")  # pending / confirmed
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("RideGroup", back_populates="driver_offers")


class GeocodeCache(Base):
    __tablename__ = "geocode_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(String, unique=True, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    display_name = Column(String, nullable=True)
    cached_at = Column(DateTime, default=datetime.utcnow)
