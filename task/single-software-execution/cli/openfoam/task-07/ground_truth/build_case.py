#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import shutil


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cylinder"
INNER = 0.05
OUTER = 1.0
SECTORS = 8


def write(relative: str, content: str) -> None:
    path = CASE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def point(radius: float, angle_index: float, z: float) -> str:
    angle = 2.0 * math.pi * angle_index / SECTORS
    return f"({radius * math.cos(angle):.12g} {radius * math.sin(angle):.12g} {z:.12g})"


if CASE.exists():
    shutil.rmtree(CASE)

vertices = []
for z in (0.0, 0.01):
    for radius in (INNER, OUTER):
        vertices.extend(point(radius, index, z) for index in range(SECTORS))

blocks = []
arcs = []
cylinder_faces = []
inlet_faces = []
outlet_faces = []
front_back_faces = []
for index in range(SECTORS):
    nxt = (index + 1) % SECTORS
    inner0, inner1 = index, nxt
    outer0, outer1 = SECTORS + index, SECTORS + nxt
    top_inner0, top_inner1 = 2 * SECTORS + index, 2 * SECTORS + nxt
    top_outer0, top_outer1 = 3 * SECTORS + index, 3 * SECTORS + nxt
    blocks.append(
        f"hex ({inner0} {outer0} {outer1} {inner1} {top_inner0} {top_outer0} {top_outer1} {top_inner1}) "
        "(40 12 1) simpleGrading (10 1 1)"
    )
    for radius, lower_offset, upper_offset in (
        (INNER, 0, 2 * SECTORS),
        (OUTER, SECTORS, 3 * SECTORS),
    ):
        arcs.append(f"arc {lower_offset + index} {lower_offset + nxt} {point(radius, index + 0.5, 0.0)}")
        arcs.append(f"arc {upper_offset + index} {upper_offset + nxt} {point(radius, index + 0.5, 0.01)}")
    cylinder_faces.append(f"({inner0} {top_inner0} {top_inner1} {inner1})")
    outer_face = f"({outer0} {outer1} {top_outer1} {top_outer0})"
    (inlet_faces if index in (2, 3, 4, 5) else outlet_faces).append(outer_face)
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
edges
(
    {chr(10).join(arcs)}
);
boundary
(
    inlet
    {{
        type patch;
        faces ({' '.join(inlet_faces)});
    }}
    outlet
    {{
        type patch;
        faces ({' '.join(outlet_faces)});
    }}
    cylinder
    {{
        type wall;
        faces ({' '.join(cylinder_faces)});
    }}
    frontAndBack
    {{
        type empty;
        faces ({' '.join(front_back_faces)});
    }}
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
internalField uniform (1 0.01 0);
boundaryField
{
    inlet { type fixedValue; value uniform (1 0 0); }
    outlet { type zeroGradient; }
    cylinder { type noSlip; }
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
    cylinder { type zeroGradient; }
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
nu [0 2 -1 0 0 0 0] 1e-3;
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
application pimpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 20;
deltaT 0.0025;
writeControl runTime;
writeInterval 20;
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
        patches (cylinder);
        log true;
        rho rhoInf;
        rhoInf 1;
        CofR (0 0 0);
        liftDir (0 1 0);
        dragDir (1 0 0);
        pitchAxis (0 0 1);
        magUInf 1;
        lRef 0.1;
        Aref 0.001;
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
fluxRequired { default no; p; }
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
    U
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-8;
        relTol 0.05;
    }
    UFinal
    {
        $U;
        relTol 0;
    }
}
PIMPLE
{
    momentumPredictor yes;
    nOuterCorrectors 1;
    nCorrectors 2;
    nNonOrthogonalCorrectors 0;
}
""",
)

print(CASE)
