"""Bounded browser preview for the existing Canvas Agent, with no model call."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess


def preview_custom_visual(*, source: str, parameters: dict[str, object]) -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(['node', str(root / 'scripts/preview_custom_visual.cjs')],
            input=json.dumps({'source': source, 'parameters': parameters}), text=True,
            capture_output=True, timeout=25, cwd=root, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('CUSTOM_VISUAL_PREVIEW_UNAVAILABLE') from exc
    if result.returncode or len(result.stdout) > 4_000_000:
        raise ValueError('CUSTOM_VISUAL_PREVIEW_FAILED')
    payload = json.loads(result.stdout)
    if payload.get('status') != 'RENDERED' or not 2 <= len(payload.get('views', [])) <= 3:
        raise ValueError('CUSTOM_VISUAL_PREVIEW_INVALID')
    return payload
