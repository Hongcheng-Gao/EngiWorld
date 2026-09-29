#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "bfs"


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
    (-0.2 0.05 0) (0 0.05 0) (0 0.1 0) (-0.2 0.1 0)
    (1 0.05 0) (1 0.1 0) (0 0 0) (1 0 0)
    (-0.2 0.05 0.01) (0 0.05 0.01) (0 0.1 0.01) (-0.2 0.1 0.01)
    (1 0.05 0.01) (1 0.1 0.01) (0 0 0.01) (1 0 0.01)
);
blocks
(
    hex (0 1 2 3 8 9 10 11) (40 20 1) simpleGrading (1 1 1)
    hex (1 4 5 2 9 12 13 10) (200 20 1) simpleGrading (1 1 1)
    hex (6 7 4 1 14 15 12 9) (200 20 1) simpleGrading (1 1 1)
);
edges ();
boundary
(
    inlet
    {
        type patch;
        faces ((0 3 11 8));
    }
    outlet
    {
        type patch;
        faces ((4 5 13 12) (7 4 12 15));
    }
    walls
    {
        type wall;
        faces ((3 2 10 11) (2 5 13 10) (0 1 9 8) (6 14 9 1) (6 7 15 14));
    }
    frontAndBack
    {
        type empty;
        faces
        (
            (0 1 2 3) (8 11 10 9)
            (1 4 5 2) (9 10 13 12)
            (6 7 4 1) (14 9 12 15)
        );
    }
);
mergePatchPairs ();
""",
)

write(
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
internalField uniform (10 0 0);
boundaryField
{
    inlet { type fixedValue; value uniform (10 0 0); }
    outlet { type zeroGradient; }
    walls { type noSlip; }
    frontAndBack { type empty; }
}
""",
)

write(
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
    inlet { type zeroGradient; }
    outlet { type fixedValue; value uniform 0; }
    walls { type zeroGradient; }
    frontAndBack { type empty; }
}
""",
)

write(
    "0/k",
    r"""
FoamFile
{
    format ascii;
    class volScalarField;
    location "0";
    object k;
}
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0.375;
boundaryField
{
    inlet { type fixedValue; value uniform 0.375; }
    outlet { type zeroGradient; }
    walls { type kqRWallFunction; value uniform 1e-10; }
    frontAndBack { type empty; }
}
""",
)

write(
    "0/omega",
    r"""
FoamFile
{
    format ascii;
    class volScalarField;
    location "0";
    object omega;
}
dimensions [0 0 -1 0 0 0 0];
internalField uniform 1000;
boundaryField
{
    inlet { type fixedValue; value uniform 1000; }
    outlet { type zeroGradient; }
    walls { type omegaWallFunction; value uniform 1e-10; }
    frontAndBack { type empty; }
}
""",
)

write(
    "0/nut",
    r"""
FoamFile
{
    format ascii;
    class volScalarField;
    location "0";
    object nut;
}
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet { type calculated; value uniform 0; }
    outlet { type calculated; value uniform 0; }
    walls { type nutkWallFunction; value uniform 0; }
    frontAndBack { type empty; }
}
""",
)

physical = r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "constant";
    object physicalProperties;
}
viscosityModel constant;
nu [0 2 -1 0 0 0 0] 1.5e-5;
"""
write("constant/physicalProperties", physical)
write("constant/transportProperties", physical.replace("physicalProperties", "transportProperties"))

write(
    "constant/momentumTransport",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "constant";
    object momentumTransport;
}
simulationType RAS;
RAS
{
    model kOmegaSST;
    turbulence on;
    printCoeffs on;
}
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
application simpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 2000;
deltaT 1;
writeControl timeStep;
writeInterval 2000;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 6;
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
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div(phi,k) bounded Gauss upwind;
    div(phi,omega) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
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
    p
    {
        solver GAMG;
        smoother GaussSeidel;
        tolerance 1e-8;
        relTol 0.05;
    }
    pFinal
    {
        $p;
        relTol 0;
    }
    "(U|k|omega)"
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-8;
        relTol 0.05;
    }
    "(U|k|omega)Final"
    {
        $U;
        relTol 0;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
    consistent yes;
}
relaxationFactors
{
    fields { p 0.3; }
    equations { U 0.7; k 0.7; omega 0.7; }
}
cache { grad(U); }
""",
)

print(CASE)
