# -*- coding: utf-8 -*-
from __future__ import print_function

import os

from abaqus import mdb, openMdb
from abaqusConstants import SET
from caeModules import *


desktop = r"C:\Users\user\Desktop"
openMdb(pathName=os.path.join(desktop, "Task08_BlockPlate_GT.cae"))
model = mdb.models["BlockPlate3D"]
model.boundaryConditions["BlockGuideY"].setValues(u1=SET)
mdb.save()
print("saved extra-guide-constraint near miss")
