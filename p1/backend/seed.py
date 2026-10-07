from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from backend.models import DriverOffer, RideGroup, RideRequest

# ---------------------------------------------------------------------------
# Hardcoded Assam locations  (Kamrup / Barpeta districts)
# ---------------------------------------------------------------------------
LOCATIONS = {
    "Gerua Village":              (26.31, 91.52),
    "Rangia Town":                (26.47, 91.62),
    "Nalbari Town":               (26.44, 91.44),
    "Barpeta Road":               (26.50, 91.00),
    "Guwahati Railway Station":   (26.18, 91.74),
    "Jalukbari":                  (26.17, 91.67),
    "Mirza":                      (26.24, 91.48),
    "Kamrup":                     (26.33, 91.57),
    "Hajo":                       (26.24, 91.52),
    "Changsari":                  (26.39, 91.64),
}


def seed_demo_data(db: Session) -> None:
    """Insert realistic Assam-style demo data.

    Safe to call multiple times — exits early if demo data already exists.
    """
    if db.query(RideRequest).filter_by(is_demo=True).first():
        return  # Already seeded, do nothing

    tomorrow = date.today() + timedelta(days=1)

    # ------------------------------------------------------------------
    # 1. Ride Groups
    # ------------------------------------------------------------------
    group_rangia = RideGroup(
        destination_text="Rangia Town",
        dest_lat=26.47,
        dest_lon=91.62,
        travel_date=tomorrow,
        suggested_departure=time(8, 45),
        total_passengers=4,
        status="active",
        is_demo=True,
    )
    group_nalbari = RideGroup(
        destination_text="Nalbari Town",
        dest_lat=26.44,
        dest_lon=91.44,
        travel_date=tomorrow,
        suggested_departure=time(10, 0),
        total_passengers=3,
        status="active",
        is_demo=True,
    )
    group_gwh = RideGroup(
        destination_text="Guwahati Railway Station",
        dest_lat=26.18,
        dest_lon=91.74,
        travel_date=tomorrow,
        suggested_departure=time(7, 30),
        total_passengers=5,
        status="active",
        is_demo=True,
    )
    db.add_all([group_rangia, group_nalbari, group_gwh])
    db.flush()  # populate .id before building requests

    # ------------------------------------------------------------------
    # 2. Ride Requests
    # ------------------------------------------------------------------
    def loc(name):
        return LOCATIONS[name]

    requests_data = [
        # name, phone, origin, dest, hh, mm, pax, lang, group, notes, ai_parsed
        ("Priya Devi",      "9876543210", "Gerua Village",            "Rangia Town",              9,  0,  2, "en", group_rangia,  "Going to weekly market with mother",           True),
        ("Ranjit Das",      "9765432109", "Kamrup",                   "Rangia Town",              8, 30,  1, "en", group_rangia,  "Office work",                                   True),
        ("Mohan Boro",      "9654321098", "Changsari",                "Nalbari Town",            10,  0,  1, "as", group_nalbari, "Bank work / bank kaaj",                         True),
        ("Anita Kalita",    "9543210987", "Gerua Village",            "Nalbari Town",             9, 30,  2, "en", group_nalbari, "Hospital appointment",                          True),
        ("Subhash Nath",    "9432109876", "Mirza",                    "Guwahati Railway Station", 7,  0,  1, "en", group_gwh,     "Catching morning train",                        True),
        ("Rekha Baruah",    "9321098765", "Hajo",                     "Guwahati Railway Station", 7, 30,  3, "hi", group_gwh,     "Family trip to Guwahati",                       False),
        ("Dipak Sarma",     "9210987654", "Jalukbari",                "Guwahati Railway Station", 8,  0,  1, "en", group_gwh,     "College",                                       False),
        ("Mamoni Das",      "9109876543", "Kamrup",                   "Rangia Town",              9,  0,  1, "en", group_rangia,  "Vegetable market",                              False),
        ("Binod Koch",      "9098765432", "Mirza",                    "Nalbari Town",            10, 30,  1, "en", None,          "Government office work (ungrouped)",            False),
        ("Sanjay Talukdar", "9087654321", "Gerua Village",            "Barpeta Road",            11,  0,  2, "en", None,          "Medical college",                               False),
    ]

    for name, phone, origin, dest, hh, mm, pax, lang, group, notes, ai_parsed in requests_data:
        olat, olon = loc(origin)
        dlat, dlon = loc(dest)
        status = "grouped" if group is not None else "pending"
        rr = RideRequest(
            passenger_name=name,
            passenger_phone=phone,
            origin_text=origin,
            destination_text=dest,
            origin_lat=olat,
            origin_lon=olon,
            dest_lat=dlat,
            dest_lon=dlon,
            travel_date=tomorrow,
            preferred_time=time(hh, mm),
            passenger_count=pax,
            language=lang,
            notes=notes,
            status=status,
            group_id=group.id if group is not None else None,
            ai_parsed=ai_parsed,
            is_demo=True,
        )
        db.add(rr)

    # ------------------------------------------------------------------
    # 3. Driver Offer  (Rangia Morning Group)
    # ------------------------------------------------------------------
    offer = DriverOffer(
        group_id=group_rangia.id,
        driver_name="Karim Ali",
        driver_phone="9876501234",
        vehicle_type="Auto-Rickshaw",
        available_seats=6,
        proposed_departure=time(8, 45),
        status="confirmed",
    )
    db.add(offer)
    group_rangia.status = "confirmed"

    db.commit()
