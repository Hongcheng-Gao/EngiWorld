#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional


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


def parse_profile_second_column(path: Path) -> list[float]:
    values: list[float] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return values

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("("):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            values.append(float(parts[1]))
        except ValueError:
            continue
    return values


def find_rst_files(root: Path) -> list[Path]:
    candidates = sorted((root).glob("*.rst")) + sorted(root.glob("*.rst"))
    return [p for p in candidates if is_nonempty_file(p)]


def find_workbench_rst_files(root: Path, wbpj_name: str) -> list[Path]:
    outputs = root
    wbpj = outputs / wbpj_name
    if not is_nonempty_file(wbpj):
        return []

    stem = Path(wbpj_name).stem
    dir_candidates: list[Path] = [outputs / f"{stem}_files", outputs / stem]

    if outputs.exists() and outputs.is_dir():
        for entry in outputs.iterdir():
            if entry.is_dir() and stem.lower() in entry.name.lower() and entry not in dir_candidates:
                dir_candidates.append(entry)

    for directory in dir_candidates:
        if not directory.exists() or not directory.is_dir():
            continue
        rst_files = [p for p in sorted(directory.rglob("*.rst")) if is_nonempty_file(p)]
        if rst_files:
            return rst_files

    return []


def run_ansys_batch(apdl_script: str, root: Path, timeout: int = 180) -> tuple[bool, str]:
    inp_path: Optional[Path] = None
    out_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".inp", dir=root, delete=False) as inp:
            inp.write(apdl_script)
            inp_path = Path(inp.name)

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".out", dir=root, delete=False) as out:
            out_path = Path(out.name)

        proc = subprocess.run(
            ["ansys", "-b", "-i", inp_path.name, "-o", out_path.name],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if out_path.exists():
            combined += "\n" + out_path.read_text(encoding="utf-8", errors="ignore")

        return proc.returncode == 0, combined
    except Exception:
        return False, ""
    finally:
        for temp in (inp_path, out_path):
            if temp is not None:
                try:
                    temp.unlink()
                except OSError:
                    pass


def run_ansys_with_extract_file(root: Path, apdl_template: str, timeout: int = 180) -> Optional[list[float]]:
    token = f"_eval_{uuid.uuid4().hex[:8]}"
    value_file = root / f"{token}.txt"
    apdl_script = apdl_template.replace("__OUT_BASENAME__", token)
    ok, _ = run_ansys_batch(apdl_script, root, timeout)
    try:
        if not ok or not is_nonempty_file(value_file):
            return None
        return parse_floats(value_file.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None
    finally:
        try:
            value_file.unlink()
        except OSError:
            pass


def run_fluent_batch(journal: str, dimension: str, root: Path, timeout: int = 180) -> tuple[bool, str]:
    jou_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".jou", dir=root, delete=False) as jou:
            jou.write(journal)
            jou_path = Path(jou.name)

        proc = subprocess.run(
            ["fluent", dimension, "-g", "-i", jou_path.name],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return proc.returncode == 0, combined
    except Exception:
        return False, ""
    finally:
        if jou_path is not None:
            try:
                jou_path.unlink()
            except OSError:
                pass


def run_fluent_with_profile(root: Path, journal_template: str, dimension: str, timeout: int = 180) -> Optional[list[float]]:
    token = f"_eval_{uuid.uuid4().hex[:8]}"
    profile_file = root / f"{token}.xy"
    journal = journal_template.replace("__OUT_XY__", profile_file.name)
    ok, _ = run_fluent_batch(journal, dimension, root, timeout)
    try:
        if not ok or not is_nonempty_file(profile_file):
            return None
        return parse_profile_second_column(profile_file)
    except Exception:
        return None
    finally:
        try:
            profile_file.unlink()
        except OSError:
            pass


def check_task(root: Path) -> bool:
    rst_files = find_workbench_rst_files(root, "wb_hertz.wbpj")
    if not rst_files:
        return False

    rst_file = rst_files[0].as_posix()
    ok, output = run_ansys_batch(f'''
    /FILNAME,extract
    /POST1
    FILE,'{rst_file}'
    SET,LAST
    *GET,P_MAX,NODE,0,S,EQV
    *STATUS,P_MAX
    FINISH
    /EXIT
    ''', root)
    if not ok:
        return False

    match = re.search(r'PARAMETER\s+STATUS-\s+P_MAX\s*=\s*([\d.Ee+-]+)', output, re.IGNORECASE)
    if not match:
        return False

    p_max = float(match.group(1))
    if abs(p_max - 2352.0) / 2352.0 > 0.10:
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
    print("true" if result == 1 else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
