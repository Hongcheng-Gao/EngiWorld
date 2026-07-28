from dolfin import *
import json
from pathlib import Path

mesh = UnitSquareMesh(96, 96)
V = FunctionSpace(mesh, "P", 1)
u = TrialFunction(V)
v = TestFunction(V)
k = Constant(58000000.0)
a = k*dot(grad(u),grad(v))*dx
source = Expression("0.0", degree=2)
L = source*v*dx
bcs = [DirichletBC(V, Constant(0.0), "near(x[0],0.0)"),
       DirichletBC(V, Constant(0.05), "near(x[0],1.0)")]
solution = Function(V, name="em_line")
solve(a == L, solution, bcs)
result = {"center_value": float(solution(Point(0.5,0.5))),
          "mean_value": float(assemble(solution*dx)),
          "energy": float(assemble(dot(grad(solution),grad(solution))*dx))}
Path(__file__).with_name("result.json").write_text(json.dumps(result))
File(str(Path(__file__).with_name("em_line.pvd"))) << solution
