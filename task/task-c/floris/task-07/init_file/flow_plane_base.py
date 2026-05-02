from floris import FlorisModel
import numpy as np

fmodel = FlorisModel("init_file/two_turbine.yaml")
fmodel.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
fmodel.run()

# TODO: 提取水平切面并保存数据
# plane = fmodel.calculate_horizontal_plane(...)
# 提取尾流中心线速度亏损
