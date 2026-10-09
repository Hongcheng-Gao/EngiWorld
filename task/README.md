[English](README.md) | [简体中文](README_CN.md)

# EngiWorld tasks

The 1,301 tasks use a common directory layout:

```text
<category>/<gui|cli>/<software or software1--software2>/<task-number>/
```

| Directory category | Paper task type | Full tasks |
|---|---|---:|
| `single-software-execution` | Single-Software Execution | 931 |
| `software-selection` | Software Selection | 140 |
| `vision-guided-modeling` | Vision-Guided Modeling | 120 |
| `design-optimization` | Design Optimization | 40 |
| `cross-software-coordination` | Cross-Software Coordination | 60 |
| `open-environment-engineering` | Open-Environment Engineering | 10 |

Software names are lowercase, without version numbers. Multiple names are joined
with `--`. Open-Environment Engineering tasks use `cli/agent-selected/`. Interface folders contain
only the modes available in that category.

Each task contains a `task-*.json` definition, `init_file/` inputs, and its evaluator
(`eval.py`, with `ground_truth/` where required). IDs use
`<category>--<gui|cli>--<software>--<task-number>--<os>`; operating systems retain
`ubuntu` or `windows` from the task. Reverse-modeling tasks retain a `-reverse`
suffix on the task number to distinguish them from same-numbered tasks.

From `../runtime/`, run `python -m engiworld.prepare_tasks` to download task resources.
Use either a task directory or its JSON ID with `python -m engiworld.local_eval --task`.
Follow the [quick start](../README.md) to run an evaluation.

The paper's 306-task main-experiment subset is listed in [`splits/main-306.txt`](splits/main-306.txt). The scheduler accepts it through `--task-id-file ../task/splits/main-306.txt`.

Directory categories and JSON IDs follow the updated paper taxonomy as of 2026-10-09. `task/aliases.json` preserves historical JSON IDs and directory names; the runtime continues to accept them for task selection. See the full [ID migration map](id-migration-20261009.json) and [task taxonomy](taxonomy.json).
