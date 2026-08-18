# -*- coding: utf-8 -*-
from __future__ import print_function

import os

from abaqus import mdb, openMdb
from caeModules import *


DESKTOP = r"C:\Users\user\Desktop"
SOURCE = os.path.join(DESKTOP, "Task18_PunchPlate_GT.cae")


def main():
    openMdb(pathName=SOURCE)
    model = mdb.models["PunchPlate2D"]
    model.boundaryConditions["PunchMotion"].setValuesInStep(
        stepName="IndentationStep",
        u2=-0.05,
    )
    mdb.save()


if __name__ == "__main__":
    main()
