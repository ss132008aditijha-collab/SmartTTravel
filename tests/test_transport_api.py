import unittest
import os
import sys
import json
from unittest.mock import patch

# Ensure project is importable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "TrainBusBooking"))

from app import app
from train_api import (
    resolve_station_code,
    search_trains_between_stations,
    get_train_live_status,
    _API_CACHE
)
from bus_api import (
    search_buses_between_cities,
    _BUS_API_CACHE
)


class TransportApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        _API_CACHE.clear()
        _BUS_API_CACHE.clear()

    def test_station_code_resolution(self):
        """Test Indian Railways station code mapping"""
        self.assertEqual(resolve_station_code("Bengaluru"), "SBC")
        self.assertEqual(resolve_station_code("Chennai"), "MAS")
        self.assertEqual(resolve_station_code("Delhi"), "NDLS")
        self.assertEqual(resolve_station_code("Mumbai"), "CSTM")
        self.assertEqual(resolve_station_code("Pune"), "PUNE")
        # Direct station code preservation
        self.assertEqual(resolve_station_code("HWH"), "HWH")

    def test_train_search_contract(self):
        """Verify train search response adheres to normalized schema contract"""
        result = search_trains_between_stations("Bengaluru", "Chennai", "2026-10-30")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("provider", result)
        self.assertIn("is_live", result)
        self.assertIn("data", result)
        self.assertTrue(len(result["data"]) > 0)

        first_train = result["data"][0]
        self.assertIn("train_number", first_train)
        self.assertIn("train_name", first_train)
        self.assertIn("classes", first_train)
        self.assertIn("amenities", first_train)

    def test_train_api_caching(self):
        """Verify repeated searches within TTL return cached=True"""
        res1 = search_trains_between_stations("Bengaluru", "Chennai", "2026-10-30")
        self.assertFalse(res1.get("cached", False))

        res2 = search_trains_between_stations("Bengaluru", "Chennai", "2026-10-30")
        self.assertTrue(res2.get("cached", False))

    def test_bus_search_contract(self):
        """Verify bus search response adheres to normalized schema contract"""
        result = search_buses_between_cities("Bengaluru", "Chennai", "2026-10-30")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("provider", result)
        self.assertIn("is_live", result)
        self.assertIn("data", result)
        self.assertTrue(len(result["data"]) > 0)

        first_bus = result["data"][0]
        self.assertIn("operator_name", first_bus)
        self.assertIn("bus_number", first_bus)
        self.assertIn("bus_type", first_bus)
        self.assertIn("fare", first_bus)
        self.assertIn("decks", first_bus)

    @patch("train_api._http_get")
    def test_train_api_mocked_live_success(self, mock_http):
        """Test RailKit live provider response parsing with mock"""
        mock_http.return_value = (200, {
            "status": "success",
            "data": [
                {
                    "number": "20608",
                    "name": "Live Vande Bharat Express",
                    "departure_time": "05:45",
                    "arrival_time": "10:15",
                    "duration": "4h 30m",
                    "min_fare": 890,
                    "classes": [{"code": "CC", "name": "AC Chair Car", "fare": 890, "available_seats": 20}]
                }
            ]
        })

        with patch("train_api.RAILKIT_API_KEY", "mock_live_token_123"):
            _API_CACHE.clear()
            res = search_trains_between_stations("Bengaluru", "Chennai", "2026-10-30")
            self.assertTrue(res["is_live"])
            self.assertEqual(res["provider"], "RailKit Live API")
            self.assertEqual(res["data"][0]["train_number"], "20608")

    @patch("train_api._http_get")
    def test_train_api_mocked_network_error_fallback(self, mock_http):
        """Test graceful fallback to verified DB on live API connection failure"""
        mock_http.return_value = (503, {"error": "RailKit Server Unavailable"})

        with patch("train_api.RAILKIT_API_KEY", "mock_live_token_123"):
            _API_CACHE.clear()
            res = search_trains_between_stations("Bengaluru", "Chennai", "2026-10-30")
            # Should not crash, should fall back to verified database
            self.assertEqual(res["status"], "SUCCESS")
            self.assertFalse(res["is_live"])
            self.assertEqual(res["provider"], "SmartTravel Verified Database (Demo)")

    def test_live_running_status_tracker(self):
        """Verify train running status endpoint"""
        status = get_train_live_status("12627")
        self.assertEqual(status["status"], "SUCCESS")
        self.assertIn("data", status)
        self.assertIn("current_status", status["data"])
        self.assertIn("last_reported_station", status["data"])

    def test_flask_transport_rest_endpoints(self):
        """Verify all new Flask JSON REST endpoints"""
        # Providers endpoint
        resp_prov = self.client.get("/api/transport/providers")
        self.assertEqual(resp_prov.status_code, 200)
        data_prov = json.loads(resp_prov.data)
        self.assertIn("providers", data_prov)
        self.assertIn("railkit_train", data_prov["providers"])

        # Trains search API
        resp_train = self.client.get("/api/trains/search?source=Bengaluru&destination=Chennai")
        self.assertEqual(resp_train.status_code, 200)

        # Train live status API
        resp_live = self.client.get("/api/trains/live-status?train_number=12627")
        self.assertEqual(resp_live.status_code, 200)

        # Buses search API
        resp_bus = self.client.get("/api/buses/search?source=Bengaluru&destination=Chennai")
        self.assertEqual(resp_bus.status_code, 200)

    def test_demo_booking_reference_generation_format(self):
        """Verify demo booking IDs never generate fake IRCTC PNRs and use ST-DEMO format"""
        payload = {
            "name": "Karnataka Superfast Express",
            "number": "12627",
            "price": "1120",
            "transport": "train",
            "source": "Bengaluru",
            "destination": "Chennai",
            "date": "2026-10-30",
            "boarding": "Platform 1",
            "seat": "B4-24",
            "vehicle_class": "3A (AC 3 Tier)",
            "quota": "GENERAL",
            "passenger_name": "Demo Passenger",
            "age": "26",
            "gender": "Female",
            "phone": "9876543210",
            "email": "demo@smarttravel.com",
            "food_total": "0",
            "total": "1120",
            "payment_method": "UPI"
        }

        response = self.client.post("/complete-booking", data=payload, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        redirect_url = response.headers.get("Location", "")

        # Must contain ST-DEMO-TRN and MUST NOT contain IRCTC
        self.assertIn("ST-DEMO-TRN-", redirect_url)
        self.assertNotIn("IRCTC", redirect_url)


if __name__ == "__main__":
    unittest.main()
