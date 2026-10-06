[English](README.init.md) | [简体中文](README.init_CN.md)

# Task 19: porous_base initialization template

- Source: OpenFOAM-10/tutorials/incompressible/simpleFoam/pipeCyclic + porousSimpleFoam reference
- Purpose: Editable training template with `TODO_*` placeholders for key parameters; it is not a ready-to-run converged case.

## Notes

- The baseline solver is `porousSimpleFoam`, available in OpenFOAM 10.
- `constant/porosityProperties` and `system/topoSetDict` include placeholders.
- An alternative is `simpleFoam` with `fvOptions` (`explicitPorositySource`).
