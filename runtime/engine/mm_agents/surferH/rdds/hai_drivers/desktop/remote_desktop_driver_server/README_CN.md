[English](README.md) | [简体中文](README_CN.md)

# 远程桌面服务

此服务部署并运行在 AMI（Amazon Machine Image）环境中。FastAPI 服务通过 pyautogui 提供远程桌面控制接口。

## 开始使用

1. 将 `hai_drivers/interfaces` 复制到远端机器的专用目录。
2. 将 `hai_drivers/desktop/remote_desktop_driver_server` 也复制到专用目录，保持服务与接口之间的相对目录结构。
3. 在远端安装 uv。
4. 进入服务目录并安装依赖：

```bash
$ cd desktop/remote_desktop_driver_server
$ uv sync
```

5. 激活环境并启动服务：

```bash
$ python src/server.py --host 0.0.0.0 --port 8000
```
