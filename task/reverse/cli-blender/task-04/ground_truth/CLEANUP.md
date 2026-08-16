# Instance cleanup

The `Blender-4.2.3` instance Desktop was empty before this task.

After the regenerated artifact had been downloaded and its SHA-256 matched,
the following task-created files were removed from `/home/user/Desktop`:

- the three uploaded init files
- the uploaded evaluator
- the task-specific generation script
- the old and regenerated `answer.blend` files
- the `audit/` directory containing the equivalent and negative cases

The final cleanup assertion checked all of the following and returned
`BLENDER_TASK04_CLEAN`:

- `/home/user/Desktop` had no remaining entries
- `/tmp` had no `reverse_blender_eval_*` directories
- no Blender process remained

The SSH/OSWorld forwarding session used for the private instance was then
terminated.

## Visual QA cleanup

A second, isolated forwarding session was opened after the formal repair to
render the downloaded GT for visual QA. The Desktop was confirmed empty before
the check. Only the hash-matched `answer.blend` and a task-specific render
script were uploaded; Blender 4.2.3 produced a 900 x 650 PNG showing the six
bores and centered pocket. The GT itself was not saved or otherwise changed by
this render.

The uploaded blend, render script, preview PNG, and a seven-byte transfer probe
were then removed by their exact paths. The final assertions confirmed an empty
Desktop and no running Blender process. No task-04 or Blender crash file was
found in the accessible portions of `/tmp`; protected system-service temporary
directories were not modified. The second forwarding session was terminated.

## Independent closure recheck

The final four-case evaluator matrix was rerun once more in the isolated
`/home/user/Desktop/engiworld_task04_recheck/` directory. That exact directory
was removed after validation. The closing assertions returned:

- `DESKTOP_COUNT=0`
- `TMP_COUNT=0` for `/tmp/reverse_blender_eval_*`
- `BLENDER_PROCS=0`

The dedicated SSH/OSWorld forwarding session was closed after these checks.
