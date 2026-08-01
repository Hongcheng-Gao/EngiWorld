#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
SOURCE = ROOT / "snappy_base"
CASE = ROOT / "cylinder_snappy"


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if not (SOURCE / "constant/triSurface/cylinder.stl").is_file():
    raise FileNotFoundError("missing supplied snappy_base cylinder.stl")
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
    (0 0 -0.005)
    (2 0 -0.005)
    (2 1 -0.005)
    (0 1 -0.005)
    (0 0 0.005)
    (2 0 0.005)
    (2 1 0.005)
    (0 1 0.005)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (160 80 1) simpleGrading (1 1 1)
);
boundary
(
    inlet
    {
        type patch;
        faces ((0 3 7 4));
    }
    outlet
    {
        type patch;
        faces ((1 5 6 2));
    }
    topBottom
    {
        type symmetry;
        faces ((0 4 5 1) (3 2 6 7));
    }
    frontAndBack
    {
        type symmetry;
        faces ((0 1 2 3) (4 7 6 5));
    }
);
mergePatchPairs ();
""",
)

write(
    "system/snappyHexMeshDict",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    object snappyHexMeshDict;
}
castellatedMesh true;
snap true;
addLayers true;

geometry
{
    cylinder
    {
        type triSurfaceMesh;
        file "cylinder.stl";
    }
}

castellatedMeshControls
{
    maxLocalCells 500000;
    maxGlobalCells 1000000;
    minRefinementCells 0;
    nCellsBetweenLevels 2;
    resolveFeatureAngle 30;
    features ();
    refinementSurfaces
    {
        cylinder
        {
            level (2 3);
            patchInfo { type wall; }
        }
    }
    refinementRegions {};
    locationInMesh (0.1 0.5 0);
    allowFreeStandingZoneFaces true;
}

snapControls
{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
    nFeatureSnapIter 15;
    implicitFeatureSnap true;
    explicitFeatureSnap false;
    multiRegionFeatureSnap false;
}

addLayersControls
{
    relativeSizes true;
    layers
    {
        cylinder { nSurfaceLayers 3; }
    }
    expansionRatio 1.2;
    finalLayerThickness 0.4;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}

meshQualityControls
{
    #include "meshQualityDict"
}
mergeTolerance 1e-6;
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
functions
{
    wallYPlus
    {
        type yPlus;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 500;
    }
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
viscosityModel constant;
nu [0 2 -1 0 0 0 0] 1e-6;
""",
)
shutil.copyfile(CASE / "constant/physicalProperties", CASE / "constant/transportProperties")
transport = (CASE / "constant/transportProperties").read_text(encoding="utf-8")
(CASE / "constant/transportProperties").write_text(
    transport.replace("object physicalProperties;", "object transportProperties;"),
    encoding="utf-8",
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
simulationType RAS;
RAS
{
    model realizableKE;
    turbulence on;
    printCoeffs on;
}
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
internalField uniform (3 0 0);
boundaryField
{
    inlet { type fixedValue; value uniform (3 0 0); }
    outlet { type zeroGradient; }
    topBottom { type symmetry; }
    frontAndBack { type symmetry; }
    cylinder { type noSlip; }
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
    frontAndBack { type symmetry; }
    cylinder { type zeroGradient; }
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
internalField uniform 0.03375;
boundaryField
{
    inlet { type fixedValue; value uniform 0.03375; }
    outlet { type zeroGradient; }
    topBottom { type symmetry; }
    frontAndBack { type symmetry; }
    cylinder { type kqRWallFunction; value uniform 0.03375; }
}
""",
)

write(
    "0/epsilon",
    r"""
FoamFile
{
    format ascii;
    class volScalarField;
    location "0";
    object epsilon;
}
dimensions [0 2 -3 0 0 0 0];
internalField uniform 0.1458;
boundaryField
{
    inlet { type fixedValue; value uniform 0.1458; }
    outlet { type zeroGradient; }
    topBottom { type symmetry; }
    frontAndBack { type symmetry; }
    cylinder { type epsilonWallFunction; value uniform 0.1458; }
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
    topBottom { type symmetry; }
    frontAndBack { type symmetry; }
    cylinder { type nutkWallFunction; value uniform 0; }
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
ddtSchemes { default steadyState; }
gradSchemes
{
    default Gauss linear;
    grad(U) cellLimited Gauss linear 1;
}
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div(phi,k) bounded Gauss upwind;
    div(phi,epsilon) bounded Gauss upwind;
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
    "(U|k|epsilon)"
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-8;
        relTol 0.05;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
}
relaxationFactors
{
    fields { p 0.3; }
    equations
    {
        U 0.7;
        k 0.7;
        epsilon 0.7;
    }
}
""",
)

print(CASE)
