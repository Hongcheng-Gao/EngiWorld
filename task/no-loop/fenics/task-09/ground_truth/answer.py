from dolfin import *
import json
from pathlib import Path

mesh = UnitSquareMesh(64, 64)
V = FunctionSpace(mesh, "P", 1)
u = TrialFunction(V)
v = TestFunction(V)
K = as_matrix(((400.0,0.0),(0.0,130.0)))
a = inner(K*grad(u),grad(v))*dx
source = Expression("1500*exp(-160*(x[0]-0.5)*(x[0]-0.5))", degree=2)
L = source*v*dx
bcs = [DirichletBC(V, Constant(100.0), "near(x[0],0.0)"),
       DirichletBC(V, Constant(25.0), "near(x[0],1.0)")]
solution = Function(V, name="tsv")
solve(a == L, solution, bcs)
result = {"center_value": float(solution(Point(0.5,0.5))),
          "mean_value": float(assemble(solution*dx)),
          "energy": float(assemble(dot(grad(solution),grad(solution))*dx))}
Path(__file__).with_name("result.json").write_text(json.dumps(result))
File(str(Path(__file__).with_name("tsv.pvd"))) << solution
