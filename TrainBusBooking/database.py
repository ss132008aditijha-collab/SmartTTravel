import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "smarttravel.db")
)


def get_db_connection():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Enable foreign keys in SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # =========================
    # 1. USERS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ensure role and created_at columns exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    # =========================
    # 2. VEHICLES TABLE (Trains & Buses)
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transport TEXT NOT NULL,
            name TEXT NOT NULL,
            number TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure TEXT NOT NULL,
            arrival TEXT NOT NULL,
            duration TEXT NOT NULL,
            price REAL NOT NULL,
            total_seats INTEGER NOT NULL,
            active INTEGER DEFAULT 1,
            rating TEXT DEFAULT '4.8',
            amenities TEXT DEFAULT 'WiFi, Charging Point',
            vehicle_type TEXT DEFAULT 'Superfast',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Verify all vehicles columns
    for col_def in [
        ("rating", "TEXT DEFAULT '4.8'"),
        ("amenities", "TEXT DEFAULT 'WiFi, Charging Point'"),
        ("vehicle_type", "TEXT DEFAULT 'Superfast'"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]:
        try:
            cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col_def[0]} {col_def[1]}")
        except sqlite3.OperationalError:
            pass

    # =========================
    # 3. SEATS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            seat_number TEXT NOT NULL,
            seat_type TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'AVAILABLE',
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
        )
    """)

    # =========================
    # 4. SEAT HOLDS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seat_holds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hold_id TEXT UNIQUE NOT NULL,
            vehicle_number TEXT NOT NULL,
            seat_number TEXT NOT NULL,
            user_email TEXT,
            expires_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'ACTIVE'
        )
    """)

    # =========================
    # 5. BOOKINGS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT UNIQUE NOT NULL,
            transport TEXT,
            vehicle_name TEXT,
            vehicle_number TEXT,
            source TEXT,
            destination TEXT,
            journey_date TEXT,
            boarding TEXT,
            seat TEXT,
            passenger_name TEXT,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            email TEXT,
            ticket_price REAL,
            food_total REAL DEFAULT 0,
            total REAL,
            payment_method TEXT,
            vehicle_class TEXT DEFAULT 'STANDARD',
            quota TEXT DEFAULT 'GENERAL',
            status TEXT DEFAULT 'CONFIRMED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Verify all bookings columns
    for col_def in [
        ("vehicle_class", "TEXT DEFAULT 'STANDARD'"),
        ("quota", "TEXT DEFAULT 'GENERAL'"),
        ("food_total", "REAL DEFAULT 0"),
        ("status", "TEXT DEFAULT 'CONFIRMED'"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]:
        try:
            cursor.execute(f"ALTER TABLE bookings ADD COLUMN {col_def[0]} {col_def[1]}")
        except sqlite3.OperationalError:
            pass

    # =========================
    # 6. PASSENGERS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passengers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            seat_number TEXT NOT NULL,
            berth_pref TEXT,
            id_proof TEXT,
            FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
        )
    """)

    # =========================
    # 7. FOOD ITEMS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            is_veg INTEGER DEFAULT 1,
            available INTEGER DEFAULT 1
        )
    """)

    # =========================
    # 8. FOOD ORDERS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT NOT NULL,
            food_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
        )
    """)

    # =========================
    # 9. PAYMENTS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            transaction_ref TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'SUCCESS',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
        )
    """)

    # =========================
    # 10. AI CONVERSATIONS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_email TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # SEED INITIAL DATA IF EMPTY
    # =========================
    try:
        from werkzeug.security import generate_password_hash
    except ImportError:
        import hashlib
        def generate_password_hash(p):
            return f"sha256:{hashlib.sha256(p.encode()).hexdigest()}"

    # Seed Demo Users if table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        sample_users = [
            ("Aditi", "aditi123@gmail.com", "9876543210", generate_password_hash("123456"), "user"),
            ("SmartTravel Admin", "admin@smarttravel.com", "9998887776", generate_password_hash("admin123"), "admin"),
            ("diya", "diya1234@gmail.com", "9876543211", generate_password_hash("123456"), "user"),
        ]
        cursor.executemany("""
            INSERT INTO users (name, email, phone, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, sample_users)

    # Seed Food Items
    cursor.execute("SELECT COUNT(*) FROM food_items")
    if cursor.fetchone()[0] == 0:
        sample_food = [
            ("South Indian Thali Deluxe", "Meals", "Steamed rice, sambar, rasam, kootu, poriyal, curd, papad & payasam", 180.0, 1, 1),
            ("North Indian Paneer Platter", "Meals", "Paneer butter masala, 2 butter naan, jeera rice, dal makhani & gulab jamun", 210.0, 1, 1),
            ("Hyderabadi Chicken Dum Biryani", "Special", "Authentic slow-cooked spiced biryani with boiled egg, mirchi ka salan & raita", 240.0, 0, 1),
            ("Gourmet Veg Club Sandwich", "Snacks", "Triple-layer multigrain sandwich with grilled veggies, cheese & potato crisps", 110.0, 1, 1),
            ("Hot Masala Chai & Cookies", "Beverages", "Freshly brewed cardamom tea with 2 artisan butter cookies", 45.0, 1, 1),
            ("Mineral Water Bottle (1L)", "Beverages", "Chilled packaged drinking water bottle", 20.0, 1, 1)
        ]
        cursor.executemany("""
            INSERT INTO food_items (name, category, description, price, is_veg, available)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_food)

    # Seed Vehicles
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    if cursor.fetchone()[0] == 0:
        sample_vehicles = [
            ("train", "Vande Bharat Express", "20608", "Bengaluru", "Chennai", "05:45", "10:15", "4h 30m", 890.0, 52, 1, "4.9", "Free WiFi, Onboard Meals, 180 Rotating Seats", "Semi-High Speed"),
            ("train", "Karnataka Superfast Express", "12627", "Bengaluru", "Chennai", "19:20", "06:00", "10h 40m", 650.0, 38, 1, "4.7", "Pantry Car, Charging Point, Bedrolls", "Superfast Express"),
            ("train", "Chennai Mail Express", "12608", "Bengaluru", "Chennai", "22:30", "07:00", "8h 30m", 720.0, 28, 1, "4.5", "Clean Linens, Reading Lamp, Pantry Car", "Mail / Express"),
            ("train", "Shatabdi Express", "12028", "Bengaluru", "Chennai", "06:00", "11:00", "5h 00m", 850.0, 44, 1, "4.8", "Complimentary Snacks, Newspaper, Water", "Shatabdi"),
            ("train", "Bangalore Rajdhani Superfast", "22691", "Bengaluru", "Delhi", "20:00", "05:30", "33h 30m", 2450.0, 20, 1, "4.9", "Gourmet Catering, Bedrolls, Attendant", "Rajdhani"),
            ("train", "Deccan Queen Express", "12124", "Pune", "Mumbai", "07:15", "10:25", "3h 10m", 450.0, 42, 1, "4.7", "Dining Car, Vista Coach, Speed Guard", "Superfast"),
            ("train", "Pink City Superfast Express", "12986", "Delhi", "Jaipur", "06:05", "10:35", "4h 30m", 560.0, 32, 1, "4.6", "AC Chair Car, Snacks, Charging Point", "Intercity Express"),
            ("bus", "IntrCity SmartBus Premium A/C Sleeper", "KA-51-AA-9988", "Bengaluru", "Chennai", "23:00", "06:45", "7h 45m", 950.0, 16, 1, "4.9", "Sanitized Washroom, Personal TV, AC Berths", "Scania A/C Sleeper (2+1)"),
            ("bus", "KSRTC Airavat Club Class Multi-Axle", "KA-01-F-1234", "Bengaluru", "Chennai", "21:30", "06:30", "9h 00m", 850.0, 24, 1, "4.8", "Air Suspension, Calf Rest, Water, Blankets", "Volvo Multi-Axle (2+2)"),
            ("bus", "Zingbus Electric Superfast Sleeper", "KA-04-EV-2026", "Bengaluru", "Chennai", "22:15", "06:15", "8h 00m", 880.0, 18, 1, "4.7", "Zero Emission, Fast USB-C, Silent Ride", "Electric AC Sleeper (2+1)"),
            ("bus", "Sharma Transports Non-AC Sleeper", "KA-02-S-4433", "Bengaluru", "Chennai", "21:00", "06:00", "9h 00m", 580.0, 22, 1, "4.3", "Sliding Windows, Reading Lamp, Fan", "Non-AC Sleeper (2+1)"),
            ("bus", "KSRTC Rajahamsa Executive Seater", "KA-05-CD-5678", "Bengaluru", "Chennai", "20:00", "05:30", "9h 30m", 520.0, 32, 1, "4.4", "Highback Recliners, First Aid, Luggage Bay", "Non-AC Pushback (2+2)"),
            ("bus", "SRS Travels Volvo A/C Multi-Axle", "KA-04-B-4321", "Bengaluru", "Hyderabad", "21:00", "06:30", "9h 30m", 920.0, 22, 1, "4.6", "Climate Control AC, Reading Lights, GPS", "Volvo Multi-Axle (2+2)"),
            ("bus", "VRL Travels I-Shift Multi-Axle", "MH-12-Q-5544", "Mumbai", "Pune", "06:30", "10:15", "3h 45m", 480.0, 35, 1, "4.6", "Air Suspension, Charging Port, Pushback", "Volvo Semi-Sleeper (2+2)")
        ]
        cursor.executemany("""
            INSERT INTO vehicles (transport, name, number, source, destination, departure, arrival, duration, price, total_seats, active, rating, amenities, vehicle_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_vehicles)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_database()
    print("SmartTravel database created, migrated, and seeded successfully!")