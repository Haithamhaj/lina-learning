"""Snapshot source hashes, task inventory, Git boundaries, and verification metadata."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = '173968515dc5f5faad24512d520eff112d8d9986'
NEW = [
    'apps/web/components/studio/decimal-number-line-workspace.tsx',
    'apps/web/lib/studio/decimal-number-line.ts',
    'apps/web/lib/studio/decimal-number-line.test.ts',
    'services/studio/subjects/decimal_number_line.py',
    'services/studio/decimal_number_line_activation.py',
    'tests/test_studio_decimal_number_line.py',
    'tests/test_studio_decimal_number_line_postgres.py',
    'scripts/run_number_line_check.py',
    'scripts/number_line_browser_setup.py',
    'scripts/verify_number_line_evidence.py',
    'scripts/number_line_source_manifest.py',
    'tests/test_number_line_browser_preflight.py',
    'docs/MATH_RENDER_NUMBER_LINE_01_IMPLEMENTATION_RECORD.md',
    'docs/MATH_RENDER_NUMBER_LINE_01_ENVIRONMENT_DISPOSITION_ADDENDUM.md',
]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode()


def main():
    label = sys.argv[1]
    assert label.replace('-', '').isalnum()
    output = ROOT / 'output/number-line-implementation-20260906'
    destination = output / f'{label}.manifest.json'
    assert not destination.exists(), 'Use a distinct evidence label'
    tracked = git('diff', '--name-only', BASE).splitlines()
    assert git('rev-parse', 'HEAD').strip() == BASE
    assert git('branch', '--show-current').strip() == 'codex/ctx-03'
    assert git('diff', '--cached', '--name-only') == ''
    forbidden = ('apps/web/app/student/', 'apps/web/components/student/', 'migrations/', 'research/', 'project-state/')
    assert not any(path.startswith(forbidden) for path in tracked)
    assert 'apps/web/app/globals.css' not in tracked
    check = subprocess.run(['git', 'diff', '--check', BASE], cwd=ROOT, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    report = 'docs/MATH_RENDER_NUMBER_LINE_01_IMPLEMENTATION_REVIEW.md'
    new = NEW + ([report] if (ROOT / report).exists() else [])
    whitespace = []
    for name in new:
        for number, line in enumerate((ROOT / name).read_text().splitlines(), 1):
            if line.rstrip() != line:
                whitespace.append(f'{name}:{number}')
    assert not whitespace, whitespace
    paths = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', 'apps', 'services', 'tests', 'scripts').split('\0'))
    extensions = {'.py', '.ts', '.tsx', '.js', '.mjs', '.cjs', '.css', '.json', '.toml', '.sql'}
    paths = sorted(path for path in paths if path and (ROOT / path).is_file() and Path(path).suffix in extensions)
    sources = [{'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), 'bytes': (ROOT / path).stat().st_size} for path in paths]
    suite = ET.parse(output / 'final-python.junit.xml').getroot().find('testsuite')
    skips = [{'class': case.get('classname'), 'test': case.get('name'), 'reason': case.find('skipped').get('message')} for case in suite.findall('testcase') if case.find('skipped') is not None]
    results = {}
    for name in ('final-python', 'final-typecheck', 'final-build', 'final-alembic', 'final-web-compile', 'final-web-tests', 'final-evidence', 'complete-focused-4'):
        results[name] = json.loads((output / f'{name}.json').read_text())
        assert results[name]['child_exit'] == results[name]['wrapper_exit'] == 0
    artifact = {
        'baseline': BASE, 'head': git('rev-parse', 'HEAD').strip(),
        'branch': git('branch', '--show-current').strip(),
        'origin_parity': git('rev-list', '--left-right', '--count', 'HEAD...origin/codex/ctx-03').strip(),
        'index_empty': True, 'tracked_whitespace_exit': check.returncode,
        'task_untracked_whitespace_issues': whitespace,
        'task_changed_tracked': tracked, 'task_new_files': new,
        'task_evidence_directory': str(output.relative_to(ROOT)),
        'complete_git_status': git('status', '--short', '--untracked-files=all'),
        'source_count': len(sources), 'sources': sources,
        'python_suite': dict(suite.attrib), 'skips': skips, 'verified_commands': results,
        'scope': 'Hashes include tracked and nonignored untracked production/test/runner source, not generated evidence, environment files, node_modules, or .acceptance-artifacts. Pre-existing untracked files are inventoried, not claimed as task-owned.',
    }
    destination.write_text(json.dumps(artifact, indent=2) + '\n')
    print(json.dumps({'manifest': str(destination), 'source_count': len(sources), 'tracked_changes': len(tracked), 'task_new_files': len(new), 'skips': skips}, indent=2))


if __name__ == '__main__':
    main()
