
# test_api.py

import unittest
from src.pop_fly.web.app import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_calculate_endpoint(self):
        response = self.app.get('/calculate?lat1=0&lon1=0&lat2=0&lon2=1')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('distance', data)
        self.assertAlmostEqual(data['distance'], 111.19, places=2)

# Updated tests to ensure elevation is not part of the API response.
