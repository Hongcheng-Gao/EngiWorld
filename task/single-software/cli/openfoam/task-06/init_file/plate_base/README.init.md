[English](README.init.md) | [简体中文](README.init_CN.md)

# Task 6: plate_base initialization template

- Source: custom (plate boundary-layer topology)
- Purpose: Editable training template with `TODO_*` placeholders for key parameters; it is not a ready-to-run converged case.

## Notes

- The bottom boundary in `blockMeshDict` is split into `upstreamWall`, `plate`, and `downstreamWall`.
- The no-slip plate boundary is the `plate` patch in `0/U`.
- Velocity, viscosity, and time-step parameters retain `TODO_*` placeholders.
