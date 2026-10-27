import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "TrainBusBooking"))

from app import app, get_db_connection, get_train_classes, verify_password
from werkzeug.security import check_password_hash


class FixesVerificationTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_vande_bharat_classes_are_only_cc_and_ec(self):
        """CRITICAL: Train 20608 (Vande Bharat) must only return CC and EC"""
        classes = get_train_classes("20608", "Vande Bharat Express", 890.0)
        class_codes = [c["code"] for c in classes]
        self.assertEqual(class_codes, ["CC", "EC"])
        self.assertNotIn("2A", class_codes)
        self.assertNotIn("3A", class_codes)
        self.assertNotIn("1A", class_codes)
        self.assertNotIn("SL", class_codes)

        # Verify prices
        cc_class = next(c for c in classes if c["code"] == "CC")
        ec_class = next(c for c in classes if c["code"] == "EC")
        self.assertEqual(cc_class["price"], 890)
        self.assertEqual(ec_class["price"], 1650)

    def test_vande_bharat_booking_flow(self):
        """Verify end-to-end booking of Train 20608 with valid CC class"""
        # 1. Overview page
        resp_overview = self.client.get(
            "/booking?name=Vande+Bharat+Express&number=20608&price=890&transport=train&source=Bengaluru&destination=Chennai&date=2026-11-15&class=CC"
        )
        self.assertEqual(resp_overview.status_code, 200)
        self.assertIn(b"Vande Bharat Express", resp_overview.data)
        self.assertIn(b"CC", resp_overview.data)
        self.assertIn(b"EC", resp_overview.data)

        # 2. Seat selection page
        resp_seats = self.client.get(
            "/seat-selection?name=Vande+Bharat+Express&number=20608&price=890&transport=train&source=Bengaluru&destination=Chennai&date=2026-11-15&class=CC"
        )
        self.assertEqual(resp_seats.status_code, 200)
        self.assertIn(b"Coach Berth Map", resp_seats.data)

        # 3. Complete booking
        payload = {
            "name": "Vande Bharat Express",
            "number": "20608",
            "price": "890",
            "transport": "train",
            "source": "Bengaluru",
            "destination": "Chennai",
            "date": "2026-11-15",
            "boarding": "Bengaluru City Junction (SBC) - Platform 1",
            "seat": "1A",
            "vehicle_class": "CC",
            "quota": "GENERAL",
            "passenger_name": "Aditi Sharma",
            "age": "24",
            "gender": "Female",
            "phone": "9876543210",
            "email": "aditi123@gmail.com",
            "food_total": "160",
            "total": "1050",
            "payment_method": "UPI"
        }
        resp_complete = self.client.post("/complete-booking", data=payload, follow_redirects=True)
        self.assertEqual(resp_complete.status_code, 200)
        self.assertIn(b"Vande Bharat Express", resp_complete.data)
        self.assertIn(b"CC", resp_complete.data)
        self.assertIn(b"Aditi Sharma", resp_complete.data)

    def test_legacy_account_compatibility_aditi(self):
        """Verify legacy plaintext account 'aditi123@gmail.com' / '123456' logs in and upgrades"""
        resp = self.client.post("/login", data={
            "email": "aditi123@gmail.com",
            "password": "123456"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Verify password hash was upgraded in the database
        with get_db_connection() as conn:
            user = conn.execute("SELECT password FROM users WHERE email = 'aditi123@gmail.com'").fetchone()
            self.assertTrue(user["password"].startswith("scrypt:") or user["password"].startswith("pbkdf2:"))
            self.assertTrue(check_password_hash(user["password"], "123456"))

    def test_legacy_admin_login(self):
        """Verify admin account 'admin@smarttravel.com' / 'admin123' logs in successfully"""
        resp = self.client.post("/admin/login", data={
            "email": "admin@smarttravel.com",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"SmartTravel Operations Center", resp.data)

    def test_forgot_and_reset_password_flow(self):
        """Verify forgot password and reset password flow"""
        # Step 1: Submit email
        resp_forgot = self.client.post("/forgot-password", data={
            "email": "diya1234@gmail.com"
        }, follow_redirects=False)
        self.assertEqual(resp_forgot.status_code, 302)
        self.assertIn("reset-password", resp_forgot.headers["Location"])

        # Step 2: Reset password
        resp_reset = self.client.post("/reset-password?email=diya1234@gmail.com", data={
            "password": "newpassword123",
            "confirm_password": "newpassword123"
        }, follow_redirects=True)
        self.assertEqual(resp_reset.status_code, 200)
        self.assertIn(b"Password reset successfully", resp_reset.data)

        # Step 3: Login with new password
        resp_login = self.client.post("/login", data={
            "email": "diya1234@gmail.com",
            "password": "newpassword123"
        }, follow_redirects=True)
        self.assertEqual(resp_login.status_code, 200)

    def test_cancellation_flow(self):
        """Verify booking cancellation updates status to CANCELLED"""
        # Create a booking first
        payload = {
            "name": "Karnataka Superfast Express",
            "number": "12627",
            "price": "1120",
            "transport": "train",
            "source": "Bengaluru",
            "destination": "Chennai",
            "date": "2026-12-01",
            "boarding": "Platform 1",
            "seat": "B4-11",
            "vehicle_class": "3A",
            "quota": "GENERAL",
            "passenger_name": "Cancel Test",
            "age": "28",
            "gender": "Male",
            "phone": "9876543210",
            "email": "canceltest@smarttravel.com",
            "payment_method": "UPI"
        }
        resp = self.client.post("/complete-booking", data=payload, follow_redirects=False)
        location = resp.headers.get("Location", "")
        booking_id = location.split("booking_id=")[-1]
        self.assertTrue(booking_id.startswith("ST-DEMO-TRN-"))

        # Now cancel the booking via POST
        cancel_resp = self.client.post(f"/cancel-booking/{booking_id}", follow_redirects=True)
        self.assertEqual(cancel_resp.status_code, 200)

        # Check DB status
        with get_db_connection() as conn:
            row = conn.execute("SELECT status FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
            self.assertEqual(row["status"], "CANCELLED")


if __name__ == "__main__":
    unittest.main()
