# Task 16 shockTube_base init template

- Source: /new_home/weiyipeng/OpenFOAM-10-master/tutorials/compressible/rhoCentralFoam/shockTube (adapted to 1 m tube)
- Purpose: 训练用可编辑缺口模板，保留关键参数 TODO_*，不是直接收敛的成品算例。
- Notes:
- 网格已改为 1m 管道、1000 轴向单元。- 初始间断通过 setFieldsDict 占位 (TODO_LEFT_P/T, TODO_RIGHT_P/T)。- 时间设置保留 TODO_*。
