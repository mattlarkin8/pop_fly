import unittest

from fastapi.testclient import TestClient

from mortar_calc.web.app import app


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

    def test_compute_xy_only(self):
        payload = {"start": [0, 0], "end": [3000, 0], "precision": 0}
        r = self.client.post("/api/compute", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["format"], "xy")
        self.assertEqual(data["distance_m"], 3000)
        self.assertEqual(data["azimuth_mils"], 1600.0)
        self.assertNotIn("slant_distance_m", data)
        self.assertNotIn("delta_z_m", data)

    def test_compute_with_z(self):
        payload = {"start": [0, 0, 10], "end": [3000, 0, 20], "precision": 0}
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


if __name__ == "__main__":
    unittest.main()
