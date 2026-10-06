# Updating model endpoints during a run

Evaluation supports updating the endpoint and key of an OpenAI-compatible model
per run. Each worker reads `<RUN_ID>.json` from
`ARENA_OPENAI_COMPAT_RUNTIME_CONFIG_DIR`, which defaults to `model-api/` under
the worker working directory.

Requests normally use the model configuration loaded when the worker starts.
If a request still fails after the normal retries, the task waits for its JSON
configuration to change and then retries with the updated endpoint configuration.
`ARENA_OPENAI_COMPAT_HOTSWAP_WAIT_SECONDS` and
`ARENA_OPENAI_COMPAT_HOTSWAP_POLL_SECONDS` control the wait limit and polling interval.

The file can contain `base_url` and `api_key`. Restrict access to the worker account
and update the file through an atomic replacement.
`scripts/build_runtime_api_config.py` generates the configuration, and
`scripts/deploy_worker_env.sh` distributes it to workers. Supply the deployment
paths and host list for your installation. Read keys from a restricted local file;
do not commit them to the repository.

If the endpoint does not recover within the wait limit, the task records
`api_incomplete` and can be retried separately after inspection. This status is
reported separately from valid model scores.
