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
    for rel in ("outputs/Job-UDL.cae", "outputs/Job-UDL.odb"):
        if not is_nonempty_file(root / rel):
            return False

    script = r'''
    from odbAccess import openOdb
    odb = openOdb(path='outputs/Job-UDL.odb', readOnly=True)
    step = odb.steps['Step-Load']
    last = step.frames[-1]
    max_u2 = max(abs(v.data[1]) for v in last.fieldOutputs['U'].values if len(v.data) > 1)
    max_mises = max(v.mises for v in last.fieldOutputs['S'].values if v.mises is not None)
    print(max_u2, max_mises)
    odb.close()
    '''
    out = run_extraction(script, root, mode)
    if not out:
        return False

    vals = parse_floats(out)
    if len(vals) < 2:
        return False

    u2, mises = vals[-2], vals[-1]
    expected_u2 = 0.0595
    expected_mises = 18.75
    if abs(u2 - expected_u2) / expected_u2 > 0.15:
        return False
    if abs(mises - expected_mises) / expected_mises > 0.12:
        return False
    return True


def evaluate(mode: str = "auto") -> int:
    normalized_mode = mode if mode in VALID_MODES else "auto"
    root = Path(__file__).resolve().parent
    try:
        ok = check_task(root, normalized_mode)
    except Exception:
        ok = False
    return 1 if ok else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate task outputs")
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="auto")
    parser.add_argument("--result-path", default="outputs/eval_result.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    try:
        result = evaluate(args.mode)
    except Exception:
        result = 0

    write_result(root / args.result_path, result)
    return 0 if result == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
