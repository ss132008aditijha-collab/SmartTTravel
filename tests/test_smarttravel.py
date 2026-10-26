import unittest
import os
import sys

# Ensure application is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "TrainBusBooking"))

from app import app, get_db_connection
from pdf_generator import generate_ticket_pdf


class SmartTravelTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_home_page_loads(self):
        """Verify home page loads with 200 OK"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SmartTravel", response.data)

    def test_train_search_results(self):
        """Verify searching trains returns valid matching schedules"""
        response = self.client.get("/search?transport=train&source=Bengaluru&destination=Chennai")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Karnataka Superfast Express", response.data)
        self.assertIn(b"3A", response.data)

    def test_bus_search_results(self):
        """Verify searching buses returns AC / Non-AC categories"""
        response = self.client.get("/search?transport=bus&source=Bengaluru&destination=Chennai")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"IntrCity SmartBus Premium", response.data)
        self.assertIn(b"AC BUS", response.data)

    def test_booking_overview_page(self):
        """Verify booking overview page renders with class details"""
        response = self.client.get("/booking?name=Karnataka+Express&number=12627&price=1120&transport=train&source=Bengaluru&destination=Chennai&date=2026-10-30&class=3A")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Boarding", response.data)

    def test_seat_selection_page(self):
        """Verify seat and berth layout renders for train classes"""
        response = self.client.get("/seat-selection?name=Karnataka+Express&number=12627&price=1120&transport=train&source=Bengaluru&destination=Chennai&date=2026-10-30&class=3A+(AC+3+Tier)")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Coach Berth Map", response.data)

    def test_complete_booking_workflow(self):
        """Verify end-to-end booking insertion into database"""
        payload = {
            "name": "Karnataka Superfast Express",
            "number": "12627",
            "price": "1120",
            "transport": "train",
            "source": "Bengaluru",
            "destination": "Chennai",
            "date": "2026-10-30",
            "boarding": "Bengaluru City Junction (SBC) - Platform 1",
            "seat": "B4-24",
            "vehicle_class": "3A (AC 3 Tier)",
            "quota": "GENERAL",
            "passenger_name": "Test Passenger",
            "age": "25",
            "gender": "Female",
            "phone": "9876543210",
            "email": "test@smarttravel.com",
            "food_total": "180",
            "total": "1300",
            "payment_method": "UPI"
        }

        response = self.client.post("/complete-booking", data=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Reservation Confirmed", response.data)
        self.assertIn(b"Test Passenger", response.data)

    def test_pdf_generation_engine(self):
        """Verify native vector PDF generator produces valid PDF bytes"""
        sample_ticket = {
            "booking_id": "TEST_PNR_999",
            "transport": "train",
            "vehicle_name": "Vande Bharat Express",
            "vehicle_number": "20608",
            "source": "Bengaluru",
            "destination": "Chennai",
            "journey_date": "2026-10-30",
            "boarding": "Platform 1",
            "seat": "C2-14",
            "passenger_name": "Sample Traveller",
            "age": 30,
            "gender": "Male",
            "phone": "9999988888",
            "email": "traveller@smarttravel.com",
            "ticket_price": 890.0,
            "food_total": 0.0,
            "total": 890.0,
            "vehicle_class": "CC (AC Chair Car)",
            "quota": "GENERAL",
            "status": "CONFIRMED"
        }

        pdf_bytes = generate_ticket_pdf(sample_ticket)
        self.assertTrue(len(pdf_bytes) > 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        self.assertTrue(b"%%EOF" in pdf_bytes)

    def test_admin_portal_access(self):
        """Verify admin login portal loads"""
        response = self.client.get("/admin/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Admin Portal Login", response.data)


if __name__ == "__main__":
    unittest.main()
