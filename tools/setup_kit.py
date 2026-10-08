"""Fetch the exact official development kit used for validation (not submitted)."""
import argparse
import subprocess
from pathlib import Path

COMMIT='3e66ba1f9bb12a9d75b8de02d92a4394e6c352d3'
URL='https://github.com/Anukul1712/Mlfootball_env.git'
p=argparse.ArgumentParser()
p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parents[1]/'vendor'/'official')
args=p.parse_args(); destination=args.directory.resolve()
if destination.exists():
    raise SystemExit('Destination already exists; use a new directory to avoid changing local work.')
destination.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['git','clone',URL,str(destination)],check=True)
subprocess.run(['git','checkout','--detach',COMMIT],cwd=destination,check=True)
actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=destination,text=True).strip()
if actual!=COMMIT: raise SystemExit('Official revision verification failed')
print('Official participant kit:',destination/'participants')
