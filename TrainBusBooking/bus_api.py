"""
SmartTravel - Local Bus Fleet Service (Demo Only)
Provides intercity bus schedules using the local SQLite database.
NO external real-time APIs (No redBus, No external GDS). Pure offline demo data.
"""

from datetime import datetime
from database import get_db_connection


def search_buses_between_cities(source: str, destination: str, journey_date: str = ""):
    """
    Queries local SQLite database for buses matching the route.
    100% demo-only, zero external APIs.
    """
    clean_src = (source or "").strip()
    clean_dst = (destination or "").strip()

    conn = get_db_connection()
    try:
        if clean_src and clean_dst:
            rows = conn.execute("""
                SELECT * FROM vehicles 
                WHERE transport = 'bus' 
                  AND (LOWER(source) LIKE LOWER(?) OR LOWER(?) LIKE LOWER(source))
                  AND (LOWER(destination) LIKE LOWER(?) OR LOWER(?) LIKE LOWER(destination))
                  AND active = 1
                ORDER BY id ASC
            """, (f"%{clean_src}%", f"%{clean_src}%", f"%{clean_dst}%", f"%{clean_dst}%")).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM vehicles WHERE transport = 'bus' AND active = 1 ORDER BY id ASC"
            ).fetchall()

        buses = []
        for r in rows:
            bus_type = r["vehicle_type"] or "A/C Sleeper"
            is_ac = 0 if "Non-AC" in bus_type or "Non-AC" in r["name"] else 1
            is_sleeper = "Sleeper" in bus_type or "Sleeper" in r["name"]

            buses.append({
                "operator_name": r["name"],
                "bus_number": r["number"],
                "bus_type": bus_type,
                "source_city": r["source"],
                "destination_city": r["destination"],
                "departure_time": r["departure"],
                "arrival_time": r["arrival"],
                "duration": r["duration"],
                "fare": float(r["price"]),
                "rating": r["rating"] or "4.7",
                "available_seats": r["total_seats"],
                "is_ac": is_ac,
                "is_sleeper": 1 if is_sleeper else 0,
                "amenities": [a.strip() for a in (r["amenities"] or "Charging, Water").split(",")],
                "boarding_points": [
                    f"{r['source']} Main Terminal (0 min)",
                    f"{r['source']} City Center (+25 min)",
                    f"{r['source']} Highway Junction (+45 min)"
                ],
                "dropping_points": [
                    f"{r['destination']} Toll Plaza (-30 min)",
                    f"{r['destination']} Intercity Hub (-10 min)",
                    f"{r['destination']} Central Bus Stand (On-Time)"
                ],
                "data_source": "SmartTravel Local Verified Database"
            })
    finally:
        conn.close()

    return {
        "success": True,
        "is_live": False,
        "provider": "SmartTravel Verified Local Database (Demo)",
        "source": clean_src,
        "destination": clean_dst,
        "journey_date": journey_date,
        "total_buses": len(buses),
        "buses": buses,
        "last_updated": datetime.utcnow().strftime("%H:%M UTC")
    }
