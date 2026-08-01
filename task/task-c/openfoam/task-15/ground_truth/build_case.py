#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
SOURCE = ROOT / "damBreak_base"
CASE = ROOT / "dam_break"


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if not SOURCE.is_dir():
    raise FileNotFoundError("missing supplied damBreak_base template")
if CASE.exists():
    shutil.rmtree(CASE)
shutil.copytree(SOURCE, CASE)
shutil.rmtree(CASE / "constant/polyMesh", ignore_errors=True)

write(
    "system/controlDict",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "system";
    object controlDict;
}
application interFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 0.5;
deltaT 0.0001;
writeControl adjustableRunTime;
writeInterval 0.5;
purgeWrite 0;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 8;
runTimeModifiable false;
adjustTimeStep yes;
maxCo 0.5;
maxAlphaCo 0.5;
maxDeltaT 0.002;
""",
)

write(
    "system/setFieldsDict",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "system";
    object setFieldsDict;
}
defaultFieldValues
(
    volScalarFieldValue alpha.water 0
);
regions
(
    boxToCell
    {
        box (0 0 -1) (0.1461 0.292 1);
        fieldValues
        (
            volScalarFieldValue alpha.water 1
        );
    }
);
""",
)

print(CASE)
