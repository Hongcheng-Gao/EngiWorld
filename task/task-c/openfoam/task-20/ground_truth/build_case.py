#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
SOURCE = ROOT / "dynamic_base"
CASE = ROOT / "dynamic"


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if not SOURCE.is_dir():
    raise FileNotFoundError("missing supplied dynamic_base template")
if CASE.exists():
    shutil.rmtree(CASE)
shutil.copytree(SOURCE, CASE)
shutil.rmtree(CASE / "constant/polyMesh", ignore_errors=True)

write(
    "system/topoSetDict",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "system";
    object topoSetDict;
}
actions
(
    {
        name movingCells;
        type cellSet;
        action new;
        source cylinderToCell;
        sourceInfo
        {
            p1 (0 0 -2);
            p2 (0 0 2);
            radius 1.41;
        }
    }
    {
        name movingZone;
        type cellZoneSet;
        action new;
        source setToCellZone;
        sourceInfo { set movingCells; }
    }
);
""",
)

write(
    "constant/dynamicMeshDict",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "constant";
    object dynamicMeshDict;
}
mover
{
    type motionSolver;
    libs ("libfvMeshMovers.so" "libfvMotionSolvers.so");
    motionSolver solidBody;
    cellZone movingZone;
    solidBodyMotionFunction oscillatingRotatingMotion;
    origin (0 0 0);
    amplitude (0 0 5);
    omega 6.283185307179586;
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
nu [0 2 -1 0 0 0 0] 0.01;
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
    left { type fixedValue; value uniform (0.5 0 0); }
    right { type zeroGradient; }
    down { type slip; }
    up { type slip; }
    cylinder { type movingWallVelocity; value uniform (0 0 0); }
    defaultFaces { type empty; }
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
    left { type zeroGradient; }
    right { type fixedValue; value uniform 0; }
    down { type zeroGradient; }
    up { type zeroGradient; }
    cylinder { type zeroGradient; }
    defaultFaces { type empty; }
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
application pimpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 2;
deltaT 0.001;
writeControl runTime;
writeInterval 0.25;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 8;
runTimeModifiable false;
functions
{
    bodyForces
    {
        type forces;
        libs ("libforces.so");
        writeControl timeStep;
        writeInterval 1;
        patches (cylinder);
        rho rhoInf;
        rhoInf 1;
        CofR (0 0 0);
    }
}
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
gradSchemes { default leastSquares; }
divSchemes
{
    default none;
    div(phi,U) Gauss linear;
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
    pcorr
    {
        solver PCG;
        preconditioner DIC;
        tolerance 1e-8;
        relTol 0;
    }
    pcorrFinal { $pcorr; relTol 0; }
    p
    {
        solver GAMG;
        smoother DIC;
        tolerance 1e-8;
        relTol 0.05;
    }
    pFinal { $p; relTol 0; }
    U
    {
        solver PBiCGStab;
        preconditioner DILU;
        tolerance 1e-8;
        relTol 0;
    }
}
PIMPLE
{
    momentumPredictor no;
    nOuterCorrectors 2;
    nCorrectors 2;
    nNonOrthogonalCorrectors 0;
}
""",
)

print(CASE)
