import os
import sys
import subprocess
import shutil
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "ai_plan_issue.py")


def _run_dry_run_env(extra_env=None):
    env = os.environ.copy()
    # Ensure dry-run mode and no tokens set
    env.pop("GITHUB_TOKEN", None)
    env.pop("GITHUB_REPOSITORY", None)
    env.pop("OPENAI_API_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)
    env["DRY_RUN"] = "1"
    if extra_env:
        env.update(extra_env)
    # Run the script using the same Python interpreter running the tests
    return subprocess.run([sys.executable, SCRIPT, "--dry-run"], env=env, capture_output=True, text=True)


class TestAIPlanIssueDryRun(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = os.path.join(ROOT, "tmp", "ai-plan-dryrun")
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def tearDown(self) -> None:
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_writes_default_issue_file_when_no_issue_env(self):
        """When no ISSUE_NUMBER or event is provided, dry-run should still write issue-0-plan.txt"""
        res = _run_dry_run_env()
        self.assertEqual(res.returncode, 0, msg=f"Stdout: {res.stdout}\nStderr: {res.stderr}")
        out_file = os.path.join(self.tmp_dir, "issue-0-plan.txt")
        self.assertTrue(os.path.exists(out_file), msg=res.stdout + res.stderr)
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Automated plan", content)

    def test_writes_issue_file_for_provided_issue_number(self):
        """If ISSUE_NUMBER is provided it should be used in the dry-run filename"""
        res = _run_dry_run_env({"ISSUE_NUMBER": "42"})
        self.assertEqual(res.returncode, 0, msg=f"Stdout: {res.stdout}\nStderr: {res.stderr}")
        out_file = os.path.join(self.tmp_dir, "issue-42-plan.txt")
        self.assertTrue(os.path.exists(out_file), msg=res.stdout + res.stderr)
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Automated plan", content)


if __name__ == "__main__":
    unittest.main()
