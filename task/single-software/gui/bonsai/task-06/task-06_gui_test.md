# Bonsai task-06: task inputs and verifier

The initial IFC is an editable building model. The agent assigns the required room names, adds the windows, and saves `result.ifc`.

| Item | Initial IFC | Required result |
| --- | --- | --- |
| Room names | 'Space 1' | 'Room 201' |
| Window objects | 0 | 1 |

## Verifier checks

- The reference IFC passes `eval.py`.
- The unchanged initial IFC receives a failing score.
- Changing only room names receives a failing score; the window objects are also required.

A complete GUI replay is not recorded for this task configuration. The checks above cover the submitted IFC and the task verifier.
