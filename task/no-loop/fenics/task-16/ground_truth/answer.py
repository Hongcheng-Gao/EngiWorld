from dolfin import *
import json
from pathlib import Path

mesh = UnitSquareMesh(64, 64)
V = FunctionSpace(mesh, "P", 1)
u = TrialFunction(V)
v = TestFunction(V)
k = Constant(120.0)
a = k*dot(grad(u),grad(v))*dx
source = Expression("10000*exp(-120*((x[0]-0.7)*(x[0]-0.7)+(x[1]-0.5)*(x[1]-0.5)))", degree=2)
L = source*v*dx
bcs = [DirichletBC(V, Constant(25.0), "near(x[0],0.0)"),
       DirichletBC(V, Constant(25.0), "near(x[0],1.0)")]
solution = Function(V, name="power")
solve(a == L, solution, bcs)
result = {"center_value": float(solution(Point(0.5,0.5))),
          "mean_value": float(assemble(solution*dx)),
          "energy": float(assemble(dot(grad(solution),grad(solution))*dx))}
Path(__file__).with_name("result.json").write_text(json.dumps(result))
File(str(Path(__file__).with_name("power.pvd"))) << solution
