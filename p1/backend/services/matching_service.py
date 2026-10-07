"""Deterministic ride-grouping algorithm."""

from datetime import datetime, time, timedelta, date
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.models import RideRequest, RideGroup
from backend.config import TIME_TOLERANCE_MIN, DEST_MATCH_KM, ORIGIN_RADIUS_KM, GROUP_SCORE_THRESHOLD
from backend.services.geo_service import haversine


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _from_minutes(mins: int) -> time:
    h, m = divmod(int(mins), 60)
    return time(h % 24, m)


def _request_to_dict(r: RideRequest) -> dict:
    return {
        "dest_lat": r.dest_lat,
        "dest_lon": r.dest_lon,
        "dest_text": r.destination_text,
        "origin_lat": r.origin_lat,
        "origin_lon": r.origin_lon,
        "travel_date": r.travel_date,
        "preferred_time": r.preferred_time,
        "passenger_count": r.passenger_count,
    }


# ---------------------------------------------------------------------------
# Public: pure scoring function
# ---------------------------------------------------------------------------

def score_compatibility(r1: dict, r2: dict) -> float:
    """Return a compatibility score 0.0–1.0 between two ride-request dicts.

    Keys required: dest_lat, dest_lon, dest_text, origin_lat, origin_lon,
                   travel_date, preferred_time (datetime.time), passenger_count.
    """
    # --- Destination score (weight 0.50) ---
    if r1["dest_text"].lower().strip() == r2["dest_text"].lower().strip():
        destination_score = 1.0
    elif (
        r1["dest_lat"] is not None and r1["dest_lon"] is not None
        and r2["dest_lat"] is not None and r2["dest_lon"] is not None
    ):
        destination_score = max(
            0.0,
            1.0 - haversine(r1["dest_lat"], r1["dest_lon"], r2["dest_lat"], r2["dest_lon"]) / DEST_MATCH_KM,
        )
    else:
        destination_score = 0.0

    # --- Time score (weight 0.30) ---
    t1_min = _to_minutes(r1["preferred_time"])
    t2_min = _to_minutes(r2["preferred_time"])
    delta_minutes = abs(t1_min - t2_min)
    time_score = max(0.0, 1.0 - delta_minutes / TIME_TOLERANCE_MIN)

    # --- Origin score (weight 0.20) ---
    if (
        r1["origin_lat"] is not None and r1["origin_lon"] is not None
        and r2["origin_lat"] is not None and r2["origin_lon"] is not None
    ):
        dist = haversine(r1["origin_lat"], r1["origin_lon"], r2["origin_lat"], r2["origin_lon"])
        if dist <= ORIGIN_RADIUS_KM:
            origin_score = 1.0
        elif dist <= ORIGIN_RADIUS_KM * 2:
            origin_score = 0.5
        else:
            origin_score = 0.0
    else:
        origin_score = 0.5  # neutral when coords unavailable

    return destination_score * 0.50 + time_score * 0.30 + origin_score * 0.20


# ---------------------------------------------------------------------------
# Public: group assignment
# ---------------------------------------------------------------------------

def assign_to_group(request: RideRequest, db: Session) -> RideGroup:
    """Find the best existing group for *request* or create a new one.

    Updates request.group_id, request.status, and the group's aggregate
    fields, then commits.  Returns the assigned RideGroup.
    """
    req_min = _to_minutes(request.preferred_time)

    # 1. Fetch candidates: same date, not confirmed, not this request
    candidates = (
        db.query(RideRequest)
        .filter(
            RideRequest.status != "confirmed",
            RideRequest.travel_date == request.travel_date,
            RideRequest.id != request.id,
        )
        .all()
    )

    # 2. Filter by time window in Python
    candidates = [
        c for c in candidates
        if abs(_to_minutes(c.preferred_time) - req_min) <= TIME_TOLERANCE_MIN
    ]

    # 3. Group candidates by group_id (ignore ungrouped)
    groups_map: dict[int, list[RideRequest]] = defaultdict(list)
    for c in candidates:
        if c.group_id is not None:
            groups_map[c.group_id].append(c)

    # 4. Score each existing group
    req_dict = _request_to_dict(request)
    best_group_id: int | None = None
    best_score: float = -1.0

    for gid, members in groups_map.items():
        avg_score = sum(score_compatibility(req_dict, _request_to_dict(m)) for m in members) / len(members)
        if avg_score > best_score:
            best_score = avg_score
            best_group_id = gid

    # 5. Assign or create group
    if best_score >= GROUP_SCORE_THRESHOLD and best_group_id is not None:
        group = db.query(RideGroup).filter(RideGroup.id == best_group_id).one()
    else:
        group = RideGroup(
            destination_text=request.destination_text,
            dest_lat=request.dest_lat,
            dest_lon=request.dest_lon,
            travel_date=request.travel_date,
            is_demo=request.is_demo,
        )
        db.add(group)
        db.flush()  # populate group.id before assigning

    # 6. Link request to group
    request.group_id = group.id
    request.status = "grouped"

    # 7. Recalculate group aggregates across all members (including new request).
    # Query existing members already committed to this group, then append the
    # current request (not yet committed) so len(members) is always >= 1.
    existing = db.query(RideRequest).filter(
        RideRequest.group_id == group.id,
        RideRequest.id != request.id,
    ).all()
    members = existing + [request]

    group.total_passengers = sum(m.passenger_count for m in members)

    avg_min = sum(_to_minutes(m.preferred_time) for m in members) / len(members)
    group.suggested_departure = _from_minutes(avg_min)

    db.commit()
    db.refresh(request)
    db.refresh(group)

    return group
