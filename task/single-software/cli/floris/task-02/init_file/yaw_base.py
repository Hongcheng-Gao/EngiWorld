from floris import FlorisModel
import numpy as np

fmodel = FlorisModel("init_file/two_turbine.yaml")

# TODO: Compare downstream power with and without yaw.
# Conditions: wind direction 270 degrees, speed 8 m/s, TI=0.06.
# Baseline: yaw_angles = [[0, 0]].
# Yaw case: yaw_angles = [[20, 0]] (upstream yaw of 20 degrees).

# Extract downstream (turbine 1) power in both cases.
