import datetime
from backend.services.matching_service import score_compatibility, assign_to_group
from backend.models import RideRequest, RideGroup


def make_request_dict(dest_text="Rangia", dest_lat=26.47, dest_lon=91.62,
                      origin_lat=26.31, origin_lon=91.52,
                      time_h=9, time_m=0, pax=1):
    return {
        "dest_text": dest_text,
        "dest_lat": dest_lat,
        "dest_lon": dest_lon,
        "origin_lat": origin_lat,
        "origin_lon": origin_lon,
        "preferred_time": datetime.time(time_h, time_m),
        "passenger_count": pax,
    }


def test_score_self_is_one():
    r = make_request_dict()
    assert score_compatibility(r, r) == 1.0


def test_same_destination_text_max_dest_score():
    r1 = make_request_dict(dest_text="Rangia Town")
    r2 = make_request_dict(dest_text="rangia town")  # case insensitive
    score = score_compatibility(r1, r2)
    # destination component is 0.50 weight * 1.0 = 0.50 minimum
    assert score >= 0.50


def test_destinations_far_apart_low_score():
    # Use different origins too so origin_score doesn't compensate
    r1 = make_request_dict(dest_text="Rangia", dest_lat=26.47, dest_lon=91.62,
                           origin_lat=26.31, origin_lon=91.52)
    r2 = make_request_dict(dest_text="Guwahati", dest_lat=26.18, dest_lon=91.74,
                           origin_lat=26.00, origin_lon=91.00)  # far origin -> origin_score=0
    score = score_compatibility(r1, r2)
    # dest_score≈0 (35km apart >> DEST_MATCH_KM=5), time_score=1.0, origin_score=0
    # total = 0*0.5 + 1.0*0.3 + 0*0.2 = 0.3
    assert score < 0.5


def test_time_at_tolerance_boundary():
    r1 = make_request_dict(time_h=9, time_m=0)
    r2 = make_request_dict(time_h=10, time_m=30)  # exactly 90 min apart
    score = score_compatibility(r1, r2)
    # time score should be 0 at boundary
    # total score = dest(1.0*0.5) + time(0.0*0.3) + origin(1.0*0.2) = 0.7
    assert 0.6 <= score <= 0.8


def test_time_over_tolerance_zero_time_score():
    r1 = make_request_dict(time_h=7, time_m=0)
    r2 = make_request_dict(time_h=10, time_m=0)  # 180 min > 90 min tolerance
    score = score_compatibility(r1, r2)
    # time score is 0
    assert score <= 0.75  # max is dest(0.5) + origin(0.2) = 0.7


def test_assign_to_group_groups_compatible_requests(db_session):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    # Create first request and add it to a group manually
    group = RideGroup(
        destination_text="Rangia",
        dest_lat=26.47, dest_lon=91.62,
        travel_date=tomorrow,
        status="active"
    )
    db_session.add(group)
    db_session.flush()

    r1 = RideRequest(
        passenger_name="Alice",
        origin_text="Gerua",
        destination_text="Rangia",
        origin_lat=26.31, origin_lon=91.52,
        dest_lat=26.47, dest_lon=91.62,
        travel_date=tomorrow,
        preferred_time=datetime.time(9, 0),
        passenger_count=1,
        group_id=group.id,
        status="grouped"
    )
    db_session.add(r1)
    db_session.flush()
    group.total_passengers = 1

    # Second request, compatible
    r2 = RideRequest(
        passenger_name="Bob",
        origin_text="Kamrup",
        destination_text="Rangia",
        origin_lat=26.33, origin_lon=91.57,
        dest_lat=26.47, dest_lon=91.62,
        travel_date=tomorrow,
        preferred_time=datetime.time(9, 15),
        passenger_count=1,
        status="pending"
    )
    db_session.add(r2)
    db_session.flush()

    result_group = assign_to_group(r2, db_session)

    assert r2.group_id == group.id
    assert r2.status == "grouped"
    assert result_group.total_passengers == 2


def test_assign_to_group_creates_new_group_for_incompatible(db_session):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    group = RideGroup(
        destination_text="Rangia",
        dest_lat=26.47, dest_lon=91.62,
        travel_date=tomorrow,
        status="active"
    )
    db_session.add(group)
    db_session.flush()

    r1 = RideRequest(
        passenger_name="Alice",
        origin_text="Gerua",
        destination_text="Rangia",
        dest_lat=26.47, dest_lon=91.62,
        travel_date=tomorrow,
        preferred_time=datetime.time(9, 0),
        passenger_count=1,
        group_id=group.id,
        status="grouped"
    )
    db_session.add(r1)
    db_session.flush()
    group.total_passengers = 1

    # Very different destination
    r2 = RideRequest(
        passenger_name="Carol",
        origin_text="Nalbari",
        destination_text="Barpeta Road",
        dest_lat=26.50, dest_lon=91.00,
        travel_date=tomorrow,
        preferred_time=datetime.time(9, 0),
        passenger_count=1,
        status="pending"
    )
    db_session.add(r2)
    db_session.flush()

    result_group = assign_to_group(r2, db_session)

    # Should be in a NEW group, not the Rangia group
    assert r2.group_id != group.id
    assert result_group.destination_text == "Barpeta Road"
