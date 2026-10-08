"""Run official tests, agent tests, live validation, packager and archive checker."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--kit',required=True,type=Path)
p.add_argument('--matches-per-side',type=int,default=2)
args=p.parse_args(); kit=args.kit.resolve()
reports=ROOT/'reports'; reports.mkdir(exist_ok=True)
dist=ROOT/'dist'; dist.mkdir(exist_ok=True)

def run(arguments,cwd=ROOT,filename=None,env=None):
    process=subprocess.run([sys.executable,*arguments],cwd=cwd,capture_output=True,text=True,env=env)
    output=process.stdout+process.stderr
    print(output,flush=True)
    if filename: (reports/filename).write_text(output,encoding='utf-8')
    if process.returncode: raise SystemExit(process.returncode)

run(['-m','unittest','discover','-s','tests','-v'],kit,'official_tests.txt')
environment=dict(os.environ); environment['CONVCUP_KIT']=str(kit)
run(['-m','unittest','discover','-s','tests','-v'],ROOT,'agent_tests.txt',environment)
run(['validate_submission.py','--submission',str(ROOT/'submission'/'submission.json'),
     '--matches-per-side',str(args.matches_per_side)],kit,'process_validation.txt')
archive=dist/'Torpedo_United_Submission.zip'
run(['package_submission.py',str(ROOT/'submission'),str(archive)],kit,'packaging.txt')
run(['check_submission.py',str(archive),'--report',str(reports/'static_check.json')],kit,'static_check.txt')
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(dist/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
print('Submission is validated:',archive)
