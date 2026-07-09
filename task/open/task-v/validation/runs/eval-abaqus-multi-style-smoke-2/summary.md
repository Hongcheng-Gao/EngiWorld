# Remote Eval Report: eval-abaqus-multi-style-smoke-2

- Host: `115.190.187.244`
- Mode: `validate`
- Run dir: `/Users/weiyipeng/Documents/GitHub/Engiworld/task/task-v/cae-commercial-open-choice/validation/runs/eval-abaqus-multi-style-smoke-2`
- Passed: 3
- Failed or error: 1
- Final cleanup ok: True

## Results

- `task-01/abaqus`: pass, last='True', cleanup=ok

```
trying Abaqus-compatible branch
abaqus checker returncode=0
```
- `task-04/abaqus`: fail, last='False', class=eval_failed, cleanup=ok

```
trying Abaqus-compatible branch
abaqus checker returncode=0
Abaqus-compatible branch did not pass
no acceptable solver branch passed
action repositories empty; trying inp fallback
exported inp has no load/action cards: __open_choice_eval_inp.inp
no load/predefined/interactions/constraints evidence found
```
- `task-06/abaqus`: pass, last='True', cleanup=ok

```
trying Abaqus-compatible branch
abaqus checker returncode=0
```
- `task-13/abaqus`: pass, last='True', cleanup=ok

```
trying Abaqus-compatible branch
abaqus checker returncode=0
```
