#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shlex, subprocess
from datetime import datetime, timezone
from pathlib import Path

def sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def now() -> str: return datetime.now(timezone.utc).isoformat()

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--work",required=True); p.add_argument("--evidence",required=True); p.add_argument("--stage",required=True); p.add_argument("--software",required=True); p.add_argument("--input",action="append",default=[]); p.add_argument("--output",action="append",default=[]); p.add_argument("--env",action="append",default=[]); p.add_argument("command",nargs=argparse.REMAINDER); a=p.parse_args()
    cmd=list(a.command); cmd=cmd[1:] if cmd and cmd[0]=="--" else cmd
    if not cmd: raise SystemExit("recorded stage requires a command after --")
    work=Path(a.work).resolve(); evidence=Path(a.evidence).resolve(); env=os.environ.copy()
    for assignment in a.env:
        key,sep,value=assignment.partition("=")
        if not sep or not key: raise SystemExit(f"invalid --env assignment: {assignment}")
        env[key]=value
    inputs={n:sha256(work/n) for n in a.input}; started=now(); done=subprocess.run(cmd,cwd=work,env=env,text=True,capture_output=True,check=False); finished=now(); outputs={n:sha256(work/n) for n in a.output if (work/n).is_file()}
    entry={"argv":cmd,"command":shlex.join(cmd),"cwd":str(work),"exit_code":done.returncode,"finished_at_utc":finished,"input_sha256":inputs,"inputs":a.input,"output_sha256":outputs,"outputs":a.output,"software":a.software,"stage":a.stage,"started_at_utc":started,"stderr_sha256":hashlib.sha256(done.stderr.encode()).hexdigest(),"stdout_sha256":hashlib.sha256(done.stdout.encode()).hexdigest()}
    entries=json.loads(evidence.read_text()) if evidence.is_file() else []
    if not isinstance(entries,list): raise SystemExit("stage evidence must be a JSON list")
    entries.append(entry); evidence.write_text(json.dumps(entries,indent=2,sort_keys=True)+"\n")
    if done.stdout: print(done.stdout,end="")
    if done.stderr: print(done.stderr,end="",file=os.sys.stderr)
    raise SystemExit(done.returncode)
if __name__=="__main__": main()
