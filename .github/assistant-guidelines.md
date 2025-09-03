# Assistant Execution Guidelines — Prefer Small, Verifiable Steps

Purpose
- Capture the user's request to favor quality over speed when running multi-step automation (especially PowerShell) and to prefer breaking complex operations into small, testable steps.
- This document will be referenced by the assistant when editing scripts, running terminal commands, or writing workflows for this repository.

Core rules

1. Break work into small, explicit steps
- When automating multi-stage tasks, split them into separate commands or script blocks that are executed and verified one-by-one.
- Example (PowerShell): run `git checkout -b <branch>` as a distinct step, then `git add`, then `git commit`, then `git push` — do not chain with `||` or `&&` in a single line.

2. Verify and fail fast
- After each step, check its result before continuing. If a step fails, stop and report the exact failure and the relevant logs.
- Prefer explicit checks (exit codes, `git status --porcelain`, presence of files) to infer success.

3. Prefer idempotent, repeatable operations
- Make each step safe to re-run. For example, create a branch only if it doesn't exist; use `git checkout -B` when resetting is acceptable; check for staged changes before committing.

4. Use clear, single-purpose script args
- Scripts should accept small, well-documented arguments (e.g., `--branch`, `--plan-path`). This makes it easier to call them piecewise and test them independently.

5. Use environment validation and short-circuiting
- Validate important environment assumptions up-front (e.g., that `.venv` exists, `OPENAI_API_KEY` present, `GITHUB_REPOSITORY` set). If a precondition is missing, stop with a helpful message.

6. Avoid complex one-liners in PowerShell
- PowerShell's parsing differs from bash. Avoid `||` and `&&` chaining. Use `if`/`else` blocks, or separate statements. Favor readability over crammed efficiency.

7. Create human-readable checkpoints and artifacts
- After substantial steps (plan generation, file application, test run), produce a small artifact (e.g., markdown summary, json diff) or print a short summary so a maintainer can review progress.

8. Keep automation conservative and auditable
- Limit the default scope of automated write actions (e.g., restrict to `src/`, `tests/`, `scripts/`, `frontend/`). Do not perform deletes or broad sweeping changes without an explicit, reviewed opt-in.

9. Provide a dry-run mode
- Where feasible, add a `--dry-run` flag that prints planned actions (file creations/updates) without applying them. This is the default for new or risky automation when requested.

10. Prefer machine-readable contracts for tool outputs
- When integrating LLMs, prefer structured outputs (JSON or function-call style) so the runner can deterministically apply changes. If human readability is desired, request both a markdown summary and the structured payload.

PowerShell patterns and examples

- Good (explicit, stepwise):

```powershell
# 1) create branch only if missing
if (-not (git rev-parse --verify feature/my-branch 2>$null)) {
    git checkout -b feature/my-branch
} else {
    git checkout feature/my-branch
}

# 2) stage changes
git add -A

# 3) commit only if there are staged changes
if (git status --porcelain) {
    git commit -m "chore: scaffolded changes"
    git push -u origin feature/my-branch
} else {
    Write-Output "No changes to commit"
}
```

- Avoid this (fragile chained one-liner):

```powershell
# BAD: uses bash-style chaining and is hard to debug in PowerShell
git checkout -b feature/my-branch || git checkout feature/my-branch; git add -A; git commit -m "msg" || echo "no changes"; git push
```

LLM usage guidance

- Always include a system prompt that defines the schema you expect (JSON schema or function-call signature).
- Prefer small context windows first: include only the plan and a concise repo structure summary. If more context is required, iterate rather than asking for the whole repo in one call.
- Sanitize and validate any model output before applying to disk: parse JSON, strip markup fences, validate paths against allowed directories, and check for suspicious content.

Issue comment safeguards

- Before posting an automation-triggering comment (for example `/plan` or `/implement`), read the issue's recent comments and skip posting if any of the following are true:
  - A recent comment (last 24 hours) is exactly `/plan` or `/implement`.
  - A recent comment contains the string `Automated plan (` indicating the workflow already produced a plan.
- Debounce: if the assistant itself posted a `/plan` within the last 2 minutes, do not post again automatically.
- Single-responsibility: post at most one trigger comment per issue unless explicitly asked to retry; wait for the workflow result and show the maintainer the generated plan before re-triggering.
- When a skip occurs, post a single informative comment (once) explaining why the trigger was skipped and what the user can do to force a rerun (for example, add a comment `force:/plan` or re-run the workflow).
- When posting a trigger comment, include the repository and issue link in the log for traceability and record the timestamp in action logs.

Minimal pseudocode for the behavior:

```
# fetch last N comments for issue
if any(comment.body == "/plan" and comment.created_at > now - 24h) or any("Automated plan (" in comment.body):
    post_once("Skipped posting /plan because a recent plan or trigger already exists. Reply 'force:/plan' to re-run.")
else if this_agent_posted_within(issue, minutes=2):
    log("Debounce: recently posted /plan; skipping")
else:
    post("/plan")
    log("Posted /plan on issue #$NUM")
```

Environment and dependencies

- Prefer installing dependencies once in the developer environment rather than calling `pip` at runtime in automation scripts. Add required packages to `requirements-dev.txt` and instruct CI to install them.
- If a script must install packages at runtime (very rare), it must only do so in an isolated, ephemeral environment and log the operation.

Checklist the assistant will follow (every multi-step action)

- [ ] Validate environment and secrets (venv, tokens)
- [ ] Break the task into 2–6 atomic steps
- [ ] Run each step, capture output and errors
- [ ] Produce a short checkpoint artifact / log after each major step
- [ ] If changes are applied, commit and push in a small, descriptive commit
- [ ] Create or update a PR with a clear title and body summarizing changes

How I will reference this

- When you ask me to perform automation, I will follow these rules and (unless you say otherwise) prefer stepwise execution and optional dry-run first.
- If you prefer a faster single-line approach for any particular step, say so explicitly and I will do it for that step only.

Documentation editing rules (Markdown)

- Scope
    - Default docs to edit are `README.md` and `PRD.md` unless otherwise requested.
    - Prefer targeted, section-level changes; do not rewrite entire documents.

- Allowed operations (mirror automation in `scripts/generate_docs.py`)
  - replace_section(heading, content)
  - append_to_section(heading, content)
  - upsert_section(heading, level=2..6, content)
  - replace_block_by_marker(name, content) using markers `<!-- AUTO-DOC:NAME -->` and `<!-- /AUTO-DOC:NAME -->`
  - Operate only on unique headings; if ambiguous, skip or create a new section via upsert.

- Constraints and safety checks
    - Max 6 ops per file in a single update; split larger updates across separate commits/PRs.
    - Preserve heading text and hierarchy; maintain surrounding blank lines and code-fence integrity.
    - Don’t reduce a file by >40% in a single change; large deletions need human review.
    - Keep relative links and anchors stable; update them only when the target actually changed.
    - Use Windows-friendly PowerShell examples where relevant to this repo; one command per line.

- Review artifacts
    - Produce a concise unified diff in PRs or logs; surface any warnings like missing markers or non-unique headings.
    - When applicable, validate against `docs/schema/docs_ops.json` and ensure structured outputs parse cleanly.