#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
SOURCE = ROOT / "shockTube_base"
CASE = ROOT / "shock_tube"


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if not SOURCE.is_dir():
    raise FileNotFoundError("missing supplied shockTube_base template")
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
    (1 0.01 0)
    (0 0.01 0)
    (0 0 0.01)
    (1 0 0.01)
    (1 0.01 0.01)
    (0 0.01 0.01)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (1000 1 1) simpleGrading (1 1 1)
);
boundary
(
    leftRight
    {
        type patch;
        faces ((0 3 7 4) (1 5 6 2));
    }
    empty
    {
        type empty;
        faces ((0 1 2 3) (4 7 6 5) (0 4 5 1) (3 2 6 7));
    }
);
mergePatchPairs ();
""",
)

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
application rhoCentralFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 0.0005;
deltaT 1e-7;
writeControl adjustableRunTime;
writeInterval 0.0005;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 8;
runTimeModifiable false;
adjustTimeStep yes;
maxCo 0.2;
maxDeltaT 1e-6;
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
    volVectorFieldValue U (0 0 0)
    volScalarFieldValue T 278.646992162988
    volScalarFieldValue p 10000
);
regions
(
    boxToCell
    {
        box (0 0 0) (0.5 0.01 0.01);
        fieldValues
        (
            volVectorFieldValue U (0 0 0)
            volScalarFieldValue T 348.308740203735
            volScalarFieldValue p 100000
        );
    }
);
""",
)

write(
    "system/fvSolution",
    r"""
FoamFile
{
    format ascii;
    class dictionary;
    location "system";
    object fvSolution;
}
solvers
{
    "(p|U|e).*"
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-15;
        relTol 0;
    }
    "rho.*"
    {
        solver PCG;
        preconditioner DIC;
        tolerance 1e-15;
        relTol 0;
    }
}
PIMPLE
{
    nOuterCorrectors 2;
    nCorrectors 1;
    nNonOrthogonalCorrectors 0;
    transonic yes;
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
    location "system";
    object fvSchemes;
}
ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U) Gauss upwind;
    div(phid,p) Gauss vanAlbada;
    div(phi,e) Gauss vanAlbada;
    div(phi,K) Gauss vanAlbada;
    div(phi,(p|rho)) Gauss vanAlbada;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear orthogonal; }
interpolationSchemes { default linear; }
snGradSchemes { default orthogonal; }
""",
)

print(CASE)
