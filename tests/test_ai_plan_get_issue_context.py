import os
import importlib.util
import sys
import unittest


# Import the module under test by path to avoid executing main()
MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "ai_plan_issue.py")
spec = importlib.util.spec_from_file_location("ai_plan_issue", MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load module spec from {MODULE_PATH}")
ai_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ai_mod
spec.loader.exec_module(ai_mod)  # type: ignore


class TestGetIssueContext(unittest.TestCase):
    def setUp(self) -> None:
        # Clear relevant env vars to simulate dry-run defaults
        self._saved = {}
        for k in ("GITHUB_REPOSITORY", "GITHUB_EVENT_PATH", "ISSUE_NUMBER"):
            self._saved[k] = os.environ.pop(k, None)

    def tearDown(self) -> None:
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                # If the variable did not exist before the test, ensure it's removed
                os.environ.pop(k, None)

    def test_dry_run_defaults_to_unknown_issue(self):
        issue_number, owner, repo = ai_mod.get_issue_context(dry_run=True)
        self.assertEqual(issue_number, 0)
        self.assertIsNone(owner)
        self.assertIsNone(repo)

    def test_respects_issue_number_env(self):
        os.environ["ISSUE_NUMBER"] = "123"
        issue_number, owner, repo = ai_mod.get_issue_context(dry_run=True)
        self.assertEqual(issue_number, 123)
        self.assertIsNone(owner)
        self.assertIsNone(repo)


if __name__ == "__main__":
    unittest.main()
