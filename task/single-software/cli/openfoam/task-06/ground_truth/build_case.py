#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "plate"


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
    (-0.2 0 0) (0 0 0) (0 0.2 0) (-0.2 0.2 0) (1 0 0) (1 0.2 0)
    (-0.2 0 0.01) (0 0 0.01) (0 0.2 0.01) (-0.2 0.2 0.01) (1 0 0.01) (1 0.2 0.01)
);
blocks
(
    hex (0 1 2 3 6 7 8 9) (40 60 1) simpleGrading (1 50 1)
    hex (1 4 5 2 7 10 11 8) (200 60 1) simpleGrading (1 50 1)
);
edges ();
boundary
(
    inlet
    {
        type patch;
        faces ((0 3 9 6));
    }
    outlet
    {
        type patch;
        faces ((4 5 11 10));
    }
    freeStream
    {
        type patch;
        faces ((3 2 8 9) (2 5 11 8));
    }
    upstreamBottom
    {
        type symmetryPlane;
        faces ((0 1 7 6));
    }
    plate
    {
        type wall;
        faces ((1 4 10 7));
    }
    frontAndBack
    {
        type empty;
        faces ((0 1 2 3) (6 9 8 7) (1 4 5 2) (7 8 11 10));
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
    freeStream { type fixedValue; value uniform (10 0 0); }
    upstreamBottom { type symmetryPlane; }
    plate { type noSlip; }
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
    freeStream { type zeroGradient; }
    upstreamBottom { type symmetryPlane; }
    plate { type zeroGradient; }
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
simulationType laminar;
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
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
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
    p
    {
        solver GAMG;
        smoother GaussSeidel;
        tolerance 1e-9;
        relTol 0.02;
    }
    pFinal
    {
        $p;
        relTol 0;
    }
    U
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-9;
        relTol 0.02;
    }
    UFinal
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
    equations { U 0.7; }
}
cache { grad(U); }
""",
)

print(CASE)
