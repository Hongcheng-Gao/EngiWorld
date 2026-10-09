from floris import FlorisModel
from floris.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR
import numpy as np

fmodel = FlorisModel("init_file/two_turbine.yaml")

# TODO: Optimize yaw and compare the power increase.
# Operating condition: wind direction 270 degrees, wind speed 8 m/s.
# Optimization bounds: yaw in [-30 degrees, 30 degrees].
