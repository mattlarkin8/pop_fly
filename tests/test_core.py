import math
import unittest

from mortar_calc.core import compute_distance_bearing_xy


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

    def test_with_elevation(self):
        r = compute_distance_bearing_xy((0, 0, 10), (3000, 0, 20))
        self.assertAlmostEqual(r.distance_m, 3000.0, places=6)
        self.assertAlmostEqual(r.azimuth_mils, 1600.0, places=6)
        self.assertIsNotNone(r.slant_distance_m)
        self.assertIsNotNone(r.delta_z_m)
        self.assertAlmostEqual(r.delta_z_m or 0.0, 10.0, places=6)
        self.assertAlmostEqual(r.slant_distance_m or 0.0, math.sqrt(3000**2 + 10**2), places=6)


if __name__ == "__main__":
    unittest.main()
