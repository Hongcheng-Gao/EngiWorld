[English](README.md) | [简体中文](README_CN.md)

# EngiWorld runtime

See the [quick start](../README.md#-quick-start) for installation, image downloads,
and local evaluation. This page covers runtime settings and cloud scheduling.
Run commands from this directory.

## Runtime settings

Run local evaluations with `python -m engiworld.local_eval`. Each environment defaults
to 4 CPUs, 16 GB RAM, and a 200 GB virtual disk. Override these with
`ENGIWORLD_DOCKER_CPU_CORES`, `ENGIWORLD_DOCKER_RAM_SIZE`, and
`ENGIWORLD_DOCKER_DISK_SIZE`. Set the guest user password with `--client-password`
or `ENGIWORLD_CLIENT_PASSWORD`.

| Setting | Default |
|---|---|
| Desktop resolution | 1920x1080, calibrated and verified before and after initialization |
| History turns | 15 |
| Regular GUI / CLI turn limit | 200 / 100 |
| Cross-Software Coordination GUI / CLI turn limit | 300 / 150 |
| Open-Environment Engineering turn limit | 150 |
| Active time per task | 5 hours (18000 seconds) |

Set the local time limit with `--task-timeout`, or the cloud limit with the master's
`--task-run-timeout-seconds` / `TASK_RUN_TIMEOUT_SECONDS`. Local timing includes VM
startup, initialization, model requests, actions, and evaluation. Registered pause
intervals are deducted, overlapping pauses count only once, and elapsed active time
is retained on resume. Agent WAIT actions and request retries count toward the budget.

Active-time exhaustion records `completed / 0`, `active_time_budget_exhausted`, and
`native_evaluator_executed=false`. API interruptions and environment failures are
recorded separately. Evaluator execution failures record `infra_incomplete` with
a `null` score. Results include `wall_duration_seconds`, `paused_seconds`, and
`active_duration_seconds`.

## Cloud scheduling

Volcengine ECS scheduling uses Redis to coordinate tasks and object storage to save
results. Configure resources with [`.env.example`](.env.example) and deploy using
[`deploy/`](deploy/). Cloud execution uses custom image IDs. Both master and worker
must point `--task-root` / `TASK_ROOT` to `../task` and have task resources prepared.

## Shared model interface

All models use `engiworld.agents.openai_compatible:create_agent` through an
OpenAI-compatible Chat Completions API. Configure a model name and endpoint to add
a model.

Set `OPENAI_BASE_URL` and `OPENAI_API_KEY` in the worker environment, then select
the model on the master:

```bash
python -m engiworld.scheduler.master plan \
  --task-root ../task --task-limit 1 --num-vms 1 \
  --agent openai-compatible \
  --agent-env ARENA_MODEL_NAME=your-model-name
```

`plan` prints the selected tasks and model configuration. `scheduler.master`
assigns tasks, and `scheduler.worker_entrypoint` runs the model and evaluators.

| Setting | Environment variable | Default |
|---|---|---|
| Endpoint | `OPENAI_BASE_URL` (also `ARENA_MODEL_BASE_URL`) | Set your endpoint |
| API key | `OPENAI_API_KEY` | Set on the worker |
| API model name | `ARENA_MODEL_NAME` | Required for the generic adapter; filled by presets |
| Output token limit | `ARENA_MODEL_MAX_TOKENS` | **16384 for all models** |
| Token-limit field | `ARENA_MODEL_TOKEN_LIMIT_FIELD` | `max_tokens`; also supports `max_completion_tokens` |
| Reasoning effort | `ARENA_MODEL_REASONING_EFFORT` | Unset for the generic adapter; presets retain their setting |
| Reasoning field | `ARENA_MODEL_REASONING_FIELD` | `reasoning_effort`; also supports `reasoning` and `none` |
| Request timeout | `ARENA_MODEL_TIMEOUT_SECONDS` | 600 seconds |
| Request attempts | `ARENA_MODEL_API_RETRIES` | 3, including the first attempt |
| Streaming | `ARENA_MODEL_STREAM` | `true` |

Actions execute only after a complete streamed response. Interrupted or invalid
responses are retried; exhaustion records an API interruption.

## Vision-Guided Modeling

Reference images for `vision-guided-modeling/` tasks live in `init_file/`. Download
them with `python -m engiworld.prepare_tasks`. The runtime includes the images in
model messages by default, using `gui_message_initial` for GUI tasks and
`cli_message_initial` for CLI tasks.

## Open-Environment Engineering

`open-environment-engineering/` uses the blank `top-10` base image without preinstalled engineering
applications. The model chooses, installs, and configures tools, using terminal
observations and the `open_engineering` interaction profile.

Geometry evaluation requires FreeCAD. The runtime checks and installs this dependency
after the model finishes. The image must support noninteractive sudo and access
to Ubuntu package repositories.
