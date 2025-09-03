"""
Generates a structured plan for a new feature based on a high-level request,
leveraging an AI to create the plan.

This script is intended to be called by a GitHub workflow. It requires the
OPENAI_API_KEY environment variable to be set.
"""
import argparse
import json
import os
import pathlib
import sys
from typing import Any, Dict


MODEL = os.environ.get("PLAN_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """
You are an expert software architect. Produce a minimal, surgical implementation plan for a feature.

You will receive repository constraints and a scope profile (allowed files, budgets). Treat these as non-negotiable.

Your plan must be Markdown with sections:
1. Goal
2. File Changes (only in the allowed files; for each, list exact functions to edit and approximate line ranges)
3. Testing (list exact assertions to change/remove and why)
4. Risks
5. Out of scope (explicitly restate forbidden changes from the profile)

Budget: do not exceed the profile's max files/lines. If you cannot meet it, explain why and stop (no expanded scope).
"""


def list_project_structure(root: pathlib.Path) -> str:
    """Lists the project structure as a string, ignoring common temporary directories."""
    lines = ["Project Structure:"]
    ignore_dirs = {".git", ".venv", "__pycache__", ".vscode", "node_modules", "dist"}
    
    paths = sorted(
        [p for p in root.rglob("*") if not any(part in p.parts for part in ignore_dirs)]
    )

    for path in paths:
        try:
            depth = len(path.relative_to(root).parts) - 1
            indent = "    " * depth
            prefix = "📁" if path.is_dir() else "📄"
            lines.append(f"{indent}{prefix} {path.name}")
        except ValueError:
            continue # Skips files that are not under the root
            
    return "\n".join(lines)


def call_llm(prompt: str) -> str:
    """Calls the OpenAI API to get a completion."""
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        return (
            "No LLM key configured. Skipping plan generation.\n"
            "Set OPENAI_API_KEY secret to enable."
        )

    try:
        import requests
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    data: Dict[str, Any] = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    response = requests.post(url, headers=headers, json=data, timeout=180)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def load_policy(root: pathlib.Path) -> dict:
    policy_path = root / ".github" / "automation_policy.json"
    try:
        import json
        return json.loads(policy_path.read_text(encoding="utf-8"))
    except Exception:
        return {"invariants": {}, "profiles": {"minor": {"allowed_files": [], "max_files": 4, "max_lines": 80}}}


def generate_plan(feature_request: str, plan_file: pathlib.Path, project_root: pathlib.Path, profile: str = "minor"):
    """
    Generates a structured markdown plan using an AI.

    Args:
        feature_request: The high-level feature request from the user.
        plan_file: The path to the output plan file.
        project_root: The root directory of the project.
    """
    policy = load_policy(project_root)
    inv = policy.get("invariants", {})
    prof = policy.get("profiles", {}).get(profile, {})
    project_structure = list_project_structure(project_root)
    policy_snippet = json.dumps({"invariants": inv, "profile": prof}, indent=2)
    prompt = (
        f"Feature Request: \"{feature_request}\"\n\n"
        f"Repository constraints and scope profile (JSON):\n{policy_snippet}\n\n"
        f"{project_structure}"
    )
    
    plan_content = call_llm(prompt)

    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text(plan_content)
    print(f"Generated AI plan for '{feature_request}' at {plan_file}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Generate a feature plan using AI.")
    parser.add_argument("--request", type=str, required=True, help="High-level feature request.")
    parser.add_argument("--output", type=str, required=True, help="Output file for the plan.")
    parser.add_argument("--profile", type=str, default="minor", choices=["minor", "moderate", "major"], help="Scope profile to use.")
    args = parser.parse_args()

    plan_file = pathlib.Path(args.output)
    project_root = pathlib.Path(__file__).parent.parent # Assumes script is in scripts/
    generate_plan(args.request, plan_file, project_root, args.profile)


if __name__ == "__main__":
    main()
