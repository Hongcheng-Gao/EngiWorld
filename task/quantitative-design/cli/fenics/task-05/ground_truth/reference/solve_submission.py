#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import dolfin as df


ROOT = Path(os.environ.get("FENICS_TASK_ROOT", "/home/user/Desktop"))


def forward_value(x: float, parameters: dict[str, float], physics: dict[str, float]) -> float:
    elastic_scale = parameters["E"] / 100000.0
    return (
        physics["mechanical_load"] / elastic_scale * x * (1.0 - x)
        + physics["thermal_load"] / parameters["k"] * math.sin(math.pi * x)
        + parameters["alpha"] * x * x
    )


def main() -> int:
    spec = json.loads((ROOT / "problem_spec.json").read_text(encoding="utf-8"))
    parameters = {
        key: float(value)
        for key, value in json.loads((ROOT / "parameters.json").read_text(encoding="utf-8")).items()
    }
    for key, bounds in spec["parameter_bounds"].items():
        if key not in parameters or not float(bounds[0]) <= parameters[key] <= float(bounds[1]):
            raise ValueError(f"parameter {key} outside bounds")

    physics = {key: float(value) for key, value in spec["physics"].items()}
    elastic_amplitude = physics["mechanical_load"] / (parameters["E"] / 100000.0)
    thermal_amplitude = physics["thermal_load"] / parameters["k"]

    mesh = df.UnitIntervalMesh(200)
    space = df.FunctionSpace(mesh, "CG", 2)
    trial = df.TrialFunction(space)
    test = df.TestFunction(space)
    solution = df.Function(space)
    source = df.Expression(
        "2.0*A + B*pi*pi*sin(pi*x[0]) - 2.0*alpha",
        degree=6,
        A=elastic_amplitude,
        B=thermal_amplitude,
        alpha=parameters["alpha"],
        pi=math.pi,
    )

    def left(point, on_boundary):
        return on_boundary and df.near(point[0], 0.0)

    def right(point, on_boundary):
        return on_boundary and df.near(point[0], 1.0)

    boundaries = [
        df.DirichletBC(space, df.Constant(0.0), left),
        df.DirichletBC(space, df.Constant(parameters["alpha"]), right),
    ]
    stiffness = df.inner(df.grad(trial), df.grad(test)) * df.dx
    load = source * test * df.dx
    df.solve(stiffness == load, solution, boundaries)

    rows = []
    maximum_fe_difference = 0.0
    for observation in spec["observations"]:
        x = float(observation["x"])
        prediction = forward_value(x, parameters, physics)
        maximum_fe_difference = max(maximum_fe_difference, abs(float(solution(x)) - prediction))
        rows.append(
            {
                "x": x,
                "prediction": prediction,
                "observation": float(observation["value"]),
            }
        )
    payload = {
        "parameters": parameters,
        "predictions": rows,
        "fenics": {
            "dolfin_version": df.__version__,
            "mesh_cells": mesh.num_cells(),
            "element": "CG2",
            "maximum_fe_difference": maximum_fe_difference,
        },
    }
    output = ROOT / "predictions.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"dolfin={df.__version__}")
    print(f"maximum_fe_difference={maximum_fe_difference:.16g}")
    print(f"wrote={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
