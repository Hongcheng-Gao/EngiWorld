from floris import FlorisModel
import numpy as np

fmodel = FlorisModel("two_turbine.yaml")
fmodel.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
fmodel.run()

# TODO: 在轮毂高度沿 y=0、从第二台风机下游 1D 开始采样中心线速度
# 使用 sample_flow_at_points(...) 并计算达到 0.95 倍来流速度的恢复距离
