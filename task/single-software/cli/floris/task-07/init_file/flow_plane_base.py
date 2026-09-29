from floris import FlorisModel
import numpy as np

fmodel = FlorisModel("two_turbine.yaml")
fmodel.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
fmodel.run()

# TODO: Sample centerline velocity at hub height along y=0, starting 1D downstream of the second turbine.
# Use sample_flow_at_points(...) and calculate the recovery distance to 0.95 times the inflow speed.
