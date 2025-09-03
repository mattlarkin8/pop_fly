import os
import importlib.util
import sys
import tempfile
import json
import unittest


# Import module by path to avoid executing main()
MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "ai_plan_issue.py")
spec = importlib.util.spec_from_file_location("ai_plan_issue", MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load module spec from {MODULE_PATH}")
ai_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ai_mod
spec.loader.exec_module(ai_mod)  # type: ignore


class TestParseEventIssue(unittest.TestCase):
    def test_none_path_returns_none(self):
        self.assertIsNone(ai_mod._parse_event_issue(None))

    def test_valid_event_returns_issue_number(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            data = {"issue": {"number": 77}}
            json.dump(data, f)
            path = f.name
        try:
            val = ai_mod._parse_event_issue(path)
            self.assertEqual(val, 77)
        finally:
            os.unlink(path)

    def test_event_without_issue_returns_none(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            data = {"action": "opened"}
            json.dump(data, f)
            path = f.name
        try:
            val = ai_mod._parse_event_issue(path)
            self.assertIsNone(val)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
