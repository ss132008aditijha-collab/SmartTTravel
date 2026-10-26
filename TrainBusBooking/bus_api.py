"""
SmartTravel - Bus API Integration Module
Connects to redBus / Intercity Bus GDS REST API providers with caching,
error handling, response normalization, and verified database schedules.
"""

import os
import json
import time
from datetime import datetime
import urllib.request
import urllib.parse
import urllib.error

# Optional requests library
try:
    import requests
except ImportError:
    requests = None

# Provider Configuration from Environment Variables
REDBUS_API_URL = os.environ.get("REDBUS_API_URL", "https://api.redbus.in/v2").rstrip("/")
REDBUS_API_KEY = os.environ.get("REDBUS_API_KEY", "").strip()

# In-Memory Cache: key -> (timestamp, data)
_BUS_API_CACHE = {}
CACHE_TTL_BUSES = 600 # 10 minutes


def _http_get(url, headers=None, timeout=6):
    """Resilient HTTP GET request handler."""
    headers = headers or {}
    if requests:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            return resp.status_code, resp.json()
        except Exception as e:
            return 0, {"error": str(e)}
    else:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return response.getcode(), json.loads(body)
        except urllib.error.HTTPError as he:
            try:
                err_body = he.read().decode("utf-8")
                return he.code, json.loads(err_body)
            except Exception:
                return he.code, {"error": f"HTTP {he.code}"}
        except Exception as e:
            return 0, {"error": str(e)}


def search_buses_between_cities(source, destination, journey_date=None):
    """
    Searches intercity buses between two cities.
    Connects to authorized redBus inventory API if REDBUS_API_KEY is configured.
    Otherwise returns verified demonstration fleet schedules from database.
    """
    clean_src = (source or "Bengaluru").strip()
    clean_dst = (destination or "Chennai").strip()
    cache_key = f"bus_{clean_src.lower()}_{clean_dst.lower()}_{journey_date}"

    # 1. Check Cache
    now = time.time()
    if cache_key in _BUS_API_CACHE:
        cached_time, cached_data = _BUS_API_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_BUSES:
            cached_data["cached"] = True
            return cached_data

    # 2. Live redBus / Bus GDS API Attempt
    if REDBUS_API_KEY:
        url = f"{REDBUS_API_URL}/availabletrips?from={urllib.parse.quote(clean_src)}&to={urllib.parse.quote(clean_dst)}&date={journey_date or ''}"
        headers = {
            "Authorization": f"Bearer {REDBUS_API_KEY}",
            "Accept": "application/json",
            "User-Agent": "SmartTravel-Client/2.0"
        }
        status_code, api_data = _http_get(url, headers=headers, timeout=6)
        if status_code == 200 and "trips" in api_data:
            normalized = _normalize_redbus_trips(api_data["trips"], clean_src, clean_dst)
            result = {
                "status": "SUCCESS",
                "is_live": True,
                "provider": "redBus Live API",
                "cached": False,
                "source": clean_src,
                "destination": clean_dst,
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "count": len(normalized),
                "data": normalized
            }
            _BUS_API_CACHE[cache_key] = (now, result)
            return result
        else:
            api_error = api_data.get("error") or api_data.get("message") or f"HTTP {status_code}"
            print(f"[BusAPI] redBus API non-200 ({api_error}), using verified database.")

    # 3. Database-backed Verified Fleet (Demonstration Data)
    from database import get_db_connection
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM vehicles 
        WHERE transport = 'bus' 
          AND (LOWER(source) LIKE LOWER(?) OR LOWER(destination) LIKE LOWER(?))
          AND active = 1
    """, (f"%{clean_src}%", f"%{clean_dst}%")).fetchall()

    if not rows:
        rows = conn.execute("SELECT * FROM vehicles WHERE transport = 'bus' AND active = 1").fetchall()
    conn.close()

    normalized_buses = []
    for r in rows:
        bus_type = r["vehicle_type"] or "A/C Sleeper"
        is_ac = 0 if "Non-AC" in bus_type or "Non-AC" in r["name"] else 1
        is_sleeper = "Sleeper" in bus_type or "Sleeper" in r["name"]

        normalized_buses.append({
            "operator_name": r["name"],
            "bus_number": r["number"],
            "bus_type": bus_type,
            "source_city": r["source"],
            "destination_city": r["destination"],
            "departure_time": r["departure"],
            "arrival_time": r["arrival"],
            "duration": r["duration"],
            "fare": float(r["price"]),
            "available_seats": int(r["total_seats"] or 20),
            "is_ac": is_ac,
            "is_sleeper": 1 if is_sleeper else 0,
            "rating": r["rating"] or "4.8",
            "amenities": [a.strip() for a in (r["amenities"] or "WiFi, Charging Point, Blankets").split(",")],
            "boarding_points": [
                f"{r['source']} Central Bus Terminal",
                f"{r['source']} Ring Road Toll",
                f"{r['source']} Express Highway Junction"
            ],
            "drop_points": [
                f"{r['destination']} Central Bus Stand",
                f"{r['destination']} Bypass Highway Point"
            ],
            "decks": ["Lower Deck", "Upper Deck"] if is_sleeper else ["Main Deck"],
            "data_source": "SmartTravel Verified Fleet (Demo)"
        })

    result = {
        "status": "SUCCESS",
        "is_live": False,
        "provider": "SmartTravel Verified Fleet (Demo)",
        "cached": False,
        "source": clean_src,
        "destination": clean_dst,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "count": len(normalized_buses),
        "data": normalized_buses
    }
    _BUS_API_CACHE[cache_key] = (now, result)
    return result


def _normalize_redbus_trips(raw_trips, src_name, dst_name):
    """Normalizes redBus live API response into SmartTravel schema."""
    normalized = []
    for t in raw_trips:
        b_type = t.get("busType", "A/C Luxury Sleeper")
        is_ac = 1 if "A/C" in b_type or "AC" in b_type else 0
        is_slp = 1 if "Sleeper" in b_type else 0

        normalized.append({
            "operator_name": t.get("travels", "InterCity Luxury Coach"),
            "bus_number": t.get("busId", "KA-01-AB-1234"),
            "bus_type": b_type,
            "source_city": src_name,
            "destination_city": dst_name,
            "departure_time": t.get("departureTime", "21:00"),
            "arrival_time": t.get("arrivalTime", "06:00"),
            "duration": t.get("duration", "9h 00m"),
            "fare": float(t.get("fare", 850)),
            "available_seats": int(t.get("availableSeats", 18)),
            "is_ac": is_ac,
            "is_sleeper": is_slp,
            "rating": str(t.get("rating", "4.8")),
            "amenities": t.get("amenities", ["Charging Point", "Water Bottle", "Blankets"]),
            "boarding_points": [bp.get("locationName", "Main Boarding Point") for bp in t.get("boardingPoints", [])] or [f"{src_name} Terminal"],
            "drop_points": [dp.get("locationName", "Main Drop Point") for dp in t.get("droppingPoints", [])] or [f"{dst_name} Terminal"],
            "decks": ["Lower Deck", "Upper Deck"] if is_slp else ["Main Deck"],
            "data_source": "redBus Live API"
        })
    return normalized
