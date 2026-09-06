"""Retain complete task evidence and command exit codes without overwriting."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
label, *command = sys.argv[1:]
if not label.replace('-', '').isalnum() or not command:
    raise SystemExit('Expected unique label and command')
out = root / 'output/place-value-implementation-20260907'
out.mkdir(parents=True, exist_ok=True)
with (out / f'{label}.stdout').open('x') as stdout, (out / f'{label}.stderr').open('x') as stderr:
    result = subprocess.run(command, cwd=root, stdout=stdout, stderr=stderr)
wrapper_exit = result.returncode % 256
with (out / f'{label}.json').open('x') as stream:
    json.dump(dict(command=command, child_exit=result.returncode, wrapper_exit=wrapper_exit), stream, indent=2)
print(json.dumps(dict(label=label, exit_code=wrapper_exit, child_exit=result.returncode)))
raise SystemExit(wrapper_exit)
