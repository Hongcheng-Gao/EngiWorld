from floris import FlorisModel
import numpy as np

fmodel = FlorisModel("init_file/two_turbine.yaml")

# TODO: 对比无偏航与有偏航的下游功率
# 工况：风向 270°，风速 8 m/s，TI=0.06
# 基准：yaw_angles = [[0, 0]]
# 偏航：yaw_angles = [[20, 0]]（上游偏航 20°）

# 提取两种情况的下游（turbine 1）功率
