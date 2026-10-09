#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OPENFAST = Path("/home/user/miniconda3/bin/openfast")
RPMS = (6, 9, 12, 15)


def replace_parameter(text: str, name: str, value: str) -> str:
    pattern = re.compile(rf"^.*?(\s+{re.escape(name)}\s+-.*)$", re.MULTILINE)
    updated, count = pattern.subn(f"{value}\\1", text, count=1)
    if count != 1:
        raise ValueError(f"expected one {name} parameter")
    return updated


def prepare_aerodyn() -> None:
    text = (ROOT / "NRELOffshrBsline5MW_Onshore_AeroDyn.dat").read_text(
        encoding="utf-8", errors="ignore"
    )
    text = text.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    marker = "END of OutList section"
    if marker not in text:
        raise ValueError("AeroDyn OutList terminator not found")
    text = text.replace(marker, '"RtAeroPwr"\n' + marker, 1)
    (ROOT / "aerodyn_tsr.dat").write_text(text, encoding="utf-8")


def prepare_case(rpm: int) -> Path:
    ed_text = (ROOT / "elasto_tsr_base.dat").read_text(encoding="utf-8", errors="ignore")
    if "{RPM}" not in ed_text:
        raise ValueError("ElastoDyn RPM placeholder not found")
    ed_name = f"elasto_rpm{rpm}.dat"
    (ROOT / ed_name).write_text(ed_text.replace("{RPM}", str(rpm)), encoding="utf-8")

    fst_text = (ROOT / "tsr_scan.fst").read_text(encoding="utf-8", errors="ignore")
    fst_text = replace_parameter(fst_text, "TMax", "30")
    fst_text = replace_parameter(fst_text, "DT_Out", "0.1")
    fst_text = replace_parameter(fst_text, "OutFileFmt", "1")
    fst_text = replace_parameter(fst_text, "EDFile", f'"{ed_name}"')
    fst_text = replace_parameter(
        fst_text,
        "InflowFile",
        '"5MW_Baseline/NRELOffshrBsline5MW_InflowWind_Steady8mps.dat"',
    )
    fst_text = replace_parameter(fst_text, "AeroFile", '"aerodyn_tsr.dat"')
    fst_name = ROOT / f"case_rpm{rpm}.fst"
    fst_name.write_text(fst_text, encoding="utf-8")
    return fst_name


def main() -> int:
    if not OPENFAST.is_file():
        raise FileNotFoundError(OPENFAST)
    prepare_aerodyn()
    for rpm in RPMS:
        fst_path = prepare_case(rpm)
        log_path = ROOT / f"case_rpm{rpm}.log"
        with log_path.open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                [str(OPENFAST), fst_path.name],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if completed.returncode != 0:
            raise RuntimeError(f"OpenFAST failed for {fst_path.name}; see {log_path.name}")
    return subprocess.run([sys.executable, "postprocess.py"], cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
