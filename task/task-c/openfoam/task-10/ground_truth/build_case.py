#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "buoyant"


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if CASE.exists():
    shutil.rmtree(CASE)
CASE.mkdir(parents=True)

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
    (0.1 0 0)
    (0.1 0.1 0)
    (0 0.1 0)
    (0 0 0.01)
    (0.1 0 0.01)
    (0.1 0.1 0.01)
    (0 0.1 0.01)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (41 41 1) simpleGrading (1 1 1)
);
edges ();
boundary
(
    hot { type wall; faces ((0 3 7 4)); }
    cold { type wall; faces ((1 5 6 2)); }
    topAndBottom { type wall; faces ((0 4 5 1) (3 2 6 7)); }
    frontAndBack { type empty; faces ((0 1 2 3) (4 7 6 5)); }
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
internalField uniform (0 0 0);
boundaryField
{
    hot { type noSlip; }
    cold { type noSlip; }
    topAndBottom { type noSlip; }
    frontAndBack { type empty; }
}
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
internalField uniform 300;
boundaryField
{
    hot { type fixedValue; value uniform 310; }
    cold { type fixedValue; value uniform 290; }
    topAndBottom { type zeroGradient; }
    frontAndBack { type empty; }
}
""",
)

write(
    "0/p_rgh",
    r"""
FoamFile
{
    format ascii;
    class volScalarField;
    location "0";
    object p_rgh;
}
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    hot { type fixedFluxPressure; value uniform 0; }
    cold { type fixedFluxPressure; value uniform 0; }
    topAndBottom { type fixedFluxPressure; value uniform 0; }
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
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 100000;
boundaryField
{
    hot { type calculated; value uniform 100000; }
    cold { type calculated; value uniform 100000; }
    topAndBottom { type calculated; value uniform 100000; }
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
thermoType
{
    type heRhoThermo;
    mixture pureMixture;
    transport const;
    thermo hConst;
    equationOfState perfectGas;
    specie specie;
    energy sensibleEnthalpy;
}
mixture
{
    specie { molWeight 28.96; }
    thermodynamics { Cp 1004.4; Hf 0; }
    transport { mu 1.846e-05; Pr 0.71; }
}
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
    "constant/g",
    r"""
FoamFile
{
    format ascii;
    class uniformDimensionedVectorField;
    location "constant";
    object g;
}
dimensions [0 1 -2 0 0 0 0];
value (0 -9.81 0);
""",
)

write(
    "constant/pRef",
    r"""
FoamFile
{
    format ascii;
    class uniformDimensionedScalarField;
    location "constant";
    object pRef;
}
dimensions [1 -1 -2 0 0 0 0];
value 100000;
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
application foamRun;
solver fluid;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 1000;
deltaT 1;
writeControl timeStep;
writeInterval 1000;
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
    div(phi,K) bounded Gauss upwind;
    div(phi,h) bounded Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear orthogonal; }
interpolationSchemes { default linear; }
snGradSchemes { default orthogonal; }
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
    p_rgh
    {
        solver GAMG;
        smoother DICGaussSeidel;
        tolerance 1e-8;
        relTol 0.01;
    }
    "(U|h)"
    {
        solver PBiCGStab;
        preconditioner DILU;
        tolerance 1e-9;
        relTol 0.05;
    }
}
PIMPLE
{
    momentumPredictor no;
    nNonOrthogonalCorrectors 0;
    pRefCell 0;
    pRefValue 0;
}
relaxationFactors
{
    fields { rho 1; p_rgh 0.7; }
    equations { U 0.5; h 0.5; }
}
""",
)

print(CASE)
