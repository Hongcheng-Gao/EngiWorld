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
    for rel in ("outputs/Job-Buckle.cae", "outputs/Job-Buckle.odb"):
        if not is_nonempty_file(root / rel):
            return False

    script = r'''
    import re
    from odbAccess import openOdb
    odb = openOdb(path='outputs/Job-Buckle.odb', readOnly=True)
    step = odb.steps['Step-1'] if 'Step-1' in odb.steps else list(odb.steps.values())[0]
    eig = None
    for frame in step.frames[1:]:
        description = frame.description or ''
        match = re.search(r'Eigenvalue[\s:=]+([\d.eE+-]+)', description)
        if match:
            eig = float(match.group(1))
            break
    if eig is None and len(step.frames) > 1:
        eig = float(step.frames[1].frameValue)
    print(eig if eig is not None else 0.0)
    odb.close()
    '''
    out = run_extraction(script, root, mode)
    if not out:
        return False

    vals = parse_floats(out)
    if not vals:
        return False

    eig = vals[-1]
    expected = 75.96
    if abs(eig - expected) / expected > 0.10:
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
