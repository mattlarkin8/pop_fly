import math
import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pop_fly.core import compute_distance_bearing_xy


class TestCore(unittest.TestCase):
    def test_basic_cardinals(self):
        # North
        r = compute_distance_bearing_xy((0, 0), (0, 100))
        self.assertAlmostEqual(r.distance_m, 100.0, places=6)
        self.assertAlmostEqual(r.azimuth_mils, 0.0, places=6)

        # East
        r = compute_distance_bearing_xy((0, 0), (100, 0))
        self.assertAlmostEqual(r.distance_m, 100.0, places=6)
        self.assertAlmostEqual(r.azimuth_mils, 1600.0, places=6)

        # South
        r = compute_distance_bearing_xy((0, 0), (0, -100))
        self.assertAlmostEqual(r.distance_m, 100.0, places=6)
        self.assertAlmostEqual(r.azimuth_mils, 3200.0, places=6)

        # West
        r = compute_distance_bearing_xy((0, 0), (-100, 0))
        self.assertAlmostEqual(r.distance_m, 100.0, places=6)
        self.assertAlmostEqual(r.azimuth_mils, 4800.0, places=6)

    def test_zero_distance(self):
        r = compute_distance_bearing_xy((10, 10), (10, 10))
        self.assertEqual(r.distance_m, 0.0)
        self.assertAlmostEqual(r.azimuth_mils, 0.0, places=6)

    def test_faction_ru_vs_nato(self):
        # East direction bearing 90 deg should be 1600 NATO, 1500 RU
        nato = compute_distance_bearing_xy((0,0), (100,0), faction="nato")
        ru = compute_distance_bearing_xy((0,0), (100,0), faction="ru")
        self.assertAlmostEqual(nato.azimuth_mils, 1600.0, places=6)
        self.assertAlmostEqual(ru.azimuth_mils, 1500.0, places=6)
        self.assertEqual(nato.faction, "nato")
        self.assertEqual(ru.faction, "ru")

    def test_reject_three_value_pairs(self):
        with self.assertRaises(ValueError):
            compute_distance_bearing_xy((0, 0, 10), (3000, 0))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            compute_distance_bearing_xy((0, 0), (3000, 0, 20))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
