from floris import FlorisModel, UncertainFlorisModel
from floris.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR
import numpy as np

# TODO: 对比确定性优化与不确定性优化
# 工况：风向 270°，风速 8 m/s，TI=0.06
# 不确定性：风向标准差 wd_std=5°
