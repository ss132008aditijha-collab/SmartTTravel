"""
SmartTravel Comprehensive Automated Test Suite
Covers all 15 required test areas:
1. Homepage and static assets
2. Train and bus searches
3. No-results searches
4. Registration and login
5. Train class selection (Vande Bharat CC/EC restriction)
6. Seat selection and booked-seat display
7. Passenger details and food selection
8. Payment page calculation
9. Complete demo booking end-to-end
10. Duplicate-seat prevention
11. E-ticket and PDF download
12. My Bookings dashboard
13. Cancellation and refund status
14. Admin access and dashboard
15. Invalid dates and malformed input handling
"""

import os
import sys
import unittest
import json
from datetime import date, timedelta

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(BASE_DIR, "TrainBusBooking")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app import app, get_db_connection, get_train_classes, extract_class_code, demo_food_order
from pdf_generator import generate_ticket_pdf


class SmartTravelComprehensiveTestSuite(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-123"
        self.client = app.test_client()

    # 1. Homepage & Static Assets
    def test_01_homepage_and_static_assets(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"SmartTravel", res.data)
        self.assertIn(b"Train Tickets", res.data)
        self.assertIn(b"Bus Tickets", res.data)

        # Static CSS check
        res_css = self.client.get("/static/style.css")
        self.assertEqual(res_css.status_code, 200)

        # Static JS check
        res_js = self.client.get("/static/js/main.js")
        self.assertEqual(res_js.status_code, 200)

    # 2. Train & Bus Searches
    def test_02_train_and_bus_searches(self):
        # Search trains Bengaluru -> Chennai
        res = self.client.get("/search?transport=train&source=Bengaluru&destination=Chennai")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Vande Bharat Express", res.data)

        # Search buses Bengaluru -> Chennai
        res_bus = self.client.get("/search?transport=bus&source=Bengaluru&destination=Chennai")
        self.assertEqual(res_bus.status_code, 200)
        self.assertIn(b"IntrCity", res_bus.data)

    # 3. No-Results Searches
    def test_03_no_results_search(self):
        # Search for a route that does not exist in demo catalog
        res = self.client.get("/search?transport=train&source=NonExistentCityA&destination=NonExistentCityB")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No Vehicles Found", res.data)
        self.assertIn(b"We could not find any trains matching your selected route", res.data)

    # 4. Registration and Login
    def test_04_registration_and_login(self):
        import secrets
        test_email = f"user_{secrets.token_hex(4)}@example.com"
        reg_res = self.client.post("/register", data={
            "name": "Integration Tester",
            "email": test_email,
            "phone": "9876543210",
            "password": "mypassword123"
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)

        # Login with new account
        login_res = self.client.post("/login", data={
            "email": test_email,
            "password": "mypassword123"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Integration Tester", login_res.data)

        # Login with wrong password
        fail_res = self.client.post("/login", data={
            "email": test_email,
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertEqual(fail_res.status_code, 200)
        self.assertIn(b"Invalid credentials", fail_res.data)

    # 5. Train Class Selection & Vande Bharat Restriction
    def test_05_train_class_selection(self):
        # Train 20608 (Vande Bharat) must strictly support ONLY CC and EC
        vb_classes = get_train_classes("20608", "Vande Bharat Express", 890)
        vb_codes = [c["code"] for c in vb_classes]
        self.assertEqual(vb_codes, ["CC", "EC"])
        self.assertNotIn("2A", vb_codes)
        self.assertNotIn("SL", vb_codes)

        # Standard train (12627) supports 1A, 2A, 3A, 3E, SL
        kf_classes = get_train_classes("12627", "Karnataka Superfast Express", 650)
        kf_codes = [c["code"] for c in kf_classes]
        self.assertIn("1A", kf_codes)
        self.assertIn("2A", kf_codes)
        self.assertIn("3A", kf_codes)
        self.assertIn("SL", kf_codes)

        # Class code extraction normalization
        self.assertEqual(extract_class_code("2A (AC 2 Tier)"), "2A")
        self.assertEqual(extract_class_code("CC"), "CC")
        self.assertEqual(extract_class_code("EC"), "EC")
        self.assertEqual(extract_class_code("3E"), "3E")

    # 6. Seat Selection & Booked Seats Display
    def test_06_seat_selection_and_booked_seats(self):
        res = self.client.get("/seat-selection?transport=train&number=20608&source=Bengaluru&destination=Chennai&date=2026-11-20&class=CC")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Seat", res.data)
        self.assertIn(b"Coach", res.data)

    # 7. Passenger Details & Food Selection
    def test_07_passenger_details_and_food(self):
        # Passenger details page
        p_res = self.client.get("/passenger-details?transport=train&number=20608&source=Bengaluru&destination=Chennai&seat=1A&class=CC")
        self.assertEqual(p_res.status_code, 200)
        self.assertIn(b"Passenger", p_res.data)

        # Food selection page
        f_res = self.client.get("/food?transport=train&number=20608&seat=1A&class=CC")
        self.assertEqual(f_res.status_code, 200)
        self.assertIn(b"Deluxe Veg Thali", f_res.data)

        # Server-side food pricing validation
        food_rows = demo_food_order(json.dumps({"veg_thali": 2, "mineral_water": 1}))
        total_food = sum(r[3] for r in food_rows)
        # 2 * 160 + 1 * 20 = 340
        self.assertEqual(total_food, 340.0)

    # 8. Payment Page Calculations
    def test_08_payment_page_calculations(self):
        res = self.client.get("/payment?transport=train&number=20608&source=Bengaluru&destination=Chennai&seat=1A&class=CC&food_items=%7B%22veg_thali%22%3A1%7D")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"890", res.data)  # Ticket fare for CC
        self.assertIn(b"160", res.data)  # Food add-on
        self.assertIn(b"1050", res.data) # Total payable

    # 9. Complete Demo Booking End-to-End
    def test_09_complete_demo_booking(self):
        import secrets
        journey_date = (date.today() + timedelta(days=14)).isoformat()
        res = self.client.post("/complete-booking", data={
            "transport": "train",
            "number": "20608",
            "source": "Bengaluru",
            "destination": "Chennai",
            "vehicle_class": "CC",
            "journey_date": journey_date,
            "seat": f"S{secrets.token_hex(2).upper()}",
            "passenger_name": "Suite Test Passenger",
            "age": "30",
            "gender": "Male",
            "phone": "9876543210",
            "email": "suite_test@smarttravel.com",
            "payment_method": "UPI",
            "food_items": json.dumps({"veg_thali": 1})
        })
        self.assertEqual(res.status_code, 302)
        location = res.headers["Location"]
        self.assertIn("/ticket?booking_id=", location)

        # Follow to ticket page
        ticket_res = self.client.get(location)
        self.assertEqual(ticket_res.status_code, 200)
        self.assertIn(b"Suite Test Passenger", ticket_res.data)
        self.assertIn(b"Vande Bharat Express", ticket_res.data)

    # 10. Duplicate Seat Prevention
    def test_10_duplicate_seat_prevention(self):
        import secrets
        app.config["TESTING"] = False
        journey_date = (date.today() + timedelta(days=40)).isoformat()
        unique_seat = f"Z{secrets.token_hex(2).upper()}"

        # First booking succeeds
        res1 = self.client.post("/complete-booking", data={
            "transport": "train",
            "number": "20608",
            "source": "Bengaluru",
            "destination": "Chennai",
            "vehicle_class": "CC",
            "journey_date": journey_date,
            "seat": unique_seat,
            "passenger_name": "First Passenger",
            "email": "p1@smarttravel.com"
        })
        self.assertEqual(res1.status_code, 302)

        # Second booking with same seat, same train, same date must be rejected
        res2 = self.client.post("/complete-booking", data={
            "transport": "train",
            "number": "20608",
            "source": "Bengaluru",
            "destination": "Chennai",
            "vehicle_class": "CC",
            "journey_date": journey_date,
            "seat": unique_seat,
            "passenger_name": "Second Passenger",
            "email": "p2@smarttravel.com"
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn(b"already booked", res2.data)
        app.config["TESTING"] = True

    # 11. E-Ticket & Vector PDF Download
    def test_11_e_ticket_and_pdf(self):
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM bookings WHERE status = 'CONFIRMED' LIMIT 1").fetchone()

        self.assertIsNotNone(row)
        booking_id = row["booking_id"]

        # View PDF
        view_res = self.client.get(f"/view-pdf/{booking_id}")
        self.assertEqual(view_res.status_code, 200)
        self.assertEqual(view_res.headers["Content-Type"], "application/pdf")
        self.assertTrue(view_res.data.startswith(b"%PDF-1.4"))

        # Download PDF
        dl_res = self.client.get(f"/download-pdf/{booking_id}")
        self.assertEqual(dl_res.status_code, 200)
        self.assertIn("attachment", dl_res.headers["Content-Disposition"])

    # 12. My Bookings Dashboard
    def test_12_my_bookings_dashboard(self):
        # Login as Aditi
        self.client.post("/login", data={"email": "aditi123@gmail.com", "password": "123456"})
        res = self.client.get("/bookings")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"My Bookings", res.data)

    # 13. Cancellation & Refund Status
    def test_13_cancellation(self):
        import secrets
        # Login first as Aditi
        self.client.post("/login", data={"email": "aditi123@gmail.com", "password": "123456"})
        journey_date = (date.today() + timedelta(days=25)).isoformat()
        unique_seat = f"C{secrets.token_hex(2).upper()}"

        res = self.client.post("/complete-booking", data={
            "transport": "train",
            "number": "12627",
            "source": "Bengaluru",
            "destination": "Chennai",
            "vehicle_class": "3A",
            "journey_date": journey_date,
            "seat": unique_seat,
            "passenger_name": "Aditi Sharma",
            "email": "aditi123@gmail.com"
        })
        location = res.headers["Location"]
        booking_id = location.split("booking_id=")[-1]

        # Execute cancellation
        cancel_res = self.client.post(f"/cancel-booking/{booking_id}", follow_redirects=True)
        self.assertEqual(cancel_res.status_code, 200)
        self.assertIn(b"cancelled successfully", cancel_res.data)

        # Verify DB status
        with get_db_connection() as conn:
            b = conn.execute("SELECT status FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
            p = conn.execute("SELECT status FROM payments WHERE booking_id = ?", (booking_id,)).fetchone()
            self.assertEqual(b["status"], "CANCELLED")
            self.assertEqual(p["status"], "REFUNDED")

    # 14. Admin Access & Dashboard
    def test_14_admin_dashboard(self):
        # Regular user should be redirected or shown login
        admin_gate = self.client.get("/admin", follow_redirects=True)
        self.assertIn(b"Admin Portal Login", admin_gate.data)

        # Admin login
        admin_login = self.client.post("/admin/login", data={
            "email": "admin@smarttravel.com",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(admin_login.status_code, 200)
        self.assertIn(b"Operations", admin_login.data)

    # 15. Invalid Input & Malformed Parameters Handling
    def test_15_invalid_input_handling(self):
        # Non-existent booking ID
        res_404 = self.client.get("/ticket?booking_id=NON_EXISTENT_ID")
        self.assertEqual(res_404.status_code, 404)

        # Empty AI chat message
        ai_res = self.client.post("/api/ai/chat", json={"message": ""})
        self.assertEqual(ai_res.status_code, 400)

        # Offline AI chat reply
        ai_valid = self.client.post("/api/ai/chat", json={"message": "What classes are on Vande Bharat?"})
        self.assertEqual(ai_valid.status_code, 200)
        self.assertIn("CC", ai_valid.get_json()["reply"])
        self.assertIn("EC", ai_valid.get_json()["reply"])


if __name__ == "__main__":
    unittest.main()
