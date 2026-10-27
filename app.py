"""
SmartTravel - Train & Bus Ticket Booking System
Root Entry Point for VS Code on Windows / Mac / Linux

Usage:
    python app.py
    or
    python run.py

Then open your browser to:
    http://127.0.0.1:5000
"""
import os
import sys
import importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "TrainBusBooking")

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Auto-initialize database if not created yet
try:
    from database import create_database
    create_database()
except Exception as e:
    print(f"[SmartTravel] Database check notice: {e}")

# Safely import Flask app from TrainBusBooking/app.py without circular import
spec = importlib.util.spec_from_file_location("trainbus_app", os.path.join(APP_DIR, "app.py"))
trainbus_app = importlib.util.module_from_spec(spec)
sys.modules["trainbus_app"] = trainbus_app
spec.loader.exec_module(trainbus_app)

app = trainbus_app.app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🚆 SmartTravel - Train & Bus Ticket Booking System (Demo)")
    print(f"🚀 Running locally at: http://127.0.0.1:{port}")
    print("📋 Demo Accounts:")
    print("   • User:  aditi123@gmail.com / 123456")
    print("   • Admin: admin@smarttravel.com / admin123")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
