"""
SmartTravel - Direct Runner Script
Usage:
    python run.py
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "TrainBusBooking")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app import app, get_db_connection

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🚆 SmartTravel - Train & Bus Ticket Booking System")
    print(f"🚀 Running locally at: http://127.0.0.1:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
