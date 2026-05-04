#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Optional

VALID_MODES = {"auto", "subprocess", "direct"}


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_floats(text: str) -> list[float]:
    values: list[float] = []
    for token in text.replace(",", " ").split():
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values


def run_extraction(script: str, root: Path, mode: str, timeout: int = 120) -> Optional[str]:
    normalized_script = textwrap.dedent(script)
    if mode in ("auto", "direct"):
        cwd = os.getcwd()
        try:
            os.chdir(root)
            capture = io.StringIO()
            namespace = {"__name__": "__main__"}
            with contextlib.redirect_stdout(capture):
                exec(normalized_script, namespace, namespace)
            out = capture.getvalue().strip()
            if out:
                return out
        except BaseException:
            pass
        finally:
            os.chdir(cwd)
        if mode == "direct":
            return None

    if mode in ("auto", "subprocess"):
        temp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".py",
                dir=root,
                delete=False,
            ) as handle:
                handle.write(normalized_script)
                temp_path = Path(handle.name)

            proc = subprocess.run(
                ["abaqus", "python", temp_path.name],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if proc.returncode != 0:
                return None
            out = (proc.stdout or "").strip()
            return out or None
        except Exception:
            return None
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    return None


def check_task(root: Path, mode: str) -> bool:
    for rel in ("Job-BlockTension.cae", "Job-BlockTension.odb"):
        if not is_nonempty_file(root / rel):
            return False

    script = r'''
    from odbAccess import openOdb
    odb = openOdb(path='Job-BlockTension.odb', readOnly=True)
    step = odb.steps['Step-Load']
    last = step.frames[-1]
    s11_vals = [v.data[0] for v in last.fieldOutputs['S'].values if len(v.data) > 0]
    u1_vals = [abs(v.data[0]) for v in last.fieldOutputs['U'].values if len(v.data) > 0]
    print(max(s11_vals) if s11_vals else 0.0, max(u1_vals) if u1_vals else 0.0)
    odb.close()
    '''
    out = run_extraction(script, root, mode)
    if not out:
        return False

    vals = parse_floats(out)
    if len(vals) < 2:
        return False

    max_s11, max_u1 = vals[-2], vals[-1]
    expected_s11 = 8.33
    expected_u1 = 0.0143
    if abs(max_s11 - expected_s11) / expected_s11 > 0.15:
        return False
    if abs(max_u1 - expected_u1) / expected_u1 > 0.20:
        return False
    return True

def evaluate() -> int:
    root = Path(r"C:\\Users\\Administrator\\Desktop")
    try:
        ok = check_task(root)
    except Exception:
        ok = False
    return 1 if ok else 0


def main() -> int:
    result = evaluate()
    print("True" if result == 1 else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
