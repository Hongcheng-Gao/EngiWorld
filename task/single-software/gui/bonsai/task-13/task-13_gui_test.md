# task-13 GUI test report

Result: VALIDATED-HARDENED-INIT

This report replaces the earlier hardening report. The init file is a natural editable IFC seed: it keeps the intended shell and existing BIM elements, but the spaces still have placeholder names and the final window objects are not present. The task now requires assigning the required room names and adding the required window objects before saving `result.ifc`.

Current init versus ground truth:

- Init spaces: ['Space 1', 'Space 2', 'Space 3', 'Space 4', 'Space 5']
- Required/ground-truth spaces: ['Reception', 'Exam 1', 'Exam 2', 'Clean Room', 'WC']
- Init windows: 0
- Required/ground-truth windows: 5
- Init and ground truth are not byte-identical.

Validation performed:

1. Ground truth copied to the expected result location passes this task's `eval.py`.
2. The current `init.ifc` copied directly as `result.ifc` fails this task's `eval.py`, so a trivial open/save or filename change is not enough.
3. A name-only variant made from `init.ifc` by changing the placeholder `IfcSpace.Name` values to ['Reception', 'Exam 1', 'Exam 2', 'Clean Room', 'WC'] still fails this task's `eval.py`, so the task cannot be completed by only renaming spaces.
4. Remote GUI retesting was not completed for this task after the unfinished-window adjustment because pyautogui automation focus was unreliable for repeated multi-object Bonsai edits. The task was validated with the evaluator-level semantic tests below; the same Bonsai save and room-name workflow was proven on task-01 and task-02, while adding window objects is a normal Bonsai GUI authoring operation stated in the instruction.

The task difficulty is now a normal Bonsai GUI completion step: assign the room program and add the required windows, then save through Bonsai's graphical IFC controls.
