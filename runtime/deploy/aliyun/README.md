# Run EngiWorld on Alibaba Cloud

Shared images provide the desktop and engineering applications. The evaluation code loads a task, calls your model, evaluates the resulting artifacts, saves the score and trajectory, and releases its temporary ECS instance.

## 1. Obtain image access

Send your **Alibaba Cloud account ID** to the project maintainers. In the ECS console, select **China (Beijing)** and open **Images → Shared Images**. The [image catalog](images.json) maps each task's `snapshot` to its image. The evaluator finds the matching shared image in your account. Use `--image-id` to select your own image.

## 2. Install the code

Use a Linux ECS controller in the same Beijing VPC as the evaluation instances. Python 3.10, 4 CPUs and 8 GB RAM are a starting configuration for this controller. Engineering applications run on separate instances created by the evaluation code.

Create a security group in that VPC, allowing TCP 5000 from the controller's private IP/32. Allow TCP 5910 as well if you want remote desktop access. The controller needs outbound access to the Alibaba Cloud API and your model endpoint.

```bash
git clone --branch aliyun-evaluation --single-branch https://github.com/Hongcheng-Gao/EngiWorld.git
cd EngiWorld/runtime
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[worker-api,download,aliyun]"
cp deploy/aliyun/config.env.example config.aliyun.env
chmod 600 config.aliyun.env
```

Fill in your RAM AccessKey, region, vSwitch ID, security group ID and model endpoint in `config.aliyun.env`, then load it:

```bash
source config.aliyun.env
```

The RAM identity needs permission to describe images and create, describe, start and delete ECS instances. The default instance type is `ecs.u1-c1m4.xlarge` (4 CPUs, 16 GB RAM). The system disk size and attached data disks follow the image. Temporary instances have an automatic release deadline; ECS, disk and model usage are billed to your account.

For a controller using public networking, set `ALIYUN_USE_PRIVATE_IP=0` and `ALIYUN_PUBLIC_BANDWIDTH=10`, and allow the controller's public IP/32 in the security group instead.

## 3. Run a task and obtain its score

Run these commands from `runtime/`:

```bash
python -m engiworld.prepare_tasks --source hf \
  --task-root ../data/task \
  --task single-software-execution/cli/autocad/task-01

python -m engiworld.cloud_eval \
  --task-root ../data/task \
  --task single-software-execution/cli/autocad/task-01 \
  --agent kimi-k3-max --max-tokens 16384 \
  --result-dir results
```

You can use `--source modelscope` for task downloads. The shared image supplies the cloud environment.

The command creates an instance, uploads task inputs, runs the agent, evaluates the artifacts and releases the instance. `summary.json` reports the score and release status. The task result directory contains `result.txt` and `traj.jsonl`.

To check environment startup without a model, replace `--agent kimi-k3-max --max-tokens 16384` with `--smoke-test`. This resets the task and saves `smoke.png`. To run another task, change `--task`; the image catalog selects its environment. Add `--image-id m-your-image-id` to use your own image.

## Batch evaluation

Use the shared Redis master/worker queue described in the [cloud guide](../cloud/README.md).

API recovery waits and retained incomplete instances incur cloud costs. See the [cloud guide](../cloud/README.md) for release policy and durable request tracking.
