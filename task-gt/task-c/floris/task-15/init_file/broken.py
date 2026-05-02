from floris import FlorisModel
import numpy as np

fmodel = FlorisModel("init_file/two_turbine.yaml")

# 错误1: wind_directions 应为 numpy array 或 list，但这里传了标量
fmodel.set(wind_directions=270, wind_speeds=8, turbulence_intensities=0.06)

# 错误2: 未执行 run() 就直接提取功率
powers = fmodel.get_turbine_powers()

# 错误3: 输出路径未创建
np.savetxt("outputs/result.txt", powers)
