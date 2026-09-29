[English](README.md) | [简体中文](README_CN.md)

# Pointer 智能体集成

## 配置

1. 创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 配置 API 密钥环境变量。

AWS Bedrock 推理还需要指定 `BEDROCK_ROLE_ARN` 和 `AWS_BEDROCK_REGION`：

```.env
# Required for AWS worker node creation
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
AWS_SUBNET_ID=your_subnet_group_id
AWS_SECURITY_GROUP_ID=your_security_group_id

# Needed for web_fetch and web_search tool
PARALLEL_API_KEY=your_parallel_api_key

# Needed for accurate token counting
ANTHROPIC_API_KEY=your_anthropic_api_key

# Needed for inference via Bedrock
BEDROCK_ROLE_ARN=bedrock_inference_role
AWS_BEDROCK_REGION=bedrock_inference_aws_region
```

3. 执行以下脚本，评测除 Google Drive 任务外的完整示例集：

```bash

python scripts/python/run_multienv_pointer.py \
    --max_steps 100 \
    --num_envs 40 \
    --test_all_meta_path evaluation_examples/test_nogdrive.json \
    --result_dir ./results/run-pointer-agent
```

## 项目来源

该智能体参考了本代码库及 OSWorld 生态中的 Anthropic、VLAA、Hippo、OpenAPA 和 Agent S3 等实现。
