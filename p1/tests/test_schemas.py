import pytest
import datetime
from pydantic import ValidationError
from backend.schemas import RideRequestParsed, DriverOfferCreate


def test_valid_ride_request_parsed():
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    data = {
        "origin": "Gerua Village",
        "destination": "Rangia",
        "travel_date": tomorrow,
        "preferred_time": "09:00",
        "passenger_count": 2,
        "language": "en"
    }
    parsed = RideRequestParsed(**data)
    assert parsed.origin == "Gerua Village"
    assert parsed.passenger_count == 2


def test_past_date_rejected():
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError) as exc_info:
        RideRequestParsed(
            origin="A", destination="B",
            travel_date=yesterday,
            preferred_time="09:00"
        )
    assert "past" in str(exc_info.value).lower() or "future" in str(exc_info.value).lower() or "today" in str(exc_info.value).lower()


def test_passenger_count_zero_rejected():
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        RideRequestParsed(
            origin="A", destination="B",
            travel_date=tomorrow,
            preferred_time="09:00",
            passenger_count=0
        )


def test_passenger_count_over_limit_rejected():
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        RideRequestParsed(
            origin="A", destination="B",
            travel_date=tomorrow,
            preferred_time="09:00",
            passenger_count=21
        )


def test_preferred_time_string_coercion():
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    parsed = RideRequestParsed(
        origin="A", destination="B",
        travel_date=tomorrow,
        preferred_time="09:00"
    )
    assert isinstance(parsed.preferred_time, datetime.time)
    assert parsed.preferred_time.hour == 9


def test_today_date_accepted():
    # travel_date = today should be accepted (not in the past)
    today = datetime.date.today().isoformat()
    parsed = RideRequestParsed(
        origin="A", destination="B",
        travel_date=today,
        preferred_time="09:00"
    )
    assert parsed.travel_date == datetime.date.today()


def test_driver_offer_seats_validation():
    with pytest.raises(ValidationError):
        DriverOfferCreate(
            group_id=1, driver_name="Test", driver_phone="1234567890",
            vehicle_type="Auto", available_seats=0,
            proposed_departure="08:00"
        )
