"""Durable verification wrapper using the existing guarded test environment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.test_postgres import test_environment, test_database_url

OUT = Path(__file__).resolve().parent
mode = sys.argv[1]
env = test_environment(test_database_url())
env["PYTHONPATH"] = str(ROOT)
env["PYTEST_ADDOPTS"] = "--junitxml=" + str(OUT / (mode + ".xml"))
if mode.startswith("full"):
    # Existing runner, externally managed disposable database: no reset/cleanup.
    env["LINA_TEST_DATABASE_MANAGED_EXTERNALLY"] = "1"
    command = [sys.executable, "scripts/test_postgres.py", "test"]
elif mode == "alembic":
    command = [sys.executable, "-m", "alembic", "check"]
elif mode == "build":
    command = ["npm", "--prefix", "apps/web", "run", "build"]
elif mode == "typecheck":
    command = ["npm", "--prefix", "apps/web", "run", "typecheck"]
elif mode == "web":
    command = ["npx", "--offline", "tsx", "--test", *sorted(str(p.relative_to(ROOT)) for p in (ROOT/"apps/web/lib").rglob("*.test.ts"))]
else:
    command = [sys.executable, "-m", "pytest", "-q", *sys.argv[2:]]
paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
sources = sorted({p for p in paths if p.startswith(("apps/", "services/", "tests/", "scripts/")) or p.startswith("output/playwright/arabic-acceptance-20260906/") and p.endswith((".py", ".js", ".cjs"))})
manifest = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources if (ROOT / p).is_file()}
(OUT / (mode + "-source.json")).write_text(json.dumps(manifest, indent=2) + "\n")
with (OUT / (mode + ".log")).open("w") as log:
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
summary = {"command":command,"wrapper_exit":result.returncode,"pytest_exit":None,"source_manifest":mode+"-source.json"}
if mode not in ("alembic", "build", "typecheck", "web"):
    import xml.etree.ElementTree as ET
    xml = OUT / (mode + ".xml")
    if xml.exists():
        suites = list(ET.parse(xml).getroot().iter("testsuite"))
        summary["junit"] = {key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ("tests","failures","errors","skipped")}
        summary["pytest_exit"] = result.returncode if not mode.startswith("full") else (0 if result.returncode == 0 else "see CalledProcessError in wrapper log")
(OUT / (mode + "-result.json")).write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
raise SystemExit(result.returncode)
