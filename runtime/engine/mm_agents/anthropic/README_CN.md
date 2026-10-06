[English](README.md) | [简体中文](README_CN.md)

# Anthropic 智能体集成

此适配器将截图缩放为 1280×720，以适应原配置采用的图像长边 1568 像素及约 1600 图像 token 的限制。

## 配置

1. 安装所需依赖：

```bash
pip install anthropic
```

2. 在 `.env` 中配置 API 密钥等环境变量。

AWS Bedrock：

```.env
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
```

直接使用 Anthropic 时，将 `APIProvider` 设置为 `anthropic`，并配置 API 密钥：

```.env
ANTHROPIC_API_KEY=your_anthropic_api_key
```
