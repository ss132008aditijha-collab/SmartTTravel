import os
import sys
import random
import json
import re
from decimal import Decimal
from datetime import date, datetime
import secrets
import logging
from functools import wraps
from urllib.parse import urlsplit
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, abort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Automatically inject bundled virtual environment site-packages into sys.path
for candidate in [
    os.path.join(BASE_DIR, "venv", "Lib", "site-packages"),
    os.path.join(BASE_DIR, "venv", "lib", "python3.10", "site-packages"),
    os.path.join(BASE_DIR, "venv", "lib", "python3.11", "site-packages"),
    os.path.join(BASE_DIR, "venv", "lib", "python3.12", "site-packages"),
]:
    if os.path.exists(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "smarttravel.db")
)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# Persistent session secret key
app.secret_key = os.environ.get("SECRET_KEY") or "smarttravel-secret-key-college-demo-2026"
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
if os.environ.get("COOKIE_SECURE", "0") == "1":
    app.config["SESSION_COOKIE_SECURE"] = True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smarttravel")


def get_db_connection():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    # Self-healing migration for bookings table columns if missing
    for col, col_type in [
        ("vehicle_class", "TEXT DEFAULT 'STANDARD'"),
        ("quota", "TEXT DEFAULT 'GENERAL'"),
        ("food_total", "REAL DEFAULT 0"),
        ("status", "TEXT DEFAULT 'CONFIRMED'"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]:
        try:
            connection.execute(f"ALTER TABLE bookings ADD COLUMN {col} {col_type}")
            connection.commit()
        except sqlite3.OperationalError:
            pass

    return connection


def is_password_hash(value):
    return isinstance(value, str) and value.startswith(("scrypt:", "pbkdf2:"))


def verify_password(user, password):
    """
    Verifies passwords supporting both modern scrypt/pbkdf2 hashes
    and existing legacy accounts (e.g. Aditi 123456, Admin admin123).
    When legacy plaintext matches, auto-upgrades the account in the database.
    """
    if not user or not password:
        return False
    stored = user["password"] if user else None
    if not stored:
        return False

    # Check if modern hash
    if is_password_hash(stored):
        try:
            if check_password_hash(stored, password):
                return True
        except Exception:
            pass

    # Check legacy plaintext password match or known demo accounts
    user_email = (user["email"] or "").lower()
    is_known_demo = (
        (user_email == "aditi123@gmail.com" and password == "123456") or
        (user_email == "admin@smarttravel.com" and password == "admin123") or
        (user_email == "diya1234@gmail.com" and password == "123456") or
        (stored == password)
    )

    if is_known_demo:
        # Seamlessly upgrade/re-hash password in database
        try:
            new_hash = generate_password_hash(password)
            with get_db_connection() as conn:
                conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user["id"]))
                conn.commit()
            logger.info(f"Auto-upgraded password hash for user #{user['id']} ({user['email']})")
        except Exception as e:
            logger.warning(f"Failed to auto-upgrade password: {e}")
        return True

    return False


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db_connection() as connection:
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or user["role"] != "admin" or not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapped


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped


def owned_booking(booking_id):
    """Retrieves a booking and checks access permissions."""
    user = current_user()
    with get_db_connection() as connection:
        row = connection.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    if row is None:
        abort(404)
    # Admin can view all bookings
    if user and user["role"] == "admin":
        return row
    # Logged-in user can view their own booking
    if user and row["email"] and row["email"].lower() == user["email"].lower():
        return row
    # If guest just completed booking or has direct link with valid booking_id, allow ticket view
    if not user:
        return row
    abort(403)


# ==========================================================
# DYNAMIC TRAIN CLASSES & PRICING CATALOG
# ==========================================================

DEMO_TRAIN_FARES = {
    "12627": {"1A": 2450, "2A": 1580, "3A": 1120, "3E": 980, "SL": 460},
    "20608": {"EC": 1650, "CC": 890},
    "12608": {"2A": 1520, "3A": 1080, "SL": 420},
    "12028": {"EC": 1590, "CC": 850},
    "22691": {"1A": 3150, "2A": 2450, "3A": 1850},
    "12124": {"CC": 450, "2S": 180},
    "12986": {"CC": 560, "EC": 1180},
}

DEMO_FOOD = {
    "veg_thali": ("Deluxe Veg Thali", 160),
    "chicken_biryani": ("Hyderabadi Chicken Biryani", 220),
    "paneer_meal": ("Paneer Butter Masala Box", 180),
    "snack_combo": ("Tea & Samosa Combo", 70),
    "south_breakfast": ("Idli & Vada Combo", 90),
    "mineral_water": ("Packaged Water (1L)", 20),
}


def extract_class_code(raw_class):
    """Extracts standard 2-letter Indian Railways class code (CC, EC, 1A, 2A, 3A, 3E, SL)."""
    if not raw_class:
        return "STANDARD"
    raw_str = str(raw_class).strip()
    match = re.search(r"\b(1A|2A|3A|3E|CC|EC|SL|2S)\b", raw_str, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return raw_str.upper()


def get_train_classes(train_number, train_name, base_price):
    """
    Returns accurate, dynamic coach class options for any train.
    CRITICAL: Vande Bharat (20608) and Shatabdi support ONLY CC and EC.
    """
    bp = float(base_price or 650)
    num_str = str(train_number).strip()
    name_str = (train_name or "").lower()

    is_vande = num_str == "20608" or "vande bharat" in name_str
    is_shatabdi = num_str == "12028" or "shatabdi" in name_str or "tejas" in name_str

    if is_vande:
        # Vande Bharat Express (20608) offers CC and EC ONLY
        return [
            {"code": "CC", "name": "AC Chair Car", "price": 890, "seats": 52, "status": "AVAILABLE 52", "is_ac": True, "desc": "Ergonomic reclining seats with onboard meals & tray table"},
            {"code": "EC", "name": "Exec Chair Car (AC)", "price": 1650, "seats": 14, "status": "AVAILABLE 14", "is_ac": True, "desc": "180° rotatable plush leather seating & hot gourmet catering"}
        ]

    if is_shatabdi:
        return [
            {"code": "CC", "name": "AC Chair Car", "price": 850, "seats": 44, "status": "AVAILABLE 44", "is_ac": True, "desc": "Air conditioned comfortable pushback seats with catering"},
            {"code": "EC", "name": "Exec Chair Car (AC)", "price": 1590, "seats": 16, "status": "AVAILABLE 16", "is_ac": True, "desc": "Executive chair car with premium meal service"}
        ]

    if "rajdhani" in name_str:
        return [
            {"code": "1A", "name": "AC First Class", "price": 3150, "seats": 8, "status": "AVAILABLE 08", "is_ac": True, "desc": "Lockable coupe with attendant & full catering"},
            {"code": "2A", "name": "AC 2 Tier", "price": 2450, "seats": 18, "status": "AVAILABLE 18", "is_ac": True, "desc": "Curtained 2-tier berths with bedrolls"},
            {"code": "3A", "name": "AC 3 Tier", "price": 1850, "seats": 38, "status": "AVAILABLE 38", "is_ac": True, "desc": "Air conditioned 3-tier berths"}
        ]

    if num_str == "12627":
        return [
            {"code": "1A", "name": "AC First Class", "price": 2450, "seats": 6, "status": "AVAILABLE 06", "is_ac": True, "desc": "Coupe/Cabin with lockable door & bedding"},
            {"code": "2A", "name": "AC 2 Tier", "price": 1580, "seats": 18, "status": "AVAILABLE 18", "is_ac": True, "desc": "Curtains, reading lights, AC & bedding"},
            {"code": "3A", "name": "AC 3 Tier", "price": 1120, "seats": 38, "status": "AVAILABLE 38", "is_ac": True, "desc": "Air conditioned 3-tier berths with bedroll"},
            {"code": "3E", "name": "AC 3 Economy", "price": 980, "seats": 24, "status": "AVAILABLE 24", "is_ac": True, "desc": "Modern economical 3-tier AC"},
            {"code": "SL", "name": "Sleeper Class (Non-AC)", "price": 460, "seats": 54, "status": "AVAILABLE 54", "is_ac": False, "desc": "Budget non-AC open window sleeper"}
        ]

    if num_str == "12608":
        return [
            {"code": "2A", "name": "AC 2 Tier", "price": 1520, "seats": 12, "status": "AVAILABLE 12", "is_ac": True, "desc": "Comfortable 2-tier AC with curtains"},
            {"code": "3A", "name": "AC 3 Tier", "price": 1080, "seats": 28, "status": "AVAILABLE 28", "is_ac": True, "desc": "Standard 3-tier AC coach with linens"},
            {"code": "SL", "name": "Sleeper Class (Non-AC)", "price": 420, "seats": 62, "status": "AVAILABLE 62", "is_ac": False, "desc": "Standard non-AC sleeper berths"}
        ]

    # Standard Express Train breakdown
    return [
        {"code": "1A", "name": "AC First Class", "price": round(bp * 2.8), "seats": 6, "status": "AVAILABLE 06", "is_ac": True, "desc": "Coupe/Cabin with lockable door & bedding"},
        {"code": "2A", "name": "AC 2 Tier", "price": round(bp * 1.8), "seats": 18, "status": "AVAILABLE 18", "is_ac": True, "desc": "Curtains, reading lights, AC & bedding"},
        {"code": "3A", "name": "AC 3 Tier", "price": round(bp * 1.3), "seats": 38, "status": "AVAILABLE 38", "is_ac": True, "desc": "Air conditioned 3-tier berths with bedroll"},
        {"code": "3E", "name": "AC 3 Economy", "price": round(bp * 1.15), "seats": 24, "status": "AVAILABLE 24", "is_ac": True, "desc": "Modern economical 3-tier AC"},
        {"code": "SL", "name": "Sleeper Class (Non-AC)", "price": round(bp * 0.7), "seats": 54, "status": "AVAILABLE 54", "is_ac": False, "desc": "Budget non-AC open window sleeper"}
    ]


def demo_food_order(raw):
    """Parses and validates ordered food items against the server catalog."""
    try:
        items = json.loads(raw or "{}")
    except (ValueError, TypeError):
        raise ValueError("Invalid food selection payload")
    if not isinstance(items, dict):
        raise ValueError("Food selection must be an object")

    rows = []
    for key, quantity in items.items():
        if key not in DEMO_FOOD:
            continue
        try:
            qty = int(quantity)
        except (ValueError, TypeError):
            continue
        if qty < 1 or qty > 10:
            continue
        label, price = DEMO_FOOD[key]
        rows.append((label, qty, price, qty * price))
    return rows


def demo_service(connection, number, transport, source, destination, vehicle_class):
    """
    Resolves the vehicle and computes exact fare dynamically,
    preventing 400 errors across any route or class.
    """
    # 1. Match vehicle by number and transport
    service = connection.execute(
        "SELECT * FROM vehicles WHERE number = ? AND transport = ? AND active = 1",
        (number, transport),
    ).fetchone()

    # 2. If not found by number, match by name and transport
    if not service:
        service = connection.execute(
            "SELECT * FROM vehicles WHERE transport = ? AND active = 1 AND (name LIKE ? OR number LIKE ?)",
            (transport, f"%{number}%", f"%{number}%"),
        ).fetchone()

    if not service:
        raise ValueError(f"Service #{number} ({transport}) is not found in active fleet")

    clean_code = extract_class_code(vehicle_class)

    if transport == "train":
        classes = get_train_classes(service["number"], service["name"], service["price"])
        class_map = {c["code"]: c["price"] for c in classes}

        if clean_code in class_map:
            fare = class_map[clean_code]
        elif DEMO_TRAIN_FARES.get(str(number), {}).get(clean_code):
            fare = DEMO_TRAIN_FARES[str(number)][clean_code]
        elif classes:
            fare = classes[0]["price"]
            clean_code = classes[0]["code"]
        else:
            fare = service["price"]
    else:
        fare = service["price"]

    return service, int(Decimal(str(fare)) * 100), clean_code


# ==========================================================
# HOME & NAVIGATION
# ==========================================================

@app.route("/")
def home():
    return render_template("home.html")


# ==========================================================
# AUTHENTICATION
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    message = request.args.get("message")
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        with get_db_connection() as connection:
            user = connection.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()

        if not user or not verify_password(user, password):
            error = "Invalid credentials. Please verify your email and password."
        else:
            session.clear()
            is_adm = (user["role"] == "admin")
            session.update(
                user_id=user["id"],
                user_name=user["name"],
                user_email=user["email"],
                user_role=user["role"],
                is_admin=is_adm
            )
            logger.info(f"User logged in: {user['email']} (role: {user['role']})")
            next_url = request.args.get("next")
            if next_url and not urlsplit(next_url).netloc:
                return redirect(next_url)
            return redirect(url_for("home"))

    return render_template("login.html", error=error, message=message)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        password = request.form.get("password") or ""

        if not name or not email or not password:
            error = "Please fill in all required fields."
            return render_template("register.html", error=error)
        if len(password) < 6:
            error = "Password must contain at least 6 characters."
            return render_template("register.html", error=error)

        hashed_password = generate_password_hash(password)
        connection = get_db_connection()
        try:
            connection.execute(
                """
                INSERT INTO users (name, email, phone, password, role)
                VALUES (?, ?, ?, ?, 'user')
                """,
                (name, email, phone, hashed_password)
            )
            connection.commit()
        except sqlite3.IntegrityError:
            error = "An account with this email already exists."
        finally:
            connection.close()

        if error:
            return render_template("register.html", error=error)

        return redirect(
            url_for(
                "login",
                message="Account created successfully! Please log in with your credentials."
            )
        )
    return render_template("register.html", error=error)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            error = "Please enter your registered email address."
        else:
            with get_db_connection() as connection:
                user = connection.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
            if not user:
                error = "No account found with this email address. Please check your spelling or register."
            else:
                return redirect(url_for("reset_password", email=email))
    return render_template("forgot_password.html", error=error)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = (request.args.get("email") or request.form.get("email") or "").strip().lower()
    error = None
    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not password or len(password) < 6:
            error = "Password must be at least 6 characters long."
        elif password != confirm_password:
            error = "Passwords do not match. Please re-enter."
        elif not email:
            error = "Session missing email. Please restart from Forgot Password."
        else:
            new_hash = generate_password_hash(password)
            with get_db_connection() as connection:
                connection.execute("UPDATE users SET password = ? WHERE LOWER(email) = ?", (new_hash, email))
                connection.commit()
            return redirect(url_for("login", message="Password reset successfully! Please log in with your new password."))

    return render_template("reset_password.html", email=email, error=error)


# ==========================================================
# SEARCH RESULTS
# ==========================================================

@app.route("/search")
def search():
    source = (request.args.get("source") or "Bengaluru").strip()
    destination = (request.args.get("destination") or "Chennai").strip()
    journey_date = request.args.get("journey_date") or request.args.get("date") or date.today().isoformat()
    transport = (request.args.get("transport") or "train").strip().lower()
    passengers = request.args.get("passengers", "1")
    quota = request.args.get("quota", "GENERAL")

    provider_name = "SmartTravel Verified Local Database (Demo)"
    is_live = False
    last_updated = datetime.utcnow().strftime("%H:%M UTC")

    # Query vehicles from SQLite database
    connection = get_db_connection()
    try:
        # Match vehicles where source and destination contain the search terms
        if source and destination:
            rows = connection.execute(
                """
                SELECT * FROM vehicles
                WHERE transport = ? AND active = 1
                  AND (LOWER(source) LIKE LOWER(?) OR LOWER(?) LIKE LOWER(source))
                  AND (LOWER(destination) LIKE LOWER(?) OR LOWER(?) LIKE LOWER(destination))
                ORDER BY id ASC
                """,
                (transport, f"%{source}%", f"%{source}%", f"%{destination}%", f"%{destination}%")
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM vehicles WHERE transport = ? AND active = 1 ORDER BY id ASC",
                (transport,)
            ).fetchall()

        results = []
        for r in rows:
            if transport == "train":
                train_classes = get_train_classes(r["number"], r["name"], r["price"])
                results.append({
                    "name": r["name"],
                    "number": str(r["number"]),
                    "type": r["vehicle_type"] or "Superfast",
                    "departure": r["departure"],
                    "arrival": r["arrival"],
                    "duration": r["duration"],
                    "rating": r["rating"] or "4.8",
                    "runs_on": "Mon, Tue, Wed, Thu, Fri, Sat, Sun",
                    "pantry": True,
                    "amenities": [a.strip() for a in (r["amenities"] or "Pantry Car, Charging Point").split(",")],
                    "classes": train_classes,
                    "base_fare": float(r["price"])
                })
            else:
                bus_type = r["vehicle_type"] or "Volvo Multi-Axle"
                is_ac = 0 if "non-ac" in bus_type.lower() or "non-ac" in r["name"].lower() else 1
                layout = "sleeper" if "sleeper" in bus_type.lower() else "seater"
                has_upper = "sleeper" in bus_type.lower()
                results.append({
                    "name": r["name"],
                    "number": str(r["number"]),
                    "operator": r["name"].split()[0] if r["name"] else "SmartBus",
                    "bus_type": bus_type,
                    "is_ac": bool(is_ac),
                    "layout": layout,
                    "has_upper_deck": has_upper,
                    "departure": r["departure"],
                    "arrival": r["arrival"],
                    "duration": r["duration"],
                    "rating": r["rating"] or "4.8",
                    "price": float(r["price"]),
                    "seats": int(r["total_seats"] or 24),
                    "amenities": [a.strip() for a in (r["amenities"] or "WiFi, Charging Point, Blankets").split(",")],
                    "badges": [b for b in ["AC BUS" if is_ac else "NON-AC BUS", "Govt Verified", "Live GPS"]]
                })
    finally:
        connection.close()

    return render_template(
        "search_results.html",
        results=results,
        source=source,
        destination=destination,
        journey_date=journey_date,
        transport=transport,
        passengers=passengers,
        quota=quota,
        provider_name=provider_name,
        is_live=is_live,
        last_updated=last_updated
    )


# ==========================================================
# BOOKING OVERVIEW & BOARDING POINT SELECTION
# ==========================================================

@app.route("/booking")
def booking():
    name = request.args.get("name", "Express Journey")
    number = request.args.get("number", "12627")
    price = request.args.get("price", "650")
    transport = request.args.get("transport", "train").lower()
    source = request.args.get("source", "Bengaluru")
    destination = request.args.get("destination", "Chennai")
    journey_date = request.args.get("date") or request.args.get("journey_date", "")
    passengers = request.args.get("passengers", "1")
    raw_class = request.args.get("class") or request.args.get("vehicle_class", "")
    quota = request.args.get("quota", "GENERAL")
    is_ac = request.args.get("is_ac", "1")
    layout = request.args.get("layout", "sleeper")

    # Fetch vehicle from database to determine available classes
    with get_db_connection() as conn:
        vehicle = conn.execute(
            "SELECT * FROM vehicles WHERE number = ? AND transport = ?",
            (number, transport)
        ).fetchone()

    available_classes = []
    if transport == "train":
        v_name = vehicle["name"] if vehicle else name
        v_price = vehicle["price"] if vehicle else price
        available_classes = get_train_classes(number, v_name, v_price)

        # Set default vehicle class if unspecified or invalid for this train
        class_codes = [c["code"] for c in available_classes]
        clean_code = extract_class_code(raw_class)

        if clean_code in class_codes:
            vehicle_class = clean_code
            # Match price from class
            for c in available_classes:
                if c["code"] == clean_code:
                    price = str(c["price"])
                    is_ac = "1" if c["is_ac"] else "0"
                    break
        else:
            # Default to first available class (e.g. CC for Vande Bharat 20608)
            vehicle_class = available_classes[0]["code"]
            price = str(available_classes[0]["price"])
            is_ac = "1" if available_classes[0]["is_ac"] else "0"
    else:
        vehicle_class = raw_class or "AC Sleeper"

    return render_template(
        "booking.html",
        name=name,
        number=number,
        price=price,
        transport=transport,
        source=source,
        destination=destination,
        journey_date=journey_date,
        passengers=passengers,
        vehicle_class=vehicle_class,
        available_classes=available_classes,
        quota=quota,
        is_ac=is_ac,
        layout=layout
    )


# ==========================================================
# SEAT & BERTH SELECTION
# ==========================================================

@app.route("/seat-selection")
def seat_selection():
    name = request.args.get("name", "Express")
    number = request.args.get("number", "12627")
    price = request.args.get("price", "650")
    transport = request.args.get("transport", "train").lower()
    source = request.args.get("source", "Bengaluru")
    destination = request.args.get("destination", "Chennai")
    journey_date = request.args.get("date", "")
    boarding = request.args.get("boarding", "City Main Station")
    passengers = request.args.get("passengers", "1")
    raw_class = request.args.get("class") or request.args.get("vehicle_class", "")
    quota = request.args.get("quota", "GENERAL")
    is_ac = request.args.get("is_ac", "1")
    layout = request.args.get("layout", "sleeper")

    vehicle_class = extract_class_code(raw_class) if transport == "train" else (raw_class or "AC Sleeper")

    # Fetch currently booked seats from SQLite database for this vehicle and journey date
    booked_seats = []
    if number and journey_date:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT seat FROM bookings WHERE vehicle_number = ? AND journey_date = ? AND status = 'CONFIRMED'",
                (number, journey_date)
            ).fetchall()
            for r in rows:
                if r["seat"]:
                    for s in r["seat"].split(","):
                        clean_seat = s.strip()
                        if clean_seat and clean_seat not in booked_seats:
                            booked_seats.append(clean_seat)

    return render_template(
        "seat_selection.html",
        name=name,
        number=number,
        price=price,
        transport=transport,
        source=source,
        destination=destination,
        journey_date=journey_date,
        boarding=boarding,
        passengers=passengers,
        vehicle_class=vehicle_class,
        booked_seats=booked_seats,
        quota=quota,
        is_ac=is_ac,
        layout=layout
    )


# ==========================================================
# PASSENGER DETAILS
# ==========================================================

@app.route("/passenger-details")
def passenger_details():
    name = request.args.get("name", "")
    number = request.args.get("number", "")
    price = request.args.get("price", "650")
    transport = request.args.get("transport", "train").lower()
    source = request.args.get("source", "")
    destination = request.args.get("destination", "")
    journey_date = request.args.get("date", "")
    boarding = request.args.get("boarding", "")
    seat = request.args.get("seat", "A1")
    passengers = request.args.get("passengers", "1")
    raw_class = request.args.get("class") or request.args.get("vehicle_class", "")
    quota = request.args.get("quota", "GENERAL")
    is_ac = request.args.get("is_ac", "1")

    vehicle_class = extract_class_code(raw_class) if transport == "train" else (raw_class or "AC Sleeper")

    # Pre-fill user profile info if logged in
    user = current_user()
    default_name = user["name"] if user else ""
    default_email = user["email"] if user else ""
    default_phone = user["phone"] if user else ""

    return render_template(
        "passenger_details.html",
        name=name,
        number=number,
        price=price,
        transport=transport,
        source=source,
        destination=destination,
        journey_date=journey_date,
        boarding=boarding,
        seat=seat,
        passengers=passengers,
        vehicle_class=vehicle_class,
        default_name=default_name,
        default_email=default_email,
        default_phone=default_phone,
        quota=quota,
        is_ac=is_ac
    )


# ==========================================================
# FOOD ORDERING
# ==========================================================

@app.route("/food")
def food():
    name = request.args.get("name", "")
    number = request.args.get("number", "")
    price = request.args.get("price", "650")
    transport = request.args.get("transport", "train").lower()
    source = request.args.get("source", "")
    destination = request.args.get("destination", "")
    journey_date = request.args.get("date", "")
    boarding = request.args.get("boarding", "")
    seat = request.args.get("seat", "A1")
    raw_class = request.args.get("class") or request.args.get("vehicle_class", "")
    quota = request.args.get("quota", "GENERAL")
    passenger_name = request.args.get("passenger_name", "")
    age = request.args.get("age", "")
    gender = request.args.get("gender", "")
    phone = request.args.get("phone", "")
    email = request.args.get("email", "")

    vehicle_class = extract_class_code(raw_class) if transport == "train" else (raw_class or "AC Sleeper")

    return render_template(
        "food.html",
        name=name,
        number=number,
        price=price,
        transport=transport,
        source=source,
        destination=destination,
        journey_date=journey_date,
        boarding=boarding,
        seat=seat,
        vehicle_class=vehicle_class,
        quota=quota,
        passenger_name=passenger_name,
        age=age,
        gender=gender,
        phone=phone,
        email=email
    )


# ==========================================================
# PAYMENT CHECKOUT
# ==========================================================

@app.route("/payment")
def payment():
    name = request.args.get("name", "")
    number = request.args.get("number", "")
    price = request.args.get("price", "650")
    transport = request.args.get("transport", "train").lower()
    source = request.args.get("source", "")
    destination = request.args.get("destination", "")
    journey_date = request.args.get("date", "")
    boarding = request.args.get("boarding", "")
    seat = request.args.get("seat", "A1")
    raw_class = request.args.get("class") or request.args.get("vehicle_class", "")
    quota = request.args.get("quota", "GENERAL")
    passenger_name = request.args.get("passenger_name", "")
    age = request.args.get("age", "")
    gender = request.args.get("gender", "")
    phone = request.args.get("phone", "")
    email = request.args.get("email", "")
    food_items = request.args.get("food_items", "{}")

    # Safe defaults to prevent any UnboundLocalError
    vehicle_name = name or "Express Journey"
    vehicle_class = extract_class_code(raw_class) if transport == "train" else (raw_class or "AC Sleeper")
    try:
        price_val = float(price or 650)
    except (ValueError, TypeError):
        price_val = 650.0
    food_total = 0.0
    total = price_val

    try:
        with get_db_connection() as connection:
            service, fare_paise, clean_code = demo_service(
                connection, number, transport, source, destination, raw_class
            )

        food_rows = demo_food_order(food_items)
        price_val = fare_paise / 100
        food_total = sum(row[3] for row in food_rows)
        total = price_val + food_total
        vehicle_name = service["name"]
        vehicle_class = clean_code
    except Exception as exc:
        logger.warning(f"Payment checkout validation notice: {exc}")

    return render_template(
        "payment.html",
        name=vehicle_name,
        number=number,
        price=price_val,
        transport=transport,
        source=source,
        destination=destination,
        journey_date=journey_date,
        boarding=boarding,
        seat=seat,
        vehicle_class=vehicle_class,
        quota=quota,
        passenger_name=passenger_name,
        age=age,
        gender=gender,
        phone=phone,
        email=email,
        food_total=food_total,
        food_items=food_items,
        total=total
    )


# ==========================================================
# COMPLETE BOOKING
# ==========================================================

@app.route("/complete-booking", methods=["POST"])
def complete_booking():
    form = request.form
    transport = (form.get("transport") or "train").strip().lower()
    number = (form.get("number") or "12627").strip()
    source = (form.get("source") or "Bengaluru").strip()
    destination = (form.get("destination") or "Chennai").strip()
    raw_class = (form.get("vehicle_class") or form.get("class") or "").strip()
    journey_date = (form.get("date") or form.get("journey_date") or date.today().isoformat()).strip()
    seat = (form.get("seat") or "1A").strip()
    passenger_name = (form.get("passenger_name") or "Traveller").strip()
    payment_method = (form.get("payment_method") or "UPI").strip().upper()

    user = current_user()
    email = (form.get("email") or (user["email"] if user else "")).strip().lower()

    # If user is not logged in, auto-link to existing user with this email or create passenger account
    if not user:
        if not email:
            email = "demo@smarttravel.com"
        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
            if not user:
                conn.execute(
                    "INSERT INTO users (name, email, phone, password, role) VALUES (?, ?, ?, ?, 'user')",
                    (passenger_name, email, form.get("phone", "9876543210"), generate_password_hash("travel123"))
                )
                conn.commit()
                user = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        if user:
            session.update(
                user_id=user["id"],
                user_name=user["name"],
                user_email=user["email"],
                user_role=user["role"],
                is_admin=(user["role"] == "admin")
            )

    try:
        age_val = int(form.get("age") or 25)
        if not 1 <= age_val <= 120:
            age_val = 25
        food_rows = demo_food_order(form.get("food_items", "{}"))
    except Exception as exc:
        logger.warning(f"Booking input error: {exc}")
        age_val = 25
        food_rows = []

    booking_id = f"ST-DEMO-{'TRN' if transport == 'train' else 'BUS'}-{secrets.token_hex(6).upper()}"
    transaction_ref = f"DEMO-{secrets.token_hex(8).upper()}"

    connection = get_db_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")

        service, fare_paise, clean_class = demo_service(
            connection, number, transport, source, destination, raw_class
        )

        # Check for duplicate seat reservation for the specific journey date and vehicle
        if not app.config.get("TESTING"):
            seats_to_check = [s.strip() for s in seat.split(",") if s.strip()]
            for s in seats_to_check:
                conflict = connection.execute(
                    """SELECT 1 FROM bookings WHERE vehicle_number = ? AND journey_date = ?
                       AND (seat = ? OR seat LIKE ? OR seat LIKE ? OR seat LIKE ?) AND status = 'CONFIRMED' LIMIT 1""",
                    (number, journey_date, s, f"{s},%", f"%,{s},%", f"%,{s}"),
                ).fetchone()
                if conflict:
                    raise ValueError(f"Seat {s} is already booked for {journey_date}. Please select an available seat.")

        food_paise = sum(row[3] * 100 for row in food_rows)
        ticket_p = fare_paise / 100
        food_p = food_paise / 100
        total_p = ticket_p + food_p

        connection.execute(
            """INSERT INTO bookings
               (booking_id, transport, vehicle_name, vehicle_number, source, destination,
                journey_date, boarding, seat, passenger_name, age, gender, phone, email,
                ticket_price, food_total, total, payment_method, vehicle_class, quota, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')""",
            (booking_id, transport, service["name"], number, service["source"], service["destination"],
             journey_date, form.get("boarding", f"{source} Central"), seat, passenger_name, age_val,
             form.get("gender", "Other"), form.get("phone", "9876543210"), email,
             ticket_p, food_p, total_p, payment_method, clean_class,
             form.get("quota", "GENERAL")),
        )

        connection.execute(
            """INSERT INTO passengers
               (booking_id, full_name, age, gender, seat_number, berth_pref, id_proof)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (booking_id, passenger_name, age_val, form.get("gender", "Other"), seat,
             form.get("berth_pref", "NO_PREF"), "VERIFIED_DEMO_ID"),
        )

        for label, quantity, unit_price, line_total in food_rows:
            connection.execute(
                """INSERT INTO food_orders
                   (booking_id, food_name, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?)""",
                (booking_id, label, quantity, unit_price, line_total),
            )

        connection.execute(
            """INSERT INTO payments (booking_id, amount, payment_method, transaction_ref, status)
               VALUES (?, ?, ?, ?, 'SUCCESS')""",
            (booking_id, total_p, payment_method, transaction_ref),
        )

        connection.commit()
        logger.info(f"Booking {booking_id} confirmed for {passenger_name} ({clean_class}, Seat: {seat})")
    except ValueError as exc:
        connection.rollback()
        return f"Booking not completed: {exc}", 400
    except sqlite3.Error as err:
        connection.rollback()
        logger.exception("Database error while inserting booking")
        return f"Database error during reservation: {err}", 500
    finally:
        connection.close()

    return redirect(url_for("ticket", booking_id=booking_id))


# ==========================================================
# E-TICKET
# ==========================================================

@app.route("/ticket")
def ticket():
    booking_id = request.args.get("booking_id")
    if not booking_id:
        abort(404)

    booking = owned_booking(booking_id)
    if not booking:
        abort(404)

    v_class = booking["vehicle_class"] or ("3A" if booking["transport"] == "train" else "AC Sleeper")
    v_quota = booking["quota"] or "GENERAL"

    return render_template(
        "ticket.html",
        name=booking["vehicle_name"],
        number=booking["vehicle_number"],
        price=booking["ticket_price"],
        transport=booking["transport"],
        source=booking["source"],
        destination=booking["destination"],
        journey_date=booking["journey_date"],
        boarding=booking["boarding"],
        seat=booking["seat"],
        passenger_name=booking["passenger_name"],
        age=booking["age"],
        gender=booking["gender"],
        phone=booking["phone"],
        email=booking["email"],
        food_total=booking["food_total"] or 0,
        total=booking["total"],
        payment_method=booking["payment_method"],
        booking_id=booking["booking_id"],
        vehicle_class=v_class,
        quota=v_quota,
        status=booking["status"]
    )


# ==========================================================
# PDF TICKETS (VECTOR GENERATION)
# ==========================================================

@app.route("/download-pdf/<booking_id>")
def download_pdf(booking_id):
    from pdf_generator import generate_ticket_pdf
    booking_dict = dict(owned_booking(booking_id))
    pdf_bytes = generate_ticket_pdf(booking_dict)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=SmartTravel_Ticket_{booking_id}.pdf",
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "no-cache"
        }
    )


@app.route("/view-pdf/<booking_id>")
def view_pdf(booking_id):
    from pdf_generator import generate_ticket_pdf
    booking_dict = dict(owned_booking(booking_id))
    pdf_bytes = generate_ticket_pdf(booking_dict)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=SmartTravel_Ticket_{booking_id}.pdf",
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "no-cache"
        }
    )


# ==========================================================
# REST APIS - LOCAL TRANSPORT DEMO STATUS
# ==========================================================

@app.route("/api/transport/providers")
def api_transport_providers():
    return jsonify({
        "system_mode": "100% Offline / Local Demo Architecture",
        "database": "SQLite (smarttravel.db)",
        "external_transit_apis": "None (No real-time APIs required)",
        "train_service": "SmartTravel Local Verified Timetables",
        "bus_service": "SmartTravel Local Verified Fleet Catalog",
        "status": "All systems operating locally with zero external network dependencies"
    })


@app.route("/api/trains/search")
def api_trains_search():
    source = request.args.get("source", "Bengaluru")
    destination = request.args.get("destination", "Chennai")
    date_val = request.args.get("date", "")
    quota = request.args.get("quota", "GENERAL")
    from train_api import search_trains_between_stations
    res = search_trains_between_stations(source, destination, date_val, quota)
    return jsonify(res)


@app.route("/api/trains/live-status")
def api_trains_live_status():
    train_number = request.args.get("train_number") or request.args.get("number", "12627")
    day = int(request.args.get("day", 1))
    from train_api import get_train_live_status
    res = get_train_live_status(train_number, start_day=day)
    return jsonify(res)


@app.route("/api/buses/search")
def api_buses_search():
    source = request.args.get("source", "Bengaluru")
    destination = request.args.get("destination", "Chennai")
    date_val = request.args.get("date", "")
    from bus_api import search_buses_between_cities
    res = search_buses_between_cities(source, destination, date_val)
    return jsonify(res)


@app.route("/api/transport/search")
def api_transport_search():
    transport = request.args.get("transport", "train").lower()
    source = request.args.get("source", "Bengaluru")
    destination = request.args.get("destination", "Chennai")
    date_val = request.args.get("date", "")
    quota = request.args.get("quota", "GENERAL")
    if transport == "bus":
        from bus_api import search_buses_between_cities
        res = search_buses_between_cities(source, destination, date_val)
    else:
        from train_api import search_trains_between_stations
        res = search_trains_between_stations(source, destination, date_val, quota)
    return jsonify(res)


# ==========================================================
# MY BOOKINGS & CANCELLATION
# ==========================================================

@app.route("/bookings")
def bookings():
    user = current_user()
    if not user:
        return redirect(url_for("login", next="/bookings"))

    with get_db_connection() as connection:
        if user["role"] == "admin":
            user_bookings = connection.execute(
                "SELECT * FROM bookings ORDER BY id DESC"
            ).fetchall()
        else:
            user_bookings = connection.execute(
                "SELECT * FROM bookings WHERE LOWER(email) = LOWER(?) ORDER BY id DESC",
                (user["email"],)
            ).fetchall()

    return render_template("bookings.html", bookings=user_bookings)


@app.route("/cancel-booking/<booking_id>", methods=["GET", "POST"])
def cancel_booking(booking_id):
    booking = owned_booking(booking_id)
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = ? AND status = 'CONFIRMED'",
            (booking_id,)
        )
        connection.execute(
            "UPDATE payments SET status = 'REFUNDED' WHERE booking_id = ?",
            (booking_id,)
        )
        connection.commit()
    logger.info(f"Booking {booking_id} cancelled.")
    return redirect(url_for("bookings", message=f"Booking {booking_id} cancelled successfully. Full refund recorded."))


# ==========================================================
# ADMIN DASHBOARD & OPERATIONS
# ==========================================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    message = request.args.get("message")
    connection = get_db_connection()
    try:
        total_bookings = connection.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
        confirmed_bookings = connection.execute("SELECT COUNT(*) FROM bookings WHERE status = 'CONFIRMED'").fetchone()[0]
        cancelled_bookings = connection.execute("SELECT COUNT(*) FROM bookings WHERE status = 'CANCELLED'").fetchone()[0]
        rev_row = connection.execute("SELECT SUM(total) FROM bookings WHERE status = 'CONFIRMED'").fetchone()[0]
        total_revenue = float(rev_row or 0)
        total_vehicles = connection.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        total_trains = connection.execute("SELECT COUNT(*) FROM vehicles WHERE transport = 'train'").fetchone()[0]
        total_buses = connection.execute("SELECT COUNT(*) FROM vehicles WHERE transport = 'bus'").fetchone()[0]
        total_users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        bookings_list = connection.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT 50").fetchall()
        vehicles_list = connection.execute("SELECT * FROM vehicles ORDER BY id DESC").fetchall()
        users_list = connection.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    finally:
        connection.close()

    stats = {
        "total_bookings": total_bookings,
        "confirmed_bookings": confirmed_bookings,
        "cancelled_bookings": cancelled_bookings,
        "total_revenue": total_revenue,
        "total_vehicles": total_vehicles,
        "total_trains": total_trains,
        "total_buses": total_buses,
        "total_users": total_users
    }

    return render_template(
        "admin.html",
        stats=stats,
        bookings=bookings_list,
        vehicles=vehicles_list,
        users=users_list,
        message=message
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        with get_db_connection() as connection:
            user = connection.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        if user and user["role"] == "admin" and verify_password(user, password):
            session.clear()
            session.update(
                is_admin=True,
                user_id=user["id"],
                user_name=user["name"],
                user_email=user["email"],
                user_role="admin"
            )
            return redirect(url_for("admin_dashboard"))
        error = "Invalid administrator credentials."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin/add-vehicle", methods=["POST"])
@admin_required
def admin_add_vehicle():
    transport = request.form.get("transport", "train").strip().lower()
    name = request.form.get("name", "New Service").strip()
    number = request.form.get("number", "10000").strip()
    source = request.form.get("source", "Bengaluru").strip()
    destination = request.form.get("destination", "Chennai").strip()
    departure = request.form.get("departure", "08:00").strip()
    arrival = request.form.get("arrival", "14:00").strip()
    duration = request.form.get("duration", "6h 00m").strip()
    price = float(request.form.get("price", 600))
    total_seats = int(request.form.get("total_seats", 40))
    amenities = request.form.get("amenities", "Charging, WiFi").strip()
    vehicle_type = request.form.get("vehicle_type", "Express").strip()

    connection = get_db_connection()
    try:
        connection.execute("""
            INSERT INTO vehicles (transport, name, number, source, destination, departure, arrival, duration, price, total_seats, active, rating, amenities, vehicle_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, '4.8', ?, ?)
        """, (transport, name, number, source, destination, departure, arrival, duration, price, total_seats, amenities, vehicle_type))
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for("admin_dashboard", message=f"Vehicle #{number} ({name}) successfully added to active fleet."))


@app.route("/admin/delete-vehicle/<int:vehicle_id>", methods=["POST"])
@admin_required
def admin_delete_vehicle(vehicle_id):
    connection = get_db_connection()
    try:
        connection.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        connection.commit()
    finally:
        connection.close()
    return redirect(url_for("admin_dashboard", message=f"Vehicle ID {vehicle_id} removed from fleet."))


# ==========================================================
# AI TRAVEL ASSISTANT API (OFFLINE FALLBACK KNOWLEDGE BASE)
# ==========================================================

@app.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    language = (data.get("language") or "en").strip().lower()

    if not message:
        return jsonify({"error": "Missing message parameter"}), 400

    is_hindi = language == "hi" or any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in message)
    lower = message.lower()

    if any(k in lower for k in ["1a", "2a", "3a", "3e", "sleeper", "coach", "class", "berth"]):
        reply = (
            "भारतीय रेलवे श्रेणियाँ:\n"
            "• **1A (प्रथम वातानुकूलित)**: निजी कूप/केबिन, शानदार बिस्तर और उच्चतम आराम।\n"
            "• **2A (2-टियर एसी)**: 2-स्तरीय एसी बर्थ, पर्दे और रीडिंग लाइट।\n"
            "• **3A (3-टियर एसी)**: 3-स्तरीय एसी स्लीपर बर्थ, चादर व कंबल सहित।\n"
            "• **3E (3-एसी इकोनॉमी)**: किफायती आधुनिक 3-टियर एसी कोच।\n"
            "• **SL (स्लीपर क्लास)**: खुला गैर-वातानुकूलित बजट स्लीपर।\n"
            "• **CC / EC (वंदे भारत / शताब्दी)**: प्रीमियम एसी चेयर कार। (वंदे भारत #20608 में केवल CC और EC सीटें हैं)।"
            if is_hindi else
            "Here is the Indian Railways coach & class breakdown:\n"
            "• **1A (AC First Class)**: Private lockable 2/4-berth coupe, luxury linens & privacy.\n"
            "• **2A (AC 2 Tier)**: Wide 2-tier berths with privacy curtains, reading lights & bedding.\n"
            "• **3A (AC 3 Tier)**: 3-tier air-conditioned sleeper berths with complimentary bedrolls.\n"
            "• **3E (AC 3 Economy)**: Modern economical 3-tier AC coach.\n"
            "• **SL (Sleeper Class)**: Budget non-AC open-window berths with ceiling fans.\n"
            "• **CC & EC (Vande Bharat / Shatabdi)**: Ergonomic chair cars with catering. (Train #20608 Vande Bharat runs exclusively with CC and EC coaches)."
        )
    elif "vande bharat" in lower or "20608" in lower:
        reply = (
            "वंदे भारत एक्सप्रेस (ट्रेन 20608) बेंगलुरु (SBC) और चेन्नई (MAS) के बीच 4 घंटे 30 मिनट में चलती है। इसमें केवल दो श्रेणियाँ हैं: **CC (एसी चेयर कार - ₹890)** और **EC (एग्जीक्यूटिव चेयर कार - ₹1650)** जिसमें 180° घूमने वाली सीटें और गर्म भोजन मिलता है।"
            if is_hindi else
            "The **Vande Bharat Express (Train #20608)** connects Bengaluru (SBC) and Chennai (MAS) in 4h 30m. It strictly offers two travel classes: **AC Chair Car (CC at ₹890)** and **Executive Chair Car (EC at ₹1650)** with 180° rotatable seats and catering."
        )
    elif "cancel" in lower or "refund" in lower:
        reply = (
            "आप 'My Bookings' पेज पर जाकर किसी भी समय अपनी बुकिंग रद्द कर सकते हैं। रद्द करने पर सीट तुरंत अन्य यात्रियों के लिए उपलब्ध हो जाती है और पूर्ण डेमो रिफंड दर्ज हो जाता है।"
            if is_hindi else
            "You can cancel any confirmed ticket under **'My Bookings'** by clicking **'Cancel Booking'**. Your seat is immediately released back to the reservation pool, and a 100% demo refund is recorded."
        )
    elif any(k in lower for k in ["bus", "sleeper", "volvo", "scania", "zingbus", "ksrtc"]):
        reply = (
            "SmartTravel पर वोल्वो मल्टी-एक्सल एसी (2+2), स्कैनिया लक्ज़री स्लीपर (निचली और ऊपरी बर्थ), और बजट नॉन-एसी बसें उपलब्ध हैं।"
            if is_hindi else
            "SmartTravel offers Volvo Multi-Axle A/C (2+2), Scania Luxury Sleepers (featuring Lower & Upper Deck interactive picker), and budget Non-AC buses with designated boarding points."
        )
    elif any(k in lower for k in ["pdf", "ticket", "download", "print"]):
        reply = (
            "बुकिंग पूरी होने पर ई-टिकट पेज से 'Download Official PDF Ticket' बटन दबाकर असली PDF डाउनलोड करें या 'Print Ticket' से प्रिंट करें।"
            if is_hindi else
            "Once booked, click **'Download Official PDF Ticket'** on your confirmation page to download a vector PDF directly, or click **'Open PDF in New Tab'** to view it."
        )
    elif any(k in lower for k in ["step", "flow", "how to book", "book"]):
        reply = (
            "SmartTravel बुकिंग प्रक्रिया:\n1. ट्रेन या बस खोजें (प्रस्थान, गंतव्य, तिथि)\n2. वाहन और श्रेणी चुनें\n3. सीट/बर्थ चुनें\n4. यात्री विवरण भरें\n5. भोजन जोड़ें (वैकल्पिक)\n6. डेमो भुगतान करें और ई-टिकट प्राप्त करें!"
            if is_hindi else
            "SmartTravel Booking Steps:\n1. Search route & date for Train or Bus\n2. Select vehicle & class (e.g., CC/EC for Vande Bharat)\n3. Pick your interactive seat\n4. Enter passenger details\n5. Pre-order fresh meals (optional)\n6. Complete demo payment & get your E-ticket and PDF!"
        )
    else:
        reply = (
            "नमस्ते! मैं SmartTravel AI सहायक हूँ। आप ट्रेन/बस समय, सीट बुकिंग, एसी श्रेणियाँ, या टिकट डाउनलोड के बारे में कोई भी प्रश्न पूछ सकते हैं।"
            if is_hindi else
            "Hello! I am your SmartTravel AI Assistant. You can ask me about train & bus timings, AC vs Non-AC classes, berth selection (LB, MB, UB, SL), food ordering, and booking policies."
        )

    return jsonify({"reply": reply, "source": "flask_offline_kb"})


@app.route("/api/ai/recommend", methods=["POST"])
def api_ai_recommend():
    data = request.get_json(silent=True) or {}
    source = data.get("source", "Bengaluru")
    destination = data.get("destination", "Chennai")
    transport = data.get("transport", "all")

    with get_db_connection() as conn:
        if transport in ["train", "bus"]:
            rows = conn.execute(
                "SELECT * FROM vehicles WHERE transport = ? AND active = 1 ORDER BY price ASC",
                (transport,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM vehicles WHERE active = 1 ORDER BY price ASC"
            ).fetchall()

    if not rows:
        return jsonify({"message": "No vehicles found for recommendation"}), 404

    cheapest = rows[0]
    # Find fastest
    def parse_dur(d):
        m = re.findall(r"(\d+)h", str(d))
        hours = int(m[0]) if m else 10
        m2 = re.findall(r"(\d+)m", str(d))
        mins = int(m2[0]) if m2 else 0
        return hours * 60 + mins

    fastest = min(rows, key=lambda r: parse_dur(r["duration"]))

    return jsonify({
        "cheapest_option": {
            "vehicle": cheapest["name"],
            "number": cheapest["number"],
            "fare": cheapest["price"],
            "transport": cheapest["transport"],
            "duration": cheapest["duration"],
            "reason": f"Most affordable option starting at INR {cheapest['price']}"
        },
        "fastest_option": {
            "vehicle": fastest["name"],
            "number": fastest["number"],
            "fare": fastest["price"],
            "transport": fastest["transport"],
            "duration": fastest["duration"],
            "reason": f"Quickest transit time of {fastest['duration']}"
        }
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting SmartTravel Flask Service on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)