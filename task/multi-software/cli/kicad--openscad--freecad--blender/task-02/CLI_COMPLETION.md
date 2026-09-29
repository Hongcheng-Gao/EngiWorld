# CLI task-02 completion record

## Snapshot boundary

- Snapshot: `kicad-openscad-freecad-blender`
- Instance private IP: `10.0.6.56`
- Evaluation date: 2026-08-13 (Asia/Shanghai)
- Observed tools: KiCad 10.0.4, OpenSCAD 2021.01, FreeCAD 1.1.0 revision 20260325, Blender 5.2.0 LTS.

## Task-specific repair

The evaluator now distinguishes the isolated submitted artifact root from the
real productive command directory `/home/user/Desktop`. The Python handoff
preparation invocation was also corrected from a false KiCad attribution to
`Python handoff generator`, with no software version claim; the release
package's log hash was updated accordingly. No init artifact changed.

## Snapshot validation

- Current real GT: `True`; detail: `PASS: task-02 artifacts satisfy the trusted semantic and geometry contract.`
- Reasonable equivalent: adding optional package review metadata remained `True`.
- Targeted forgery: changing both recorded OpenSCAD production versions and
  the package version from `2021.01` to `2021.011` returned `False`; detail:
  `toolchain log lacks a valid recorded OpenSCAD execution`.

All three checks used separate writable directories on the mapped snapshot.

## Cleanup

The base, equivalent, and forged-version audit directories and uploaded tar
were removed after validation. The post-cleanup probe reported zero audit
directories, zero Desktop entries, and zero related CAD processes.

## Official references

- https://www.kicad.org/blog/2026/06/KiCad-10.0.4-Release/
- https://docs.kicad.org/10.0/en/cli/cli.html
- https://github.com/openscad/openscad/releases/tag/openscad-2021.01
- https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.0
- https://wiki.freecad.org/Release_notes_1.1
- https://www.blender.org/releases/5-2/
- https://docs.blender.org/api/5.2/
