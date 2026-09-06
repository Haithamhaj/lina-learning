"""Retain complete verification output and real child exit status for this task."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
label, *command = sys.argv[1:]
child_cwd = ROOT
if command[:1] == ['--web-cwd']:
    command = command[1:]
    child_cwd = ROOT / 'apps' / 'web'
if not label.replace('-', '').isalnum() or not command:
    raise SystemExit('Expected a new alphanumeric label and a command')
output = ROOT / 'output' / 'number-line-implementation-20260906'
output.mkdir(parents=True, exist_ok=True)
result_path = output / f'{label}.json'
if result_path.exists():
    raise SystemExit('Evidence label already exists')
with (output / f'{label}.stdout').open('x') as stdout, (output / f'{label}.stderr').open('x') as stderr:
    result = subprocess.run(command, cwd=child_cwd, stdout=stdout, stderr=stderr)
result_path.write_text(json.dumps({'command': command, 'cwd': str(child_cwd), 'child_exit': result.returncode, 'wrapper_exit': result.returncode}, indent=2) + '\n')
print(json.dumps({'label': label, 'child_exit': result.returncode, 'result': str(result_path)}))
raise SystemExit(result.returncode)
