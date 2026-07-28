from dolfin import *
import json
from pathlib import Path

mesh = UnitSquareMesh(52, 52)
V = FunctionSpace(mesh, "P", 1)
u = TrialFunction(V)
v = TestFunction(V)
K = as_matrix(((2.5,0.0),(0.0,1.2)))
a = inner(K*grad(u),grad(v))*dx
source = Expression("800", degree=2)
L = source*v*dx
bcs = [DirichletBC(V, Constant(150.0), "near(x[0],0.0)"),
       DirichletBC(V, Constant(25.0), "near(x[0],1.0)")]
solution = Function(V, name="attach")
solve(a == L, solution, bcs)
result = {"center_value": float(solution(Point(0.5,0.5))),
          "mean_value": float(assemble(solution*dx)),
          "energy": float(assemble(dot(grad(solution),grad(solution))*dx))}
Path(__file__).with_name("result.json").write_text(json.dumps(result))
File(str(Path(__file__).with_name("attach.pvd"))) << solution
