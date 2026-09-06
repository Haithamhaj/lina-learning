"""Read-only source/status inventory; writes only this run's evidence files."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
tracked=subprocess.check_output(["git","diff","--name-only"],cwd=ROOT,text=True).splitlines()
untracked=subprocess.check_output(["git","ls-files","--others","--exclude-standard"],cwd=ROOT,text=True).splitlines()
task=sorted(set(tracked+[p for p in untracked if "arabic" in p or "STUDIO_ACT_AR_01" in p]))
source=[p for p in task if Path(p).suffix in (".py",".ts",".tsx",".js",".cjs",".md")]
hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source}
(OUT/"source-manifest.json").write_text(json.dumps(hashes,indent=2)+"\n")
(OUT/"task-inventory.json").write_text(json.dumps({"tracked":tracked,"task_owned":task},indent=2)+"\n")
status=subprocess.check_output(["git","status","--short","--untracked-files=all"],cwd=ROOT,text=True)
(OUT/"local-git-status.txt").write_text(status)
issues=[]
for path in source:
    for number,line in enumerate((ROOT/path).read_text().splitlines(),1):
        if line.rstrip()!=line: issues.append(f"{path}:{number}: trailing whitespace")
check=subprocess.run(["git","diff","--check"],cwd=ROOT,capture_output=True,text=True)
(OUT/"whitespace.json").write_text(json.dumps({"tracked_exit":check.returncode,"tracked_output":check.stdout+check.stderr,"task_source_issues":issues},indent=2)+"\n")
print(json.dumps({"tracked":len(tracked),"task_paths":len(task),"source_hashes":len(hashes),"whitespace_issues":issues,"tracked_whitespace_exit":check.returncode}))
