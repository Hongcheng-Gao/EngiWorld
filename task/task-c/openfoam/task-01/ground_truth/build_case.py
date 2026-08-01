#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "channel"
LENGTH = 1.0
HEIGHT = 0.1
SPAN = 0.01
NX = 100
NY = 80
MEAN_SPEED = 0.1
NU = 1.0e-5


def foam_header(class_name: str, object_name: str, location: str | None = None) -> str:
    location_line = f'    location    "{location}";\n' if location else ""
    return f"""FoamFile
{{
    format      ascii;
    class       {class_name};
{location_line}    object      {object_name};
}}
"""


def inlet_values() -> str:
    values = []
    for index in range(NY):
        y = HEIGHT * (index + 0.5) / NY
        ux = 6.0 * MEAN_SPEED * y * (HEIGHT - y) / HEIGHT**2
        values.append(f"        ({ux:.12g} 0 0)")
    return "\n".join(values)


def main() -> None:
    if CASE.exists():
        shutil.rmtree(CASE)
    for directory in (CASE / "0", CASE / "constant", CASE / "system"):
        directory.mkdir(parents=True, exist_ok=True)

    block_mesh = foam_header("dictionary", "blockMeshDict") + f"""
convertToMeters 1;

vertices
(
    (0 0 0)
    ({LENGTH} 0 0)
    ({LENGTH} {HEIGHT} 0)
    (0 {HEIGHT} 0)
    (0 0 {SPAN})
    ({LENGTH} 0 {SPAN})
    ({LENGTH} {HEIGHT} {SPAN})
    (0 {HEIGHT} {SPAN})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({NX} {NY} 1) simpleGrading (1 1 1)
);

boundary
(
    inlet
    {{
        type patch;
        faces ((0 4 7 3));
    }}
    outlet
    {{
        type patch;
        faces ((1 2 6 5));
    }}
    walls
    {{
        type wall;
        faces ((0 1 5 4) (3 7 6 2));
    }}
    frontAndBack
    {{
        type empty;
        faces ((0 3 2 1) (4 5 6 7));
    }}
);
"""
    (CASE / "system/blockMeshDict").write_text(block_mesh, encoding="utf-8")

    velocity = foam_header("volVectorField", "U", "0") + f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform ({MEAN_SPEED} 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           nonuniform List<vector>
{NY}
(
{inlet_values()}
);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    walls
    {{
        type            noSlip;
    }}
    frontAndBack
    {{
        type            empty;
    }}
}}
"""
    (CASE / "0/U").write_text(velocity, encoding="utf-8")

    pressure = foam_header("volScalarField", "p", "0") + """
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    walls
    {
        type            zeroGradient;
    }
    frontAndBack
    {
        type            empty;
    }
}
"""
    (CASE / "0/p").write_text(pressure, encoding="utf-8")

    transport = foam_header("dictionary", "transportProperties", "constant") + f"""
nu              [0 2 -1 0 0 0 0] {NU};
"""
    (CASE / "constant/transportProperties").write_text(transport, encoding="utf-8")
    physical = foam_header("dictionary", "physicalProperties", "constant") + f"""
nu              [0 2 -1 0 0 0 0] {NU};
"""
    (CASE / "constant/physicalProperties").write_text(physical, encoding="utf-8")

    control = foam_header("dictionary", "controlDict", "system") + """
application     icoFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         30;
deltaT          0.02;
writeControl    runTime;
writeInterval   5;
purgeWrite      0;
writeFormat     ascii;
writePrecision  10;
writeCompression off;
timeFormat      general;
timePrecision   8;
runTimeModifiable false;
"""
    (CASE / "system/controlDict").write_text(control, encoding="utf-8")

    schemes = foam_header("dictionary", "fvSchemes", "system") + """
ddtSchemes
{
    default         Euler;
}
gradSchemes
{
    default         Gauss linear;
}
divSchemes
{
    default         none;
    div(phi,U)      Gauss linear;
}
laplacianSchemes
{
    default         Gauss linear orthogonal;
}
interpolationSchemes
{
    default         linear;
}
snGradSchemes
{
    default         orthogonal;
}
"""
    (CASE / "system/fvSchemes").write_text(schemes, encoding="utf-8")

    solution = foam_header("dictionary", "fvSolution", "system") + """
solvers
{
    p
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-10;
        relTol          0;
    }
    pFinal
    {
        $p;
        relTol          0;
    }
    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-10;
        relTol          0;
    }
}
PISO
{
    nCorrectors             2;
    nNonOrthogonalCorrectors 0;
    pRefCell                0;
    pRefValue               0;
}
"""
    (CASE / "system/fvSolution").write_text(solution, encoding="utf-8")

    half_cell = HEIGHT / (2.0 * NY)
    sample_dict = foam_header("dictionary", "sampleDict", "system") + f"""
type                sets;
libs                ("libsampling.so");
interpolationScheme cellPoint;
setFormat           raw;
sets
(
    outletLine
    {{
        type        lineUniform;
        axis        y;
        start       (0.99 {half_cell:.8f} {SPAN / 2.0:.8f});
        end         (0.99 {HEIGHT - half_cell:.8f} {SPAN / 2.0:.8f});
        nPoints     {NY};
    }}
);
fields              (U);
"""
    (CASE / "system/sampleDict").write_text(sample_dict, encoding="utf-8")


if __name__ == "__main__":
    main()
