# task-01 GUI test report

Result: VALIDATED-HARDENED-INIT

This report replaces the earlier hardening report. The init file is a natural editable IFC seed: it keeps the intended shell and existing BIM elements, but the spaces still have placeholder names and the final window objects are not present. The task now requires assigning the required room names and adding the required window objects before saving `result.ifc`.

Current init versus ground truth:

- Init spaces: ['Space 1']
- Required/ground-truth spaces: ['Room 101']
- Init windows: 0
- Required/ground-truth windows: 1
- Init and ground truth are not byte-identical.

Validation performed:

1. Ground truth copied to the expected result location passes this task's `eval.py`.
2. The current `init.ifc` copied directly as `result.ifc` fails this task's `eval.py`, so a trivial open/save or filename change is not enough.
3. A name-only variant made from `init.ifc` by changing the placeholder `IfcSpace.Name` values to ['Room 101'] still fails this task's `eval.py`, so the task cannot be completed by only renaming spaces.
4. Remote Bonsai GUI retest earlier confirmed the room-name editing and Save IFC Project As workflow on host 124.174.128.89. After the later unfinished-window adjustment, semantic validation confirms a name-only edit is no longer sufficient.

The task difficulty is now a normal Bonsai GUI completion step: assign the room program and add the required windows, then save through Bonsai's graphical IFC controls.
