[English](README.md) | [简体中文](README_CN.md)

# EngiWorld tasks

The 1,301 tasks use a common directory layout:

```text
<category>/<gui|cli>/<software or software1--software2>/<task-number>/
```

| Directory category | Paper task type |
|---|---|
| `single-software` | Single-Software Execution |
| `software-selection` | Software Selection |
| `image-based-modeling` | Vision-Guided Modeling |
| `quantitative-design` | Design Optimization |
| `multi-software` | Cross-Software Coordination |
| `open-ended` | Open-Environment Engineering |

Software names are lowercase, without version numbers. Multiple names are joined
with `--`. Open-ended tasks use `cli/agent-selected/`. Interface folders contain
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
