#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--software", required=True)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    command = command[1:] if command and command[0] == "--" else command
    if not command:
        raise SystemExit("recorded stage requires a command after --")
    work = Path(args.work).resolve()
    evidence = Path(args.evidence).resolve()
    environment = os.environ.copy()
    for assignment in args.env:
        key, separator, value = assignment.partition("=")
        if not separator or not key:
            raise SystemExit(f"invalid --env assignment: {assignment}")
        environment[key] = value
    input_hashes = {name: sha256(work / name) for name in args.input}
    started = now()
    completed = subprocess.run(command, cwd=work, env=environment, text=True, capture_output=True, check=False)
    finished = now()
    output_hashes = {name: sha256(work / name) for name in args.output if (work / name).is_file()}
    entry = {
        "argv": command,
        "command": shlex.join(command),
        "cwd": str(work),
        "exit_code": completed.returncode,
        "finished_at_utc": finished,
        "input_sha256": input_hashes,
        "inputs": args.input,
        "output_sha256": output_hashes,
        "outputs": args.output,
        "software": args.software,
        "stage": args.stage,
        "started_at_utc": started,
        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
    }
    entries = json.loads(evidence.read_text()) if evidence.is_file() else []
    if not isinstance(entries, list):
        raise SystemExit("stage evidence must be a JSON list")
    entries.append(entry)
    evidence.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=os.sys.stderr)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
