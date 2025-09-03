import importlib.util
import os
import sys
import types
import unittest
from unittest import mock


# Import module by path to avoid executing main()
MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "ai_plan_issue.py")
spec = importlib.util.spec_from_file_location("ai_plan_issue", MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load module spec from {MODULE_PATH}")
ai_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ai_mod
spec.loader.exec_module(ai_mod)  # type: ignore


class TestEnsurePyGithub(unittest.TestCase):
    def tearDown(self) -> None:
        # Clean up any fake github module we injected and reset ai_mod.Github
        sys.modules.pop("github", None)
        setattr(ai_mod, "Github", None)

    def test_installs_and_imports_when_missing(self):
        # Ensure starting state has no Github
        setattr(ai_mod, "Github", None)

        # Create a fake 'github' module with a Github symbol
        fake_module = types.ModuleType("github")

        class DummyGithub:
            pass

        setattr(fake_module, "Github", DummyGithub)
        sys.modules["github"] = fake_module

        called = {}

        def fake_check_call(argv):
            # Record the call and don't actually run pip
            called["argv"] = list(argv)

        with mock.patch("subprocess.check_call", side_effect=fake_check_call):
            ai_mod.ensure_pygithub()

        # verify subprocess.check_call was invoked with pip install
        self.assertIn("-m", called["argv"])
        self.assertIn("pip", called["argv"])
        self.assertTrue(any("PyGithub" in str(x) for x in called["argv"]))

        # Github global should now reference our DummyGithub class
        self.assertIs(getattr(ai_mod, "Github"), DummyGithub)

    def test_noop_if_github_already_set(self):
        sentinel = object()
        setattr(ai_mod, "Github", sentinel)

        def fail_if_called(*args, **kwargs):
            raise AssertionError("subprocess.check_call should not be called when Github is set")

        with mock.patch("subprocess.check_call", side_effect=fail_if_called):
            ai_mod.ensure_pygithub()

        self.assertIs(getattr(ai_mod, "Github"), sentinel)


if __name__ == "__main__":
    unittest.main()
