"""
SmartTravel - Train API Integration Module
Connects to RailKit / Indian Railways REST API providers with caching,
error handling, station code resolution, response normalization, and fallback.
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
RAILKIT_API_URL = os.environ.get("RAILKIT_API_URL", "https://api.railkit.in/v1").rstrip("/")
RAILKIT_API_KEY = os.environ.get("RAILKIT_API_KEY", "").strip()

# Standard Railway Station Code Map
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
    "lucknow": "LKO",
    "varanasi": "BSB",
    "patna": "PNBE",
    "chandigarh": "CDG",
    "bhopal": "BPL",
    "indore": "INDB"
}

# In-Memory Cache: key -> (timestamp, data)
_API_CACHE = {}
CACHE_TTL_SCHEDULES = 600   # 10 minutes
CACHE_TTL_LIVE_STATUS = 120 # 2 minutes


def resolve_station_code(city_or_code):
    """Resolves city name to IRCTC 3/4-letter railway station code."""
    if not city_or_code:
        return "SBC"
    clean = city_or_code.strip()
    # If already a valid station code (2 to 5 uppercase characters)
    if clean.isupper() and 2 <= len(clean) <= 5:
        return clean
    lower = clean.lower()
    return STATION_CODE_MAP.get(lower, clean[:4].upper())


def _http_get(url, headers=None, timeout=6):
    """Helper for resilient GET requests using requests or urllib."""
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


def search_trains_between_stations(source, destination, journey_date=None, quota="GENERAL"):
    """
    Searches trains between two stations.
    Uses RailKit live API if RAILKIT_API_KEY is configured.
    Otherwise queries SQLite vehicles and normalizes output into a unified contract.
    """
    src_code = resolve_station_code(source)
    dst_code = resolve_station_code(destination)
    cache_key = f"trains_{src_code}_{dst_code}_{journey_date}_{quota}"

    # 1. Check cache
    now = time.time()
    if cache_key in _API_CACHE:
        cached_time, cached_data = _API_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SCHEDULES:
            cached_data["cached"] = True
            return cached_data

    # 2. Live RailKit API Attempt (if key is configured)
    if RAILKIT_API_KEY:
        url = f"{RAILKIT_API_URL}/trains/between?from={src_code}&to={dst_code}&date={journey_date or ''}&quota={quota}"
        headers = {
            "Authorization": f"Bearer {RAILKIT_API_KEY}",
            "Accept": "application/json",
            "User-Agent": "SmartTravel-Client/2.0"
        }
        status_code, api_data = _http_get(url, headers=headers, timeout=6)
        if status_code == 200 and "data" in api_data:
            normalized = _normalize_railkit_search(api_data["data"], src_code, dst_code, source, destination)
            result = {
                "status": "SUCCESS",
                "is_live": True,
                "provider": "RailKit Live API",
                "cached": False,
                "source_code": src_code,
                "destination_code": dst_code,
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "count": len(normalized),
                "data": normalized
            }
            _API_CACHE[cache_key] = (now, result)
            return result
        else:
            api_error = api_data.get("error") or api_data.get("message") or f"HTTP {status_code}"
            print(f"[TrainAPI] RailKit API response non-200 ({api_error}), using verified database.")

    # 3. Database-backed Verified Schedules (Demonstration Data)
    from database import get_db_connection
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM vehicles 
        WHERE transport = 'train' 
          AND (LOWER(source) LIKE LOWER(?) OR LOWER(destination) LIKE LOWER(?))
          AND active = 1
    """, (f"%{source}%", f"%{destination}%")).fetchall()
    
    if not rows:
        # Fallback to all trains if route not specifically filtered
        rows = conn.execute("SELECT * FROM vehicles WHERE transport = 'train' AND active = 1").fetchall()
    conn.close()

    normalized_db = []
    for r in rows:
        classes = _get_default_rail_classes(r["price"], r["name"])
        normalized_db.append({
            "train_number": str(r["number"]),
            "train_name": r["name"],
            "source_station": f"{r['source']} ({src_code})",
            "destination_station": f"{r['destination']} ({dst_code})",
            "departure_time": r["departure"],
            "arrival_time": r["arrival"],
            "duration": r["duration"],
            "base_fare": float(r["price"]),
            "classes": classes,
            "running_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "amenities": [a.strip() for a in (r["amenities"] or "WiFi, Charging Point").split(",")],
            "rating": r["rating"] or "4.8",
            "live_status_available": True,
            "data_source": "SmartTravel Verified DB"
        })

    result = {
        "status": "SUCCESS",
        "is_live": False,
        "provider": "SmartTravel Verified Database (Demo)",
        "cached": False,
        "source_code": src_code,
        "destination_code": dst_code,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "count": len(normalized_db),
        "data": normalized_db
    }
    _API_CACHE[cache_key] = (now, result)
    return result


def get_train_live_status(train_number, start_day=1):
    """
    Retrieves live running status of a train.
    Connects to RailKit if key present, else calculates realistic running schedule.
    """
    train_no = str(train_number).strip()
    cache_key = f"live_status_{train_no}_{start_day}"
    now = time.time()

    if cache_key in _API_CACHE:
        cached_time, cached_data = _API_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_LIVE_STATUS:
            cached_data["cached"] = True
            return cached_data

    # Live RailKit API
    if RAILKIT_API_KEY:
        url = f"{RAILKIT_API_URL}/trains/{train_no}/live?day={start_day}"
        headers = {
            "Authorization": f"Bearer {RAILKIT_API_KEY}",
            "Accept": "application/json"
        }
        status_code, api_data = _http_get(url, headers=headers, timeout=6)
        if status_code == 200 and "data" in api_data:
            result = {
                "status": "SUCCESS",
                "is_live": True,
                "provider": "RailKit Live API",
                "train_number": train_no,
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "data": api_data["data"]
            }
            _API_CACHE[cache_key] = (now, result)
            return result

    # Realistic Simulated Running Status for Demo
    from database import get_db_connection
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM vehicles WHERE number = ? AND transport = 'train'", (train_no,)).fetchone()
    conn.close()

    train_name = row["name"] if row else f"Express #{train_no}"
    dep = row["departure"] if row else "08:00"
    arr = row["arrival"] if row else "14:00"

    simulated_status = {
        "train_number": train_no,
        "train_name": train_name,
        "current_status": "Running On Time",
        "delay_minutes": 0,
        "last_reported_station": "Approaching Katpadi Junction",
        "last_reported_time": datetime.now().strftime("%H:%M"),
        "scheduled_departure": dep,
        "scheduled_arrival": arr,
        "platform_number": "Platform 1",
        "stations_covered": 4,
        "total_stations": 7,
        "data_source": "SmartTravel Live Simulation Engine"
    }

    result = {
        "status": "SUCCESS",
        "is_live": False,
        "provider": "SmartTravel Live Running Tracker (Demo)",
        "train_number": train_no,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "data": simulated_status
    }
    _API_CACHE[cache_key] = (now, result)
    return result


def _normalize_railkit_search(raw_trains, src_code, dst_code, src_name, dst_name):
    """Normalizes RailKit response structure into SmartTravel schema."""
    normalized = []
    for item in raw_trains:
        classes = []
        raw_classes = item.get("classes", [])
        if isinstance(raw_classes, list):
            for c in raw_classes:
                classes.append({
                    "class_code": c.get("code", "3A"),
                    "class_name": c.get("name", "AC 3-Tier"),
                    "price": float(c.get("fare", 1120)),
                    "seats": int(c.get("available_seats", 24)),
                    "status": c.get("status", "AVAILABLE"),
                    "is_ac": 1 if "AC" in c.get("name", "") or c.get("code") in ["1A", "2A", "3A", "3E", "CC", "EC"] else 0
                })

        normalized.append({
            "train_number": str(item.get("number", "12627")),
            "train_name": item.get("name", "Superfast Express"),
            "source_station": f"{src_name} ({src_code})",
            "destination_station": f"{dst_name} ({dst_code})",
            "departure_time": item.get("departure_time", "08:00"),
            "arrival_time": item.get("arrival_time", "14:00"),
            "duration": item.get("duration", "6h 00m"),
            "base_fare": float(item.get("min_fare", 650)),
            "classes": classes or _get_default_rail_classes(item.get("min_fare", 650), item.get("name", "")),
            "running_days": item.get("days", ["Daily"]),
            "amenities": item.get("amenities", ["Pantry Car", "Charging Point"]),
            "rating": "4.8",
            "live_status_available": True,
            "data_source": "RailKit Live API"
        })
    return normalized


def _get_default_rail_classes(base_price, train_name):
    """Builds standard Indian Railways class breakdown based on base price."""
    bp = float(base_price or 650)
    if "Vande Bharat" in train_name or "Shatabdi" in train_name:
        return [
            {"class_code": "CC", "class_name": "AC Chair Car", "price": round(bp, 2), "seats": 44, "status": "AVAILABLE", "is_ac": 1},
            {"class_code": "EC", "class_name": "Exec. Chair Car", "price": round(bp * 1.7, 2), "seats": 12, "status": "AVAILABLE", "is_ac": 1}
        ]

    return [
        {"class_code": "1A", "class_name": "AC First Class", "price": round(bp * 2.8, 2), "seats": 6, "status": "AVAILABLE", "is_ac": 1},
        {"class_code": "2A", "class_name": "AC 2 Tier", "price": round(bp * 1.8, 2), "seats": 18, "status": "AVAILABLE", "is_ac": 1},
        {"class_code": "3A", "class_name": "AC 3 Tier", "price": round(bp * 1.3, 2), "seats": 28, "status": "AVAILABLE", "is_ac": 1},
        {"class_code": "3E", "class_name": "AC 3 Economy", "price": round(bp * 1.15, 2), "seats": 32, "status": "AVAILABLE", "is_ac": 1},
        {"class_code": "SL", "class_name": "Sleeper Class", "price": round(bp * 0.7, 2), "seats": 48, "status": "AVAILABLE", "is_ac": 0}
    ]
