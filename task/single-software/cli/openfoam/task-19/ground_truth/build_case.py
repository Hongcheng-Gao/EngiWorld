#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
SOURCE = ROOT / "porous_base"
CASE = ROOT / "porous"


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if not SOURCE.is_dir():
    raise FileNotFoundError("missing supplied porous_base template")
if CASE.exists():
    shutil.rmtree(CASE)
shutil.copytree(SOURCE, CASE)
shutil.rmtree(CASE / "constant/polyMesh", ignore_errors=True)

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
    (1 0 0)
    (1 0.1 0)
    (0 0.1 0)
    (0 0 0.01)
    (1 0 0.01)
    (1 0.1 0.01)
    (0 0.1 0.01)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (100 10 1) simpleGrading (1 1 1)
);
boundary
(
    inlet { type patch; faces ((0 3 7 4)); }
    outlet { type patch; faces ((1 5 6 2)); }
    topBottom { type symmetry; faces ((0 4 5 1) (3 2 6 7)); }
    frontAndBack { type empty; faces ((0 1 2 3) (4 7 6 5)); }
);
mergePatchPairs ();
""",
)

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
        name porousCells;
        type cellSet;
        action new;
        source boxToCell;
        sourceInfo { box (-1 -1 -1) (2 2 2); }
    }
    {
        name porosity;
        type cellZoneSet;
        action new;
        source setToCellZone;
        sourceInfo { set porousCells; }
    }
);
""",
)

write(
    "constant/porosityProperties",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "constant";
    object porosityProperties;
}
porousBed
{
    type DarcyForchheimer;
    cellZone porosity;
    d (1e8 1e8 1e8);
    f (1000 1000 1000);
    coordinateSystem
    {
        type cartesian;
        origin (0 0 0);
        coordinateRotation
        {
            type axesRotation;
            e1 (1 0 0);
            e2 (0 1 0);
        }
    }
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
nu [0 2 -1 0 0 0 0] 1e-6;
"""
write("constant/physicalProperties", physical)
write("constant/transportProperties", physical.replace("physicalProperties", "transportProperties"))
write(
    "constant/referenceProperties",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "constant";
    object referenceProperties;
}
rho 1000;
""",
)
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
internalField uniform (0.1 0 0);
boundaryField
{
    inlet { type fixedValue; value uniform (0.1 0 0); }
    outlet { type zeroGradient; }
    topBottom { type symmetry; }
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
    topBottom { type symmetry; }
    frontAndBack { type empty; }
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
application porousSimpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 500;
deltaT 1;
writeControl timeStep;
writeInterval 500;
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
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear orthogonal; }
interpolationSchemes { default linear; }
snGradSchemes { default orthogonal; }
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
        tolerance 1e-10;
        relTol 0.01;
    }
    U
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-10;
        relTol 0.01;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
    pRefCell 0;
    pRefValue 0;
}
relaxationFactors
{
    fields { p 0.3; }
    equations { U 0.7; }
}
""",
)

print(CASE)
