# -*- coding: utf-8 -*-
from __future__ import print_function

import os

from abaqus import mdb, openMdb
from abaqusConstants import OFF
from caeModules import *


desktop = r"C:\Users\user\Desktop"
openMdb(pathName=os.path.join(desktop, "Task18_PunchPlate_GT.cae"))
model = mdb.models["PunchPlate2D"]
model.interactionProperties["FrictionlessHard"].normalBehavior.setValues(
    allowSeparation=OFF,
)
mdb.save()
print("saved no-separation near miss")
