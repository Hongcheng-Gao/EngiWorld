# Alibaba Cloud and Volcengine evaluation

Both providers use the same task runner, explicit model protocols, and Redis
master/worker queue. Use Linux and Python 3.10. Install
`pip install -e ".[worker-api,download,aliyun]"` for Alibaba Cloud, or
`pip install -e ".[worker-api,download]"` for Volcengine, then download task data.
Configure Alibaba credentials/network as described in [its guide](../aliyun/README.md),
or set the `VOLCENGINE_*` credentials, region, zone, subnet, security group and
instance type from `.env.example`. Images must contain compatible desktop services
and engineering applications. Private guests that install dependencies need NAT
or another outbound route, independently of the controller's connectivity.

## One task

```bash
python -m engiworld.cloud_eval --provider aliyun \
  --task-root ../data/task --task single-software-execution/cli/autocad/task-01 \
  --agent kimi-k3-max --max-tokens 16384 --result-dir results
```

Replace `aliyun` with `volcengine` for Volcengine. `--check` creates no instances;
`--smoke-test` runs no model. Named `--agent` presets select the model, reasoning
effort, token field and output allowance; use `--reasoning-effort` and
`--max-tokens` to override them explicitly. Custom models require
`--agent openai-compatible --model NAME --reasoning-effort none --max-tokens 16384`.
Set `OPENAI_BASE_URL` and `OPENAI_API_KEY` privately on controllers/workers.

API failures wait for an endpoint update using the existing
[hot-swap protocol](../../docs/runtime-api-hot-swap.md). Exhausted recovery records
`api_incomplete`, with a null score. Single runs retain that instance by default;
use `--no-retain-api-incomplete-instances` to release it. Retained instances incur
charges. Trajectories alone are not complete VM checkpoints.

Task timing stops before release starts. Cleanup failures preserve native scores.
`instances/` stores a durable request intent before creation, then the returned IDs.
Lost responses are reconciled by unique instance name; an unknown outcome remains
explicitly unconfirmed. Inspect these records and the cloud console for cleanup.
Alibaba's automatic release covers task time, the API recovery window and a margin;
it is a wall-clock safety deadline, not an indefinitely renewable pause budget.
Volcengine single runs need the controller to remain alive for automatic cleanup.

## Distributed batches

Start Redis, then run the master and workers in separate terminals. All hosts
must use the same reachable `REDIS_URL`, task data and model configuration.

```bash
python -m engiworld.scheduler.master start --cloud-provider aliyun \
  --run-id aliyun-demo --task-root ../data/task --task-id-file ../data/task/splits/main-306.txt \
  --agent kimi-k3-max --max-tokens 16384 --num-vms 40 --global-max-vms 80 \
  --max-attempts 1 --no-s3-upload --keep-local-results --follow
```

```bash
python -m engiworld.scheduler.worker --run-id aliyun-demo --task-root ../data/task \
  --local-concurrency 4 --no-s3-upload --keep-local-results
```

For Volcengine, change the provider and run ID; add `--use-baked-server` to use
the service in the image, or keep the existing service-bundle provisioning flow.
Instances must cover the selected snapshots. Multiple worker hosts share queue,
capacity, heartbeat, attempt and incomplete-result handling. Existing `status`,
`summary`, `reconcile`, `run` and `teardown` commands recover the persisted provider.
Configure the existing S3-compatible storage for centralized archives; these
examples preserve worker-local files. Explicit incomplete retries use a new run
ID and are fresh attempts, not checkpoint recovery. Failed or unknown cleanup
keeps request evidence and its capacity reservation until release is confirmed.
Alibaba batch instances default to a 30-hour safety release deadline, configurable
with `DEFAULT_TTL_MINUTES`; plan long queues and retained-instance costs accordingly.

To reconcile and release requests recorded by one run, use `python -m engiworld.cloud_cleanup --provider aliyun --journal-dir results/<run_id>/instances` (or `--provider volcengine`). Unknown creation outcomes remain failures until confirmed; this command never silently treats an empty lookup as proof of release.
