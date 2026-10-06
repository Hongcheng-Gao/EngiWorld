from floris import FlorisModel
import numpy as np

fmodel = FlorisModel("two_turbine.yaml")

# Error 1: wind_directions must be a numpy array or list, but a scalar is passed here.
fmodel.set(wind_directions=270, wind_speeds=8, turbulence_intensities=0.06)

# Error 2: Power is extracted before run() is called.
powers = fmodel.get_turbine_powers()

# Error 3: The output directory has not been created.
np.savetxt("outputs/result.txt", powers)
