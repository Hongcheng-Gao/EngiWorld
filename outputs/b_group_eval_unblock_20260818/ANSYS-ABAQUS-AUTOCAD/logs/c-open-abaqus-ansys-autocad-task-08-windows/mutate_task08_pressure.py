# -*- coding: utf-8 -*-
from __future__ import print_function

import os

from abaqus import mdb, openMdb
from caeModules import *


desktop = r"C:\Users\user\Desktop"
openMdb(pathName=os.path.join(desktop, "Task08_BlockPlate_GT.cae"))
model = mdb.models["BlockPlate3D"]
model.loads["BlockTopPressure"].setValuesInStep(stepName="ContactStep", magnitude=1.0)
mdb.save()
print("saved wrong-load near miss")
