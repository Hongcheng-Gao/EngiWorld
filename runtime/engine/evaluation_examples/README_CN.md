[English](README.md) | [简体中文](README_CN.md)

# 评测示例

本目录存放用于评测智能体 GUI 交互能力的示例数据。示例位于 `./examples`，每条数据的格式如下：

```
{
    "id": "uid", # unique id
    "snapshot": "snapshot_id", # the snapshot id of the environment, with some data already there and apps already opened, or just desktop
    "instruction": "natural_language_instruction", # the natural language instruction of the task, what we want the agent to do
    "source": "website_url", # where we know this example, some forum, or some website, or some paper
    "config": {xxx}, # the scripts to setup the donwload and open files actions, as the initial state of a task
    # (coming in next project) "trajectory": "trajectory_directory", # the trajectory directory, which contains the action sequence file, the screenshots and the recording video
    "related_apps": ["app1", "app2", ...], # the related apps, which are opened during the task
    "evaluator": "evaluation_dir", # the directory of the evaluator, which contains the evaluation script for this example
…
}
```

`./trajectories` 包含 `./examples` 中各任务的已标注完成轨迹。

这组示例仍在建设中，目前只在 Windows 10 上测试过。运行时请调整路径；若有配置过度依赖原环境，请反馈。
