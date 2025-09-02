import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient

from pop_fly.web.app import app


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_version(self):
        r = self.client.get("/api/version")
        self.assertEqual(r.status_code, 200)
        self.assertIn("version", r.json())

    def test_compute_mgrs_digits_only(self):
        payload = {"start": ["00000", "00000"], "end": ["03000", "00000"], "precision": 0}
        r = self.client.post("/api/compute", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["format"], "mgrs-digits")
        self.assertEqual(data["distance_m"], 3000)
        self.assertEqual(data["azimuth_mils"], 1600.0)
        self.assertNotIn("slant_distance_m", data)
        self.assertNotIn("delta_z_m", data)

    def test_compute_with_z(self):
        payload = {"start": ["00000", "00000", 10], "end": ["03000", "00000", 20], "precision": 0}
        r = self.client.post("/api/compute", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["distance_m"], 3000)
        self.assertIn("slant_distance_m", data)
        self.assertIn("delta_z_m", data)
        self.assertEqual(data["delta_z_m"], 10)

    def test_invalid_input(self):
        payload = {"start": [0], "end": [1, 2]}
        r = self.client.post("/api/compute", json=payload)
        self.assertEqual(r.status_code, 422)  # pydantic validation error

    def test_cli_vs_api_parity_example(self):
        # Example from report: start "021,032" end "084,069" should be 7306 m
        payload = {"start": ["021", "032"], "end": ["084", "069"], "precision": 0}
        r = self.client.post("/api/compute", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["distance_m"], 7306)


if __name__ == "__main__":
    unittest.main()
