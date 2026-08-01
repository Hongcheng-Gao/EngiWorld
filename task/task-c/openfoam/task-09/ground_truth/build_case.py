#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "heat"


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if CASE.exists():
    shutil.rmtree(CASE)

write(
    "system/blockMeshDict",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    object blockMeshDict;
}
convertToMeters 1;
vertices
(
    (0 0 0) (1 0 0) (1 0.5 0) (0 0.5 0)
    (0 0 0.01) (1 0 0.01) (1 0.5 0.01) (0 0.5 0.01)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (200 20 1) simpleGrading (1 1 1)
);
edges ();
boundary
(
    hot { type wall; faces ((0 3 7 4)); }
    cold { type wall; faces ((1 5 6 2)); }
    adiabatic { type wall; faces ((0 4 5 1) (3 2 6 7)); }
    frontAndBack { type empty; faces ((0 1 2 3) (4 7 6 5)); }
);
mergePatchPairs ();
""",
)

write(
    "0/T",
    r"""
FoamFile
{
    format ascii;
    class volScalarField;
    location "0";
    object T;
}
dimensions [0 0 0 1 0 0 0];
internalField uniform 350;
boundaryField
{
    hot { type fixedValue; value uniform 400; }
    cold { type fixedValue; value uniform 300; }
    adiabatic { type zeroGradient; }
    frontAndBack { type empty; }
}
""",
)

write(
    "constant/physicalProperties",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "constant";
    object physicalProperties;
}
DT DT [0 2 -1 0 0 0 0] 0.01;
""",
)

write(
    "system/controlDict",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    object controlDict;
}
application laplacianFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 50;
deltaT 0.05;
writeControl runTime;
writeInterval 50;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 8;
runTimeModifiable false;
""",
)

write(
    "system/fvSchemes",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    object fvSchemes;
}
ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; grad(T) Gauss linear; }
divSchemes { default none; }
laplacianSchemes { default none; laplacian(DT,T) Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
""",
)

write(
    "system/fvSolution",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    object fvSolution;
}
solvers
{
    T
    {
        solver PCG;
        preconditioner DIC;
        tolerance 1e-10;
        relTol 0;
    }
}
SIMPLE { nNonOrthogonalCorrectors 0; }
""",
)

print(CASE)
