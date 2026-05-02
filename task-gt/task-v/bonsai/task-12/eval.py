#!/usr/bin/env python3
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

REQUIRED_STOREYS = ["Ground Floor", "Mezzanine"]
REQUIRED_SPACES = ["Ground Seating", "Counter", "Upper Seating"]


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def norm_text(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).casefold()


def check_outputs(root):
    if not (root / "result.ifc").is_file() or (root / "result.ifc").stat().st_size < 100:
        return False
    return True


def check_ifc(root):
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if model.schema.upper() != "IFC4":
        return False
    if len(model.by_type("IfcProject")) != 1 or len(model.by_type("IfcSite")) != 1:
        return False
    if len(model.by_type("IfcBuilding")) != 1:
        return False
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != len(REQUIRED_STOREYS):
        return False
    storey_names = [norm_text(getattr(storey, "Name", "")) for storey in storeys]
    if sorted(storey_names) != sorted(norm_text(name) for name in REQUIRED_STOREYS):
        return False
    spaces = model.by_type("IfcSpace")
    if len(spaces) != len(REQUIRED_SPACES):
        return False
    space_names = [norm_text(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in spaces]
    if sorted(space_names) != sorted(norm_text(name) for name in REQUIRED_SPACES):
        return False
    if len(model.by_type("IfcSlab")) < 2:
        return False
    if len(model.by_type("IfcWall")) < 4:
        return False
    if len(model.by_type("IfcDoor")) < 1:
        return False
    if len(model.by_type("IfcRelVoidsElement")) < 2 or len(model.by_type("IfcRelFillsElement")) < 1:
        return False
    if model.by_type("IfcBuildingElementProxy") or model.by_type("IfcFurniture"):
        return False
    return True


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and check_outputs(root) and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
