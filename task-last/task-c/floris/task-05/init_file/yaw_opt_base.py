from floris import FlorisModel
from floris.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR
import numpy as np

fmodel = FlorisModel("init_file/two_turbine.yaml")

# TODO: 执行偏航优化并对比功率提升
# 工况：风向 270°，风速 8 m/s
# 优化边界：yaw ∈ [-30°, 30°]
