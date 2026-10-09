[English](README.init.md) | [简体中文](README.init_CN.md)

# Task 20: dynamic_base initialization template

- Source: OpenFOAM-10/tutorials/incompressible/pimpleFoam/laminar/offsetCylinder
- Purpose: Editable training template with `TODO_*` placeholders for key parameters; it is not a ready-to-run converged case.

## Notes

- The O-grid mesh contains an internal cylinder and supports the required moving-mesh field structure.
- `constant/dynamicMeshDict` contains an `oscillatingRotatingMotion` placeholder.
- `controlDict` selects `pimpleDyMFoam` and retains time-step placeholders.
