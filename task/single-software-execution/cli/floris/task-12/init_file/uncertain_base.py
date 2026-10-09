from floris import FlorisModel, UncertainFlorisModel
from floris.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR
import numpy as np

# TODO: Compare deterministic and uncertainty-aware optimization.
# Conditions: wind direction 270 degrees, speed 8 m/s, TI=0.06.
# Uncertainty: wind-direction standard deviation wd_std=5 degrees.
