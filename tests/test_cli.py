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

    def test_with_z_signed_delta(self):
        self.assertEqual(self.run_cli(["--set-start", "00000,00000,5"])[0], 0)
        code, out = self.run_cli(["--end", "00000 00000 25", "--precision", "0"])  # 20 m up
        self.assertEqual(code, 0)
        self.assertIn("ΔZ: +20 m", out)

    def test_json_output(self):
        self.assertEqual(self.run_cli(["--set-start", "00000 00000 0"])[0], 0)
        code, out = self.run_cli(["--end", "03000 00000 10", "--json", "--precision", "0"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["format"], "mgrs-digits")
        self.assertEqual(data["start"], [0.0, 0.0, 0.0])
        self.assertEqual(data["end"], [3000.0, 0.0, 10.0])
        self.assertEqual(data["distance_m"], 3000)
        self.assertIn("slant_distance_m", data)
        self.assertIn("delta_z_m", data)
        self.assertAlmostEqual(data["delta_z_m"], 10.0, places=6)


if __name__ == "__main__":
    unittest.main()
