import io
import json
import os
import tempfile
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pop_fly import cli


class TestCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        os.environ["POP_FLY_CONFIG_DIR"] = self.td.name
        super().setUp()

    def tearDown(self) -> None:
        self.td.cleanup()
        os.environ.pop("POP_FLY_CONFIG_DIR", None)
        super().tearDown()

    def run_cli(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(argv)
        return code, buf.getvalue().strip()

    def test_set_start_and_compute_plain(self):
        code, _ = self.run_cli(["--set-start", "00000,00000"])  # origin
        self.assertEqual(code, 0)
        code, out = self.run_cli(["--end", "03000 00000", "--precision", "1"])  # 3km east
        self.assertEqual(code, 0)
        self.assertIn("Distance:", out)
        self.assertIn("Azimuth:", out)
        self.assertNotIn("ΔZ:", out)

    def test_reject_three_value_inputs(self):
        # set-start with 3 values should error
        code, out = self.run_cli(["--set-start", "00000,00000,5"])  
        self.assertEqual(code, 2)
        self.assertIn("Expected 'E N'", out)
        # compute with 3-value end should error
        self.assertEqual(self.run_cli(["--set-start", "00000,00000"])[0], 0)
        code, out = self.run_cli(["--end", "00000 00000 25"]) 
        self.assertEqual(code, 2)
        self.assertIn("Expected 'E N'", out)

    def test_json_output(self):
        self.assertEqual(self.run_cli(["--set-start", "00000 00000"])[0], 0)
        code, out = self.run_cli(["--end", "03000 00000", "--json", "--precision", "0"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["format"], "mgrs-digits")
        self.assertEqual(data["start"], [0.0, 0.0])
        self.assertEqual(data["end"], [3000.0, 0.0])
        self.assertEqual(data["distance_m"], 3000)
        self.assertNotIn("slant_distance_m", data)
        self.assertNotIn("delta_z_m", data)

    def test_faction_flag(self):
        self.assertEqual(self.run_cli(["--set-start", "00000 00000"])[0], 0)
        # NATO 3km east = 1600 mils
        code, out = self.run_cli(["--end", "03000 00000", "--json", "--faction", "nato"])        
        self.assertEqual(code, 0)
        nato = json.loads(out)
        self.assertEqual(nato["azimuth_mils"], 1600.0)
        self.assertEqual(nato["faction"], "nato")
        # RU 3km east = 1500 mils
        code, out = self.run_cli(["--end", "03000 00000", "--json", "--faction", "ru"])        
        self.assertEqual(code, 0)
        ru = json.loads(out)
        self.assertEqual(ru["azimuth_mils"], 1500.0)
        self.assertEqual(ru["faction"], "ru")

    def test_persisted_faction(self):
        # Persist start and faction then run without --faction
        self.assertEqual(self.run_cli(["--set-start", "00000 00000"])[0], 0)
        self.assertEqual(self.run_cli(["--set-faction", "ru"])[0], 0)
        code, out = self.run_cli(["--end", "03000 00000", "--json"])  # 3km east
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["faction"], "ru")
        self.assertEqual(data["azimuth_mils"], 1500.0)
        # Override with CLI arg
        code, out = self.run_cli(["--end", "03000 00000", "--json", "--faction", "nato"])  # override
        self.assertEqual(code, 0)
        data2 = json.loads(out)
        self.assertEqual(data2["faction"], "nato")
        self.assertEqual(data2["azimuth_mils"], 1600.0)


if __name__ == "__main__":
    unittest.main()
