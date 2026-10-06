# CLI task-01 completion record

## Snapshot boundary

- Snapshot: `kicad-openscad-freecad-blender`
- Instance private IP: `10.0.6.56`
- Evaluation date: 2026-08-13 (Asia/Shanghai)
- Observed tools: KiCad 10.0.4, OpenSCAD 2021.01, FreeCAD 1.1.0 revision 20260325, Blender 5.2.0 LTS.

## Task-specific repair

The evaluator previously compared recorded productive command paths with the
submission directory supplied by `ENGIWORLD_DESKTOP`. That rejected an
otherwise valid isolated audit because the real commands were executed on
`/home/user/Desktop`. The evaluator now keeps the submitted artifact root and
the recorded productive desktop as separate concepts. No init artifact was
changed.

## Snapshot validation

- Current real GT: `True`; detail: `PASS: task-01 artifacts satisfy the trusted semantic and geometry contract.`
- Reasonable equivalent: adding optional `audit_note` package metadata remained `True`.
- Targeted forgery: changing the KiCad productive-stage and package version
  from `10.0.4` to `10.0.40`, without changing the CAD artifacts, returned
  `False`; detail: `toolchain log lacks an ordered, versioned productive KiCad stage`.

Each case ran from a separate writable audit directory. Only a read-only
dependency installation was shared by the two variants.

## Cleanup

After copying the repaired local files and recording results, the base,
equivalent, and forged-version audit directories and the uploaded tar were
deleted. A follow-up instance probe reported `AUDIT_DIRS=0`,
`DESKTOP_ENTRIES=0`, and `RELATED_PROCESSES=0`.

## Official references

- https://www.kicad.org/blog/2026/06/KiCad-10.0.4-Release/
- https://docs.kicad.org/10.0/en/cli/cli.html
- https://dev-docs.kicad.org/en/file-formats/sexpr-pcb/
- https://github.com/openscad/openscad/releases/tag/openscad-2021.01
- https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.0
- https://wiki.freecad.org/Release_notes_1.1
- https://www.blender.org/releases/5-2/
- https://docs.blender.org/api/5.2/
