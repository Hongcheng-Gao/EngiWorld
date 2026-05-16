# `_common/` — shared evaluation plumbing

Every task's `eval.py` talks to the running OrCAD Capture via two files here:

| File              | Role                                                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------- |
| `worker.tcl`      | long-lived Tcl loop that watches `_worker_queue/`, sources any `*.tcl` job dropped in, moves to `done/` |
| `run_in_capture.py` | Python helper; writes the job TCL, waits for the verdict file to appear                           |

## Startup (once per Capture session)

```
source D:/localwork/orcad/tasks/_common/worker.tcl
::engiworld::worker::start
```

You should see `[engiworld worker] started; watching D:/localwork/orcad/tasks/_worker_queue` in the Command Window. Leave Capture open.

## Running one task's eval.py

```powershell
D:\anaconda\python.exe D:\localwork\orcad\tasks\task-01\eval.py `
    D:\path\to\output_dir
```

The eval.py generates a small TCL blob, queues it, waits, and prints `PASS` / `FAIL` with details.

## Why a worker loop rather than launching Capture per call?

Capture.exe requires a Cadence Okta login on cold start, consumes a license
seat per instance, and holds MS-Office-style global state. Spinning up a new
process per evaluation would be unusably slow and would hit the license
server every time. Dropping Tcl jobs into one long-lived interpreter
sidesteps all of that.
