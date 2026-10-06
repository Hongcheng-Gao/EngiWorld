[English](README.md) | [简体中文](README_CN.md)

# aworldGUIAgent-v1

aworldGUIAgent-v1 基于 [AWorld Framework](https://github.com/inclusionAI/AWorld)，用于 [OSWorld-verified](https://os-world.github.io/) 中的复杂桌面自动化任务。其感知和推理逻辑改编自 [Agent-S](https://github.com/simular-ai/Agent-S)，并增加了可执行工具。

## 快速开始

1. 创建 Python 3.11 Conda 环境：

       ```bash
       conda create -n osworld_env python=3.11
       conda activate osworld_env
       ```

然后按 [OSWorld README](https://github.com/xlang-ai/OSWorld) 安装依赖。

2. 在同一环境中安装指定版本的 AWorld：

         ```bash
         # Make sure your osworld_env is still activated
         git clone https://github.com/inclusionAI/AWorld.git
         cd AWorld
         git checkout osworld_benchmark
         python setup.py install
         ```

3. 运行评测。原配置通过 OpenRouter 使用 `openai/o3` 推理和 `bytedance/ui-tars-1.5-7b` 视觉定位。将 API 密钥、端点和 `/path/to/your/vm/Ubuntu.vmx` 替换为实际配置：

    ```bash
    # Activate your OSWorld conda environment (e.g., osworld_env)
    conda activate osworld_env

    # Run the evaluation with the recommended settings
    python run_multienv_aworldguiagent.py \
        --headless \
        --ground_url YOUR_BASE_URL \
        --ground_api_key YOUR_API_KEY \
        --ground_model bytedance/ui-tars-1.5-7b \
        --ground_provider open_router \
        --model_url YOUR_BASE_URL \
        --model_api_key YOUR_API_KEY \
        --model_temperature 1.0 \
        --provider_name vmware \
        --path_to_vm /path/to/your/vm/Ubuntu.vmx \
        --max_steps 50 \
        --model_provider open_router \
        --model openai/o3 \
        --grounding_width 1920 \
        --grounding_height 1080 \
        --test_all_meta_path evaluation_examples/test_all.json \
        --result_dir ./results \
        --observation_type screenshot \
        --num_envs 1 \
        --region us-east-1 \
        --client_password osworld-public-evaluation
    ```

## 项目来源

- [AWorld Framework](https://github.com/inclusionAI/AWorld)：用于智能体训练和多智能体应用的平台。
- [Agent-S](https://github.com/simular-ai/Agent-S)：提供基础智能体架构，该实现增加了环境交互工具。
- [OSWorld](https://os-world.github.io/)：该适配器原始 GUI 评测所使用的基准。
