from dolfin import *
import json
from pathlib import Path

mesh = UnitSquareMesh(48, 48)
V = FunctionSpace(mesh, "P", 1)
u = TrialFunction(V)
v = TestFunction(V)
u_old = interpolate(Expression("exp(-120*pow(x[0]-0.25,2))", degree=2), V)
k = Constant(0.9)
dt = Constant(0.01)
source = Expression("500*exp(-100*((x[0]-0.3)*(x[0]-0.3)+(x[1]-0.5)*(x[1]-0.5)))", degree=2)
a = u*v*dx + dt*k*dot(grad(u), grad(v))*dx
L = (u_old + dt*source)*v*dx
bcs = [DirichletBC(V, Constant(25.0), "near(x[0],0.0)"),
       DirichletBC(V, Constant(25.0), "near(x[0],1.0)")]
solution = Function(V, name="pulse")
for step in range(20):
    solve(a == L, solution, bcs)
    u_old.assign(solution)
result = {"center_value": float(solution(Point(0.5,0.5))),
          "mean_value": float(assemble(solution*dx)), "steps": 20}
Path(__file__).with_name("result.json").write_text(json.dumps(result))
File(str(Path(__file__).with_name("pulse.pvd"))) << solution
