# Remote Eval Report: eval-abaqus-multi-style-debug-task01

- Host: `115.190.187.244`
- Mode: `validate`
- Run dir: `/Users/weiyipeng/Documents/GitHub/Engiworld/task/task-v/cae-commercial-open-choice/validation/runs/eval-abaqus-multi-style-debug-task01`
- Passed: 0
- Failed or error: 1
- Final cleanup ok: True

## Results

- `task-01/abaqus`: fail, last='False', class=eval_failed, cleanup=ok

```
trying Abaqus-compatible branch
abaqus checker returncode=0
Abaqus-compatible branch did not pass
no acceptable solver branch passed
cannot iterate odb frames: arg1; found 'generator', expecting a recognized type
Traceback (most recent call last):
  File "C:/Users/user/Desktop/__open_choice_abaqus_checker.py", line 344, in select_abaqus_result_frame
    count = sum(1 for f in expected if f in names)
TypeError: arg1; found 'generator', expecting a recognized type

result has no frames
```
