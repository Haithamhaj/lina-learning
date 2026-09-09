#!/usr/bin/env python3
"""Small deterministic hygiene checks for the repository truth structure."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ["README.md", "AGENTS.md", "TASKS.md", "docs/README.md", "docs/PROJECT_REFERENCE.md", "docs/IMPLEMENTATION_PLAN.md", "docs/LEARNING_PRODUCT_ROADMAP.md", "docs/LEARNING_INTELLIGENCE_SPEC.md", "docs/CHILD_SAFETY_POLICY.md", "project-state/PROJECT_STATE.md", "project-state/SYSTEM_MAP.html"]
errors = []
for relative in CANONICAL:
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"missing canonical file: {relative}")
        continue
    start = path.read_text(encoding="utf-8").lstrip()[:120].upper()
    if start.startswith("# HISTORICAL") or start.startswith("# REFERENCE ONLY"):
        errors.append(f"canonical file is marked historical: {relative}")
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        target = target.split("#", 1)[0]
        if target and not target.startswith(("http://", "https://", "mailto:")) and not (path.parent / target).exists():
            errors.append(f"unresolved canonical link: {relative} -> {target}")
state_files = {path.name for path in (ROOT / "project-state").iterdir() if path.is_file()}
if state_files != {"PROJECT_STATE.md", "SYSTEM_MAP.html"}:
    errors.append(f"unexpected project-state files: {sorted(state_files)}")
if (ROOT / "TASKS.md").stat().st_size >= 20_000:
    errors.append("TASKS.md is not compact (<20 KB required)")
for directory in ("docs/history", "docs/reviews", "research"):
    text = (ROOT / directory / "README.md").read_text(encoding="utf-8").lower()
    if "non-authoritative" not in text:
        errors.append(f"{directory} is not explicitly non-authoritative")
for relative in ("README.md", "docs/PROJECT_REFERENCE.md", "docs/IMPLEMENTATION_PLAN.md", "docs/LEARNING_PRODUCT_ROADMAP.md", "project-state/PROJECT_STATE.md"):
    text = (ROOT / relative).read_text(encoding="utf-8").lower()
    for phrase in ("voice input / stt", "vision as not implemented", "canvas foundation as future/frozen"):
        if phrase in text:
            errors.append(f"obsolete capability wording in {relative}: {phrase}")
    if "codex/ctx-03" in text:
        errors.append(f"shadow canonical branch named in {relative}")
if "output/" not in (ROOT / ".gitignore").read_text(encoding="utf-8"):
    errors.append("output/ is not ignored")
tracked_output = subprocess.run(["git", "ls-files", "output"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
if tracked_output:
    errors.append("files under output/ are tracked")
if errors:
    print("REPOSITORY TRUTH CHECK: FAIL")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)
print("REPOSITORY TRUTH CHECK: PASS")
