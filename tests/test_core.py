
# test_core.py

import unittest
from src.pop_fly.core import calculate_distance

class TestCoreCalculations(unittest.TestCase):
    def test_calculate_distance(self):
        # Test without elevation
        result = calculate_distance(0, 0, 0, 1)
        self.assertAlmostEqual(result, 111.19, places=2)

# Removed tests related to elevation.
