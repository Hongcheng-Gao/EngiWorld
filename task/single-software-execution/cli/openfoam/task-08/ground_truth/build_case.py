#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "airfoil"
HALF_POINTS = 80
RADIAL_CELLS = 80


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


if CASE.exists():
    shutil.rmtree(CASE)
CASE.mkdir(parents=True)


def naca_thickness(x: float) -> float:
    return 5.0 * 0.12 * (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1015 * x**4
    )


surface = []
for index in range(HALF_POINTS + 1):
    x = 0.5 * (1.0 + math.cos(math.pi * index / HALF_POINTS))
    surface.append((x, naca_thickness(x)))
for index in range(HALF_POINTS - 1, -1, -1):
    x = 0.5 * (1.0 + math.cos(math.pi * index / HALF_POINTS))
    surface.append((x, -naca_thickness(x)))

count = len(surface)
outer = []
for index, (x, y) in enumerate(surface):
    previous = surface[(index - 1) % count]
    following = surface[(index + 1) % count]
    dx = following[0] - previous[0]
    dy = following[1] - previous[1]
    length = math.hypot(dx, dy)
    outer.append((x + 5.0 * dy / length, y - 5.0 * dx / length))
vertices = []
for z in (0.0, 0.01):
    vertices.extend(f"({x:.12g} {y:.12g} {z:.12g})" for x, y in surface)
    vertices.extend(f"({x:.12g} {y:.12g} {z:.12g})" for x, y in outer)

blocks = []
wall_faces = []
farfield_faces = []
front_back_faces = []
for index in range(count):
    nxt = (index + 1) % count
    inner0, inner1 = index, nxt
    outer0, outer1 = count + index, count + nxt
    top_inner0, top_inner1 = 2 * count + index, 2 * count + nxt
    top_outer0, top_outer1 = 3 * count + index, 3 * count + nxt
    blocks.append(
        f"hex ({inner0} {outer0} {outer1} {inner1} {top_inner0} {top_outer0} {top_outer1} {top_inner1}) "
        f"({RADIAL_CELLS} 1 1) simpleGrading (80 1 1)"
    )
    wall_faces.append(f"({inner0} {top_inner0} {top_inner1} {inner1})")
    outer_face = f"({outer0} {outer1} {top_outer1} {top_outer0})"
    farfield_faces.append(outer_face)
    front_back_faces.extend(
        (
            f"({inner0} {inner1} {outer1} {outer0})",
            f"({top_inner0} {top_outer0} {top_outer1} {top_inner1})",
        )
    )

write(
    "system/blockMeshDict",
    f"""
FoamFile
{{
    format ascii;
    class dictionary;
    object blockMeshDict;
}}
convertToMeters 1;
vertices
(
    {chr(10).join(vertices)}
);
blocks
(
    {chr(10).join(blocks)}
);
edges ();
boundary
(
    FARFIELD {{ type patch; faces ({' '.join(farfield_faces)}); }}
    WALL10 {{ type wall; faces ({' '.join(wall_faces)}); }}
    SYMP3 {{ type empty; faces ({' '.join(front_back_faces)}); }}
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
internalField uniform (0.9961946981 0.08715574275 0);
boundaryField
{
    FARFIELD
    {
        type freestreamVelocity;
        freestreamValue uniform (0.9961946981 0.08715574275 0);
        value uniform (0.9961946981 0.08715574275 0);
    }
    SYMP3 { type empty; }
    WALL10 { type noSlip; }
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
    FARFIELD
    {
        type freestreamPressure;
        freestreamValue uniform 0;
    }
    SYMP3 { type empty; }
    WALL10 { type zeroGradient; }
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
internalField uniform 0.001;
boundaryField
{
    FARFIELD
    {
        type inletOutlet;
        inletValue uniform 0.001;
        value uniform 0.001;
    }
    SYMP3 { type empty; }
    WALL10 { type kqRWallFunction; value uniform 1e-10; }
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
internalField uniform 10;
boundaryField
{
    FARFIELD
    {
        type inletOutlet;
        inletValue uniform 10;
        value uniform 10;
    }
    SYMP3 { type empty; }
    WALL10 { type omegaWallFunction; value uniform 1e-10; }
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
    FARFIELD { type calculated; value uniform 0; }
    SYMP3 { type empty; }
    WALL10 { type nutkWallFunction; value uniform 0; }
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
nu [0 2 -1 0 0 0 0] 1e-5;
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
endTime 1000;
deltaT 1;
writeControl timeStep;
writeInterval 1000;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 8;
runTimeModifiable false;
functions
{
    forces
    {
        type forceCoeffs;
        libs ("libforces.so");
        writeControl timeStep;
        writeInterval 1;
        patches (WALL10);
        log true;
        rho rhoInf;
        rhoInf 1;
        CofR (0.25 0 0);
        liftDir (-0.08715574275 0.9961946981 0);
        dragDir (0.9961946981 0.08715574275 0);
        pitchAxis (0 0 1);
        magUInf 1;
        lRef 1;
        Aref 0.01;
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
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss upwind;
    div(phi,k) bounded Gauss upwind;
    div(phi,omega) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.5; }
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
    Phi
    {
        solver GAMG;
        smoother GaussSeidel;
        tolerance 1e-8;
        relTol 0;
    }
    p
    {
        solver GAMG;
        smoother GaussSeidel;
        tolerance 1e-7;
        relTol 0.1;
        maxIter 50;
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
    nNonOrthogonalCorrectors 1;
}
potentialFlow { nNonOrthogonalCorrectors 10; }
relaxationFactors
{
    fields { p 0.1; }
    equations { U 0.3; k 0.5; omega 0.5; }
}
cache { grad(U); }
""",
)

print(CASE)
