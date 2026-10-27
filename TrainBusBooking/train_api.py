"""
SmartTravel - Local Train Schedules Service (Demo Only)
Provides train schedules and timetable status using the local SQLite database.
NO external real-time APIs (No RailKit, No IRCTC). Pure offline demo data.
"""

import os
from datetime import datetime
from database import get_db_connection

# Standard Railway Station Code Map (Offline Reference)
STATION_CODE_MAP = {
    "bengaluru": "SBC",
    "bangalore": "SBC",
    "chennai": "MAS",
    "madras": "MAS",
    "delhi": "NDLS",
    "new delhi": "NDLS",
    "mumbai": "CSTM",
    "bombay": "CSTM",
    "pune": "PUNE",
    "hyderabad": "SC",
    "secunderabad": "SC",
    "kolkata": "HWH",
    "howrah": "HWH",
    "jaipur": "JP",
    "coimbatore": "CBE",
    "ahmedabad": "ADI",
    "mysuru": "MYS",
    "mysore": "MYS",
    "goa": "MAO",
    "madgaon": "MAO",
    "kochi": "ERS",
    "ernakulam": "ERS",
    "thiruvananthapuram": "TVC",
    "trivandrum": "TVC",
}


def get_station_code(city_or_station_name: str) -> str:
    """Returns the Indian Railways 3-4 letter station code for known cities."""
    if not city_or_station_name:
        return "SBC"
    clean = city_or_station_name.strip().lower()
    for key, code in STATION_CODE_MAP.items():
        if key in clean or clean in key:
            return code
    return clean[:4].upper()


def _get_train_classes(base_price: float, train_name: str, train_no: str):
    """Calculates realistic class options for a train."""
    price = float(base_price or 600)
    name = (train_name or "").lower()
    no = str(train_no or "")

    # Train #20608 (Vande Bharat Express) strictly supports only CC and EC
    if no == "20608" or "vande bharat" in name:
        return [
            {"code": "CC", "name": "AC Chair Car", "price": int(price), "seats": 52, "status": "AVAILABLE", "is_ac": 1},
            {"code": "EC", "name": "Executive Class", "price": int(price * 1.85), "seats": 14, "status": "AVAILABLE", "is_ac": 1},
        ]

    if "shatabdi" in name:
        return [
            {"code": "CC", "name": "AC Chair Car", "price": int(price), "seats": 44, "status": "AVAILABLE", "is_ac": 1},
            {"code": "EC", "name": "Executive Chair Car", "price": int(price * 1.8), "seats": 12, "status": "AVAILABLE", "is_ac": 1},
        ]

    if "rajdhani" in name or "duronto" in name:
        return [
            {"code": "1A", "name": "AC First Class", "price": int(price * 1.7), "seats": 8, "status": "AVAILABLE", "is_ac": 1},
            {"code": "2A", "name": "AC 2 Tier", "price": int(price * 1.25), "seats": 18, "status": "AVAILABLE", "is_ac": 1},
            {"code": "3A", "name": "AC 3 Tier", "price": int(price), "seats": 32, "status": "AVAILABLE", "is_ac": 1},
        ]

    # Standard Superfast / Express
    return [
        {"code": "1A", "name": "AC First Class", "price": int(price * 2.2), "seats": 10, "status": "AVAILABLE", "is_ac": 1},
        {"code": "2A", "name": "AC 2 Tier", "price": int(price * 1.55), "seats": 22, "status": "AVAILABLE", "is_ac": 1},
        {"code": "3A", "name": "AC 3 Tier", "price": int(price), "seats": 36, "status": "AVAILABLE", "is_ac": 1},
        {"code": "3E", "name": "AC 3 Economy", "price": int(price * 0.88), "seats": 28, "status": "AVAILABLE", "is_ac": 1},
        {"code": "SL", "name": "Sleeper Class", "price": max(180, int(price * 0.42)), "seats": 48, "status": "AVAILABLE", "is_ac": 0},
    ]


def search_trains_between_stations(source: str, destination: str, journey_date: str = "", quota: str = "GENERAL"):
    """
    Queries local SQLite database for trains matching the route.
    100% demo-only, zero external APIs.
    """
    src_code = get_station_code(source)
    dst_code = get_station_code(destination)

    conn = get_db_connection()
    try:
        if source and destination:
            rows = conn.execute("""
                SELECT * FROM vehicles 
                WHERE transport = 'train' 
                  AND (LOWER(source) LIKE LOWER(?) OR LOWER(?) LIKE LOWER(source))
                  AND (LOWER(destination) LIKE LOWER(?) OR LOWER(?) LIKE LOWER(destination))
                  AND active = 1
                ORDER BY id ASC
            """, (f"%{source}%", f"%{source}%", f"%{destination}%", f"%{destination}%")).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM vehicles WHERE transport = 'train' AND active = 1 ORDER BY id ASC"
            ).fetchall()

        trains = []
        for r in rows:
            classes = _get_train_classes(r["price"], r["name"], r["number"])
            trains.append({
                "train_number": str(r["number"]),
                "train_name": r["name"],
                "source_station": f"{r['source']} ({src_code})",
                "destination_station": f"{r['destination']} ({dst_code})",
                "departure_time": r["departure"],
                "arrival_time": r["arrival"],
                "duration": r["duration"],
                "base_fare": float(r["price"]),
                "train_type": r["vehicle_type"] or "Superfast",
                "rating": r["rating"] or "4.8",
                "amenities": [a.strip() for a in (r["amenities"] or "WiFi, Charging").split(",")],
                "classes": classes,
                "data_source": "SmartTravel Local Verified Database"
            })
    finally:
        conn.close()

    return {
        "success": True,
        "is_live": False,
        "provider": "SmartTravel Verified Local Database (Demo)",
        "source": source,
        "destination": destination,
        "source_code": src_code,
        "destination_code": dst_code,
        "journey_date": journey_date,
        "quota": quota,
        "total_trains": len(trains),
        "trains": trains,
        "last_updated": datetime.utcnow().strftime("%H:%M UTC")
    }


def get_train_live_status(train_number: str, start_day: int = 1):
    """
    Generates realistic scheduled timetable status from local SQLite data.
    Zero external APIs.
    """
    clean_no = str(train_number).strip()
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM vehicles WHERE transport = 'train' AND number = ?",
            (clean_no,)
        ).fetchone()
    finally:
        conn.close()

    train_name = row["name"] if row else f"Train #{clean_no}"
    source = row["source"] if row else "Origin Station"
    destination = row["destination"] if row else "Destination Station"
    dep_time = row["departure"] if row else "06:00"
    arr_time = row["arrival"] if row else "12:00"

    return {
        "success": True,
        "is_live": False,
        "provider": "SmartTravel Demo Timetable Tracker",
        "data": {
            "train_number": clean_no,
            "train_name": train_name,
            "current_status": "Running On Time (Demo Schedule)",
            "last_reported_station": f"{source} Central Area",
            "last_reported_time": "Real-time Timetable Sync",
            "scheduled_departure": dep_time,
            "scheduled_arrival": arr_time,
            "delay_minutes": 0,
            "route": f"{source} -> {destination}",
            "is_running": True
        }
    }
