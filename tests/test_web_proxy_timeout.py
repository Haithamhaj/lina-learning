"""Production Next proxy timeout contract for buffered Tutor SSE."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_next_proxy_timeout_allows_buffered_tutor_turns_beyond_default_30_seconds() -> None:
    script = "import cfg from './apps/web/next.config.mjs'; console.log(JSON.stringify(cfg.experimental ?? {}))"
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    experimental = json.loads(completed.stdout)
    assert experimental.get("proxyTimeout") == 180_000
