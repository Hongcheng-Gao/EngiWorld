# 阿里云与火山云评测

两种云使用同一任务执行器、模型预设，以及 Redis master/worker 调度和中断分类。
单任务入口负责创建实例、执行、保存结果和确认释放。批量入口使用集中队列、
全局并发额度、worker 心跳、独立 attempt 和结果汇总，不使用 shell 循环代替调度。

## 准备

控制端和 worker 使用 Linux、Python 3.10。阿里云安装 `pip install -e ".[worker-api,download,aliyun]"`；
火山安装 `pip install -e ".[worker-api,download]"`。完整下载任务：

```bash
python -m engiworld.prepare_tasks --source hf --task-root ../data/task
```

阿里云账号、共享镜像和网络配置见 [阿里云说明](../aliyun/README_CN.md)。
火山使用自己的私有或共享镜像，配置 `.env.example` 中的 `VOLCENGINE_*` 网络和账号字段；
镜像按任务 snapshot 名称匹配，也可在单任务入口指定 `--image-id`。
两云镜像均需预装对应工程软件及兼容的桌面服务；镜像名称匹配不代表已通过运行验收。
控制端及 worker 应能访问实例的 TCP 5000 和模型接口。私网实例若要安装软件或下载依赖，
还需要 NAT 等出网通道；仅开放控制端网络不能代替实例出网。

## 模型配置

使用 `--agent` 选择明确的预设，例如 `kimi-k3-max`、`gpt-5.6-sol-xhigh`、
`gemini-3.7-flash-high`。预设固定模型名、推理档位、额度字段和生成额度（默认 16384）。
可用 `--reasoning-effort max --max-tokens 32768` 显式覆盖。自定义模型需同时指定：

```bash
--agent openai-compatible --model your-model --reasoning-effort none --max-tokens 16384
```

`OPENAI_BASE_URL` 和 `OPENAI_API_KEY` 仅保存在控制端/worker 的受限环境配置中。
模型名及协议参数会记录到结果或运行计划；历史实验额度按其实际批次匹配。

## 单任务

```bash
python -m engiworld.cloud_eval --provider aliyun \
  --task-root ../data/task --task single-software-execution/cli/autocad/task-01 \
  --agent kimi-k3-max --max-tokens 16384 --result-dir results
```

火山使用完全相同的命令，把 `--provider aliyun` 改为 `--provider volcengine`。
`--smoke-test` 只验收环境，不调用模型；`--check` 只检查数据、配置和镜像，不创建实例。

API 重试耗尽后，默认等待运行目录 `model-api/<run_id>.json` 中的接口配置更新，
恢复后继续同一请求；详见 [接口更新](../../docs/runtime-api-hot-swap.md)。
等待额度耗尽会记为 `api_incomplete`、`score=null`，默认保留实例供人工检查；
`--no-retain-api-incomplete-instances` 可要求退出后释放。保留实例仍会计费，
且轨迹文件本身不等于可恢复的完整软件现场。

任务的活跃时间默认 18000 秒，已登记的接口等待不计入活跃时间。
评分结束即停止任务计时，实例释放单独处理。阿里云还设云端自动释放期限，
单任务默认覆盖任务预算、接口等待额度和一小时余量；云端期限是墙钟时间，
不会随无限次接口更新而无限延长。火山单任务需保持控制进程运行以完成释放。

`summary.json` 区分有效得分、API 中断、环境中断及释放错误。
清理失败不会覆盖已得到的分数。`instances/` 在创建请求发出前保存幂等标识、
实例名称和地域，成功后补充实例 ID。响应丢失会按唯一名称查询；查询不到时保留
“创建结果未知”，不宣称释放成功。检查这些文件及云控制台后再处理残留实例。

## 批量调度

先启动 Redis。在控制端执行以下命令，再在同一或其他 worker 主机执行下一条命令。
跨主机时为两者设置同一个可达的 `REDIS_URL`，并保持任务文件和模型配置一致。
初次使用可先把清单缩小，批量运行会创建收费实例。

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

多个 worker 可分别启动；它们共享队列和全局实例额度。40 个实例需覆盖清单中的全部
snapshot；master 会先核对所需环境数。阿里云默认使用镜像内服务。
火山把 provider 改为 `volcengine`，使用新 run ID；如同样使用镜像内服务，加
`--use-baked-server`，否则保留原火山的指定服务包部署流程。

两云的 `status`、`summary`、`reconcile`、`run`、`teardown` 均复用现有 master 命令，
后续操作按运行记录中的云类型选择后端。API/环境中断不算有效零分，也不自动无限重排；
明确检查后使用新的 run ID 和 `--retry-api-incomplete-from-run-id` 或
`--retry-infra-incomplete-from-run-id` 进行独立重试。该操作是新 attempt，不能当成原地续跑。
需要集中归档时，按原运行框架配置兼容 S3 的对象存储并启用上传；示例保留 worker 本地结果。

阿里云批量实例默认设 30 小时自动释放期限，可由 `DEFAULT_TTL_MINUTES` 设置。
长队列或长时间保留现场应提前规划期限和成本。创建、启动或释放异常时，保留
实例请求日志和额度占用，未确认释放前不会把资源额度当作已经归还。

检查后，可用 `python -m engiworld.cloud_cleanup --provider aliyun --journal-dir results/<run_id>/instances` 按某一次运行的记录确认并释放实例；火山改用 `--provider volcengine`。未知创建结果在未确认前仍返回失败，不会因一次空查询而被当作已释放。
