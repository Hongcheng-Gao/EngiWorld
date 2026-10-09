#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "pipe_laminar"


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
    (0 0 0)
    (5 0 0)
    (0 0.0499524111 -0.00218096937)
    (5 0.0499524111 -0.00218096937)
    (0 0.0499524111 0.00218096937)
    (5 0.0499524111 0.00218096937)
);
blocks
(
    hex (0 1 3 2 0 1 5 4) (500 40 1) simpleGrading (1 1 1)
);
edges ();
boundary
(
    axis
    {
        type empty;
        faces ((0 1 1 0));
    }
    inlet
    {
        type patch;
        faces ((0 0 4 2));
    }
    outlet
    {
        type patch;
        faces ((1 3 5 1));
    }
    wall
    {
        type wall;
        faces ((2 4 5 3));
    }
    wedgeLow
    {
        type wedge;
        faces ((0 2 3 1));
    }
    wedgeHigh
    {
        type wedge;
        faces ((0 1 5 4));
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
internalField uniform (1 0 0);
boundaryField
{
    axis { type empty; }
    inlet { type fixedValue; value uniform (1 0 0); }
    outlet { type zeroGradient; }
    wall { type noSlip; }
    wedgeLow { type wedge; }
    wedgeHigh { type wedge; }
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
    axis { type empty; }
    inlet { type zeroGradient; }
    outlet { type fixedValue; value uniform 0; }
    wall { type zeroGradient; }
    wedgeLow { type wedge; }
    wedgeHigh { type wedge; }
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
nu [0 2 -1 0 0 0 0] 1e-4;
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
