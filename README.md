[English](README.md) | [简体中文](README_CN.md)

<h1 align="center">EngiWorld</h1>
<p align="center"><strong>What Can Frontier Agents Deliver in Professional Engineering Environments?</strong></p>

<p align="center">
  <a href="https://engiworld.github.io/">🌐 Website</a> ·
  <a href="https://arxiv.org/abs/2609.37686">📄 Paper (arXiv)</a> ·
  <a href="task/">🧩 Tasks &amp; Verifiers</a> ·
  <a href="https://huggingface.co/datasets/HongchengGao/EngiWorld-Images">🤗 Environment Images</a>
</p>

<p align="center"><a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License"></a></p>

<p align="center"><a href="assets/engiworld-overview.png"><img src="assets/engiworld-overview.png" alt="EngiWorld task examples and engineering software coverage" width="100%"></a></p>

<p align="center"><em>Examples of cross-application workflows and software selection in EngiWorld. Click to enlarge.</em></p>

EngiWorld evaluates whether agents can operate professional engineering software and deliver the requested engineering artifacts. This repository provides all **1,301 tasks**, their evaluators, and the GUI/CLI evaluation runtime. The paper uses a 300-task main-experiment subset, listed in [`task/splits/main-300.txt`](task/splits/main-300.txt).

Local evaluation runs environment images through Docker on Linux, calls the model, and saves evaluation results.

## 💾 Installation

Prepare an x86_64 Linux server with Python 3.10, [Docker Engine](https://docs.docker.com/engine/install/), and `zstd`. With `/dev/kvm`, the VM uses hardware acceleration. Without it, the Docker runner attempts software emulation, which starts and runs more slowly. Each environment defaults to 4 CPUs and 16 GB RAM.

Get the code and enter the runtime directory:

```bash
git clone --branch main --single-branch --depth 1 https://github.com/Hongcheng-Gao/Engiworld.git &&
cd Engiworld/runtime
```

Install the runtime in a Python `venv` environment:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[worker-api]" huggingface_hub
```

Run the following commands from `runtime/`.

## 🚀 Quick start

This LibreCAD example shows how to prepare an environment, start a task, and run a model through scoring.

### 1. Download an environment image

Tasks run inside virtual machines with the corresponding engineering software installed. Download and decompress the LibreCAD image from the [Hugging Face environment image repository](https://huggingface.co/datasets/HongchengGao/EngiWorld-Images):

```bash
hf download HongchengGao/EngiWorld-Images \
  --repo-type dataset --local-dir ../environment-images \
  images/LibreCAD2.2.0.2.qcow2.zst &&
zstd -d ../environment-images/images/LibreCAD2.2.0.2.qcow2.zst
```

The decompressed image is saved to `../environment-images/images/LibreCAD2.2.0.2.qcow2`.

### 2. Start a task

Prepare the selected task's input and scoring resources:

```bash
python -m engiworld.prepare_tasks --task single-software/gui/librecad/task-08
```

```bash
python -m engiworld.local_eval \
  --task single-software/gui/librecad/task-08 \
  --image ../environment-images/images/LibreCAD2.2.0.2.qcow2 \
  --smoke-test
```

This starts the VM, loads the task inputs, and saves a `smoke.png` screenshot in the results directory without calling a model.

**Servers without KVM:** Check whether the server provides `/dev/kvm`:

```bash
test -e /dev/kvm && echo "KVM available" || echo "Software emulation"
```

If the output says `Software emulation`, run the same `--smoke-test` command above. The runtime selects software emulation automatically; no arguments need to change. Startup may take several minutes. When the terminal shows `"status": "environment_ready"` and `smoke.png` appears in the results directory, open the screenshot to confirm that LibreCAD and the input drawing are ready. Then follow step 3 to run and score a model.

### 3. Run a model and score the task

Configure an OpenAI-compatible Chat Completions endpoint and run the task:

```bash
export OPENAI_BASE_URL="https://your-api-endpoint/v1"
export OPENAI_API_KEY="your-api-key"

python -m engiworld.local_eval \
  --task single-software/gui/librecad/task-08 \
  --image ../environment-images/images/LibreCAD2.2.0.2.qcow2 \
  --model your-model-name \
  --result-dir results
```

When the run finishes, the terminal shows the result location. `summary.json` summarizes the run, `result.txt` holds the task score, and `traj.jsonl` records the model's actions. To run another task, use its task directory name or JSON ID as `--task`, prepare its resources with `engiworld.prepare_tasks --task`, and use the image named in its `snapshot` field. To download resources for all 1,301 tasks, run `python -m engiworld.prepare_tasks`. See the [runtime guide](runtime/README.md) for more options.

## Repository layout

```text
task/<category>/<gui|cli>/<software or software1--software2>/<task-number>/
runtime/
```

Task categories are `single-software`, `multi-software`, `software-selection`,
`quantitative-design`, `image-based-modeling`, and `open-ended`.
Open-ended tasks use **CLI** in a blank environment and live under
`task/open-ended/cli/agent-selected/`; the agent chooses and installs its tools.

Task JSON IDs follow `<category>--<gui|cli>--<software>--<task-number>--<os>`, for example
`single-software--gui--librecad--task-08--ubuntu`. Use either this ID or its task
directory path with `--task`. See the [task guide](task/README.md).

## 📊 Evaluation results

The main experiment evaluates seven models on the same 300 tasks. EngiScore is the mean task score on a 0–100 scale.

| Model | EngiScore |
| --- | ---: |
| Claude Opus 5 | **42.3** |
| GPT-5.6 Sol | 37.0 |
| Qwen3.8 Max | 25.8 |
| Gemini 3.7 Flash | 24.9 |
| DeepSeek V4.1 Flash | 24.8 |
| Kimi K3 | 24.1 |
| Qwen3.8 Flash | 15.8 |

## 📚 Citation

If you use EngiWorld in your research, please cite:

```bibtex
@misc{engiworld2026,
  title = {EngiWorld: What Can Frontier Agents Deliver in Professional Engineering Environments?},
  author = {Hongcheng Gao and Hailong Qu and Yu Lei and Henghui Sun and Haoyang Li and Yipeng Wei and Naihao Xue and Xiaohan Yu and Zhuo Tao and Yihe Zang and Yajiao Wang and Jingyi Tang and Yi Li and Jingjing Zhou and Jie Luo and Bohan Zeng and Chengyu Shen and Hao Jiang and Chong Chen and Bowen Qu and Olive Huang and Zeqiang Wang},
  year = {2026},
  eprint = {2609.37686},
  archivePrefix = {arXiv},
  primaryClass = {cs.AI},
  url = {https://arxiv.org/abs/2609.37686}
}
```

## 📄 License

EngiWorld's original code is released under the [MIT License](LICENSE). See [Third-party notices](THIRD_PARTY_NOTICES.md) for component licenses.
