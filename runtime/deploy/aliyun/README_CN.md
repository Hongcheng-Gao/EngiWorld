# 在阿里云运行 EngiWorld

使用共享镜像创建评测环境。源码负责加载任务、调用模型、收集工程成果和评分；镜像提供 Windows 或 Ubuntu 桌面及任务所需的软件。每次评测创建一台独立实例，结束后释放，评分和轨迹保存在运行源码的服务器上。

## 1. 获取镜像

向项目维护者提供你的**阿里云主账号 ID**，获得北京地域的镜像共享权限。进入 ECS 控制台，将地域切换到**华北 2（北京）**，在“镜像 → 共享镜像”查看。

[镜像清单](images.json)按任务 JSON 中的 `snapshot` 对应环境，程序会在你的账号中查找对应的共享镜像。也可以在命令中通过 `--image-id` 指定自己准备的镜像。镜像与创建的实例必须位于同一地域。

## 2. 准备运行源码的服务器

准备一台北京地域的 Linux ECS，安装 Python 3.10。它负责调用云接口和模型，4 核、8 GB 内存即可作为起点；工程软件运行在程序另外创建的评测实例中。

在 ECS 控制台记录这台服务器所在的 **VPC、交换机 ID**，并为评测实例创建一个属于同一 VPC 的安全组。在该安全组中允许运行源码的服务器的**私网 IP/32 访问 TCP 5000**。需要查看远程桌面时，再放行 TCP 5910。程序使用私网控制评测实例，运行源码的服务器还需能访问阿里云 API 和模型接口。

```bash
git clone --branch aliyun-evaluation --single-branch https://github.com/Hongcheng-Gao/EngiWorld.git
cd EngiWorld/runtime
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[worker-api,download,aliyun]"
```

下面的命令都在 `runtime/` 中执行。

## 3. 配置自己的账号和网络

```bash
cp deploy/aliyun/config.env.example config.aliyun.env
chmod 600 config.aliyun.env
```

编辑 `config.aliyun.env`，填写自己的 RAM AccessKey、交换机、安全组和模型接口。RAM 用户需要查询镜像、创建/查询/启动/释放 ECS 实例的权限。

```bash
source config.aliyun.env
```

默认规格为 `ecs.u1-c1m4.xlarge`（4 核、16 GB）。程序按镜像大小设置系统盘，并从镜像恢复附带的数据盘，继承镜像登录设置，并配置自动释放时间。按量实例、系统盘及模型调用由使用者的账号付费。

如果源码服务器通过公网访问评测实例，设置 `ALIYUN_USE_PRIVATE_IP=0`、`ALIYUN_PUBLIC_BANDWIDTH=10`，并将上述安全组来源改为源码服务器的公网 IP/32。

## 4. 下载任务

下面以 AutoCAD 的 CLI 制图任务为例：

```bash
python -m engiworld.prepare_tasks --source hf \
  --task-root ../data/task \
  --task single-software-execution/cli/autocad/task-01
```

也可以使用 `--source modelscope` 下载。云端运行直接使用共享镜像，任务数据下载到源码服务器。

## 5. 运行并评分

```bash
python -m engiworld.cloud_eval \
  --task-root ../data/task \
  --task single-software-execution/cli/autocad/task-01 \
  --agent kimi-k3-max --max-tokens 16384 \
  --result-dir results
```

程序依次完成：**从对应镜像创建实例 → 上传任务输入 → 模型执行 → 评分器检查工程成果 → 保存结果 → 释放实例**。

终端最后显示结果目录。`summary.json` 汇总任务得分、错误信息和实例释放状态；任务子目录中的 `result.txt` 保存得分，`traj.jsonl` 保存交互轨迹。

只检查环境是否能启动和加载任务时，在同一命令中使用 `--smoke-test` 代替 `--agent kimi-k3-max --max-tokens 16384`。这会保存 `smoke.png` 截图，不调用模型；正常的模型评测使用上面的完整命令。

更换任务时修改 `--task`。程序按镜像清单选择环境；使用自有镜像时增加 `--image-id m-your-image-id`。每个任务使用一台独立实例。

## 批量评测

批量运行使用统一 Redis master/worker 队列，参见[两云批量调度](../cloud/README_CN.md)。

API 中断默认等待接口更新，超时后记为未完成且默认保留实例。保留实例仍计费；释放选项、请求追踪及故障处理以[云端说明](../cloud/README_CN.md)为准。
