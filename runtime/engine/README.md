[English](README.md) | [简体中文](README_CN.md)

# EngiWorld environment engine

This directory implements the environment and execution layer used by EngiWorld.
Install and run the framework from the parent [runtime directory](../README.md),
or follow the repository [quick start](../../README.md).

- `desktop_env/`: environment lifecycle, providers, task initialization, observations, actions, and evaluation integration.
- `lib_run_single.py`: the GUI/CLI task loop, trajectory recording, terminal actions, and final-artifact evaluation.
- `mm_agents/cli_policy.py`: engineering CLI tool and artifact-integrity policies.
- `mm_agents/`: interaction prompts, reference-image profiles, parsing, and agent utilities. The shared model adapter is in [`src/engiworld/agents/`](../src/engiworld/agents/).
- [`../../task/`](../../task/): EngiWorld task definitions, inputs, and engineering-artifact evaluators.

Run evaluations with `python -m engiworld.local_eval` from the parent
`runtime/` directory. See [third-party notices](../../THIRD_PARTY_NOTICES.md)
for component licenses.
