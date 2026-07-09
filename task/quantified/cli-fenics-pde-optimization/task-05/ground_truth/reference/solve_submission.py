#!/usr/bin/env python3
from __future__ import annotations

# Reference ground-truth workflow marker. The evaluator recomputes the metric
# from the submitted design variables with its own FEniCS/DOLFIN model.
import dolfin

print("reference ground-truth FEniCS workflow")
