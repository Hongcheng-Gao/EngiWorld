from dolfin import *
import json
from pathlib import Path

mesh = UnitSquareMesh(72, 72)
V = FunctionSpace(mesh, "P", 1)
u = TrialFunction(V)
v = TestFunction(V)
k = Constant(0.25)
a = k*dot(grad(u),grad(v))*dx + Constant(1.0)*u*v*dx
source = Expression("20*exp(-100*(x[1]-0.5)*(x[1]-0.5))", degree=2)
L = source*v*dx
bcs = [DirichletBC(V, Constant(0.0), "near(x[0],0.0)"),
       DirichletBC(V, Constant(0.0), "near(x[0],1.0)")]
solution = Function(V, name="photonics")
solve(a == L, solution, bcs)
result = {"center_value": float(solution(Point(0.5,0.5))),
          "mean_value": float(assemble(solution*dx)),
          "energy": float(assemble(dot(grad(solution),grad(solution))*dx))}
Path(__file__).with_name("result.json").write_text(json.dumps(result))
File(str(Path(__file__).with_name("photonics.pvd"))) << solution
