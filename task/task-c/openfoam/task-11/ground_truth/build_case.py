#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
SWEEP = ROOT / "cavity_sweep"
REYNOLDS = (100, 400, 1000)


def write(case: Path, relative: str, content: str) -> None:
    path = case / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if SWEEP.exists():
    shutil.rmtree(SWEEP)

for reynolds in REYNOLDS:
    case = SWEEP / f"Re{reynolds}"
    viscosity = 1.0 / reynolds
    write(
        case,
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
    (0 0 0)
    (1 0 0)
    (1 1 0)
    (0 1 0)
    (0 0 0.01)
    (1 0 0.01)
    (1 1 0.01)
    (0 1 0.01)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (50 50 1) simpleGrading (1 1 1)
);
edges ();
boundary
(
    movingWall { type wall; faces ((3 7 6 2)); }
    fixedWalls { type wall; faces ((0 4 7 3) (1 2 6 5) (0 1 5 4)); }
    frontAndBack { type empty; faces ((0 3 2 1) (4 5 6 7)); }
);
mergePatchPairs ();
""",
    )
    write(
        case,
        "0/U",
        r"""
FoamFile
{
    format ascii;
    class volVectorField;
    location "0";
    object U;
}
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{
    movingWall { type fixedValue; value uniform (1 0 0); }
    fixedWalls { type noSlip; }
    frontAndBack { type empty; }
}
""",
    )
    write(
        case,
        "0/p",
        r"""
FoamFile
{
    format ascii;
    class volScalarField;
    location "0";
    object p;
}
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    movingWall { type zeroGradient; }
    fixedWalls { type zeroGradient; }
    frontAndBack { type empty; }
}
""",
    )
    physical = f"""
FoamFile
{{
    format ascii;
    class dictionary;
    location "constant";
    object physicalProperties;
}}
nu [0 2 -1 0 0 0 0] {viscosity:.12g};
"""
    write(case, "constant/physicalProperties", physical)
    write(case, "constant/transportProperties", physical.replace("physicalProperties", "transportProperties"))
    write(
        case,
        "system/controlDict",
        r"""
FoamFile
{
    format ascii;
    class dictionary;
    object controlDict;
}
application icoFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 30;
deltaT 0.005;
writeControl timeStep;
writeInterval 6000;
purgeWrite 0;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 6;
runTimeModifiable false;
""",
    )
    write(
        case,
        "system/fvSchemes",
        r"""
FoamFile
{
    format ascii;
    class dictionary;
    object fvSchemes;
}
ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes { default none; div(phi,U) Gauss linear; }
laplacianSchemes { default Gauss linear orthogonal; }
interpolationSchemes { default linear; }
snGradSchemes { default orthogonal; }
""",
    )
    write(
        case,
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
    p
    {
        solver PCG;
        preconditioner DIC;
        tolerance 1e-8;
        relTol 0.01;
    }
    pFinal { $p; relTol 0; }
    U
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-9;
        relTol 0;
    }
}
PISO
{
    nCorrectors 2;
    nNonOrthogonalCorrectors 0;
    pRefCell 0;
    pRefValue 0;
}
""",
    )

print(SWEEP)
