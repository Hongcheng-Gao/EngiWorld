[English](README.init.md) | [简体中文](README.init_CN.md)

# Task 14: snappy_base initialization template

- Source: OpenFOAM-10/tutorials/mesh/snappyHexMesh/pipe + generated cylinder STL
- Purpose: Editable training template with `TODO_*` placeholders for key parameters; it is not a ready-to-run converged case.

## Notes

- `constant/triSurface/cylinder.stl` is supplied: diameter 0.1 m, length 0.01 m, centered at (0.5, 0.5, 0).
- `snappyHexMeshDict` references the supplied `cylinder.stl`.
- Layer and refinement settings retain `TODO_*` placeholders.
