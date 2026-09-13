"""Isolated production-browser verification; no model, learner or storage authority."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess

from services.studio.full_power_canvas import CanvasSemanticBridge, CanvasSemanticManifestV1


def preview_custom_visual(*, source: str, parameters: dict[str, object], manifest: CanvasSemanticManifestV1 | None = None) -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    payload = {'source': source, 'parameters': parameters,
               'widths': [960, 640],
               'interactions': [] if manifest is None else [item.model_dump(mode='json') for item in manifest.interactions]}
    process = None
    try:
        process = subprocess.Popen(['node', str(root / 'scripts/preview_custom_visual.cjs')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=root, start_new_session=True)
        stdout, stderr = process.communicate(json.dumps(payload), timeout=25)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('CUSTOM_VISUAL_PREVIEW_UNAVAILABLE') from exc
    finally:
        if process is not None:
            # Kill the entire private browser process group, including an unresponsive
            # renderer. No worker/browser cache or cross-owner process is retained.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    if process.returncode or len(stdout) > 4_000_000:
        raise ValueError('CUSTOM_VISUAL_PREVIEW_FAILED')
    try:
        result = json.loads(stdout)
        if result.get('status') not in {'RENDERED', 'FAILED'} or not 2 <= len(result.get('views', [])) <= 6:
            raise ValueError()
    except (TypeError, ValueError) as error:
        raise ValueError('CUSTOM_VISUAL_PREVIEW_INVALID') from error
    if manifest is not None:
        known_state = {item.semantic_id for item in manifest.interactions if item.action not in {'SELECT', 'FOCUS'}}
        # The private parser resolves literal/const identifiers with lexical scope.
        # Dynamic reads remain covered by actual event/replay validation.
        state_ids = {item["semantic_id"] for item in result.get("state_reads", [])}
        for state_id in sorted(state_ids - known_state):
            result['views'][0].setdefault('findings', []).append(
                f"State read ID {state_id[:120]} has no value-bearing interaction; use the exact emitted semantic ID.")
        bridge = CanvasSemanticBridge(manifest=manifest, artifact_instance_id='preview-instance', nonce='preview-nonce')
        for check in result.get('checks', []):
            if check.get('action') != 'EVENT_AUDIT':
                continue
            for index, event in enumerate(check.pop('events', [])):
                try:
                    bridge.validate({
                        'version': 'canvas-semantic-event-v1', 'artifact_instance_id': 'preview-instance',
                        'nonce': 'preview-nonce', 'idempotency_key': f'preview-{index}',
                        **{key: event.get(key) for key in ('semantic_action', 'semantic_id', 'from_value', 'to_value')},
                    })
                    if event.get('semantic_action') in {'SELECT', 'FOCUS'} and event.get('to_value') is not None:
                        raise ValueError()
                except (TypeError, ValueError):
                    action, semantic_id = event.get('semantic_action'), event.get('semantic_id')
                    declared = {(item.action, item.semantic_id) for item in manifest.interactions}
                    if action not in {item.action for item in manifest.interactions}:
                        detail = "Unknown action. Use bridge.emit(action, semantic_id, {to_value: string}), or bound handle.emit(value); bridge.emit(semantic_id, value) is invalid."
                    elif (action, semantic_id) not in declared:
                        detail = "Action and semantic ID must match one declared Manifest interaction."
                    elif any(isinstance(event.get(key), str) and len(event[key]) > 240 for key in ('from_value', 'to_value')):
                        detail = "Event values exceed 240 characters; emit compact semantic state."
                    else:
                        detail = "Value does not meet the declared interaction contract; SELECT/FOCUS carry no value and required mutation values must be strings."
                    result['views'][0].setdefault('findings', []).append(
                        f"Invalid semantic event: {str(action)[:64]}:{str(semantic_id)[:64]}. {detail}")
    return result
