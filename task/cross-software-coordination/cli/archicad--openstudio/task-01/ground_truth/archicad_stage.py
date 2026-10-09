from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.guid


CASE_ID = "multi-cli-2-archicad-openstudio-task-01-windows"
REVISION = "EW2A01"
EXE = Path(r"C:\Program Files\GRAPHISOFT\Archicad 27\IFCCommandServerApp.exe")
DB = Path(r"C:\EW01-GT-20260820")
MODEL_NAME = "EW01-GT"
PORT = 19741
TOKENS = (
    REVISION,
    "SITE-OFFICE",
    "PRINT-COPY",
    "SOUTH-ENTRANCE-WINDOW",
    "OPAQUE-NORTH-WEST",
    CASE_ID,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_reset_database() -> None:
    resolved = DB.resolve()
    if str(resolved).upper() != r"C:\EW01-GT-20260820":
        raise RuntimeError(f"Refusing to reset unexpected database path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def wait_for_health(process: subprocess.Popen[bytes]) -> None:
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f"IFCCommandServerApp exited with {process.returncode}")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/HEALTH", timeout=1).read()
            return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("IFCCommandServerApp did not become healthy")


class Jemi:
    def __init__(self) -> None:
        self.url = f"http://127.0.0.1:{PORT}/JEMI"
        self.transactions: list[dict[str, object]] = []

    def rpc(self, method: str, params: dict[str, object]) -> object:
        request_data = {"method": method, "params": params}
        started = utc_now()
        request_json = json.dumps(request_data, separators=(",", ":"))
        request = urllib.request.Request(
            self.url,
            data=request_json.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            response_data = json.loads(response.read().decode("utf-8"))
        completed = utc_now()
        self.transactions.append(
            {
                "request": request_data,
                "request_json": request_json,
                "status": status,
                "response": response_data,
                "started_at_utc": started,
                "completed_at_utc": completed,
            }
        )
        if response_data.get("error"):
            raise RuntimeError(f"{method} failed: {response_data['error']}")
        return response_data.get("result")

    def create(self, ifc_class: str, data: dict[str, object]) -> str:
        result = self.rpc("Entity.Create", {"EntityData": {ifc_class: data}})
        if not result:
            raise RuntimeError(f"Entity.Create returned no reference for {ifc_class}")
        return str(result)

    def modify(self, ifc_class: str, select: dict[str, object], data: dict[str, object]) -> str:
        result = self.rpc(
            "Entity.Modify",
            {"select": {ifc_class: select}, "EntityData": {ifc_class: data}},
        )
        if not result:
            raise RuntimeError(f"Entity.Modify returned no reference for {ifc_class}")
        return str(result)

    def refs(self, ifc_class: str) -> list[str]:
        result = self.rpc("Entity.Get", {"Select": {ifc_class: {}}})
        if result is None:
            return []
        return [str(value) for value in (result if isinstance(result, list) else [result])]

    def attr(self, reference: str, attribute: str) -> object:
        result = self.rpc("Entity.GetAttribute", {"Select": reference, "Attribute": attribute})
        return result.get(attribute) if isinstance(result, dict) else None


def new_guid() -> str:
    return ifcopenshell.guid.new()


def create_axis_placement(jemi: Jemi, xyz: tuple[float, float, float]) -> str:
    point = jemi.create("IfcCartesianPoint", {"Coordinates": list(xyz)})
    axis = jemi.create("IfcDirection", {"DirectionRatios": [0.0, 0.0, 1.0]})
    ref_direction = jemi.create("IfcDirection", {"DirectionRatios": [1.0, 0.0, 0.0]})
    return jemi.create(
        "IfcAxis2Placement3D",
        {"Location": point, "Axis": axis, "RefDirection": ref_direction},
    )


def create_local_placement(
    jemi: Jemi,
    parent_selector: dict[str, object],
    xyz: tuple[float, float, float],
) -> dict[str, object]:
    create_axis_placement(jemi, xyz)
    relative_selector = {
        "IfcAxis2Placement3D": {
            "Location": {"IfcCartesianPoint": {"Coordinates": list(xyz)}}
        }
    }
    jemi.create(
        "IfcLocalPlacement",
        {"PlacementRelTo": None, "RelativePlacement": relative_selector},
    )
    return {
        "IfcLocalPlacement": {
            "PlacementRelTo": None,
            "RelativePlacement": relative_selector,
        }
    }


def create_box_shape(
    jemi: Jemi,
    context: str,
    width: float,
    depth: float,
    height: float,
    shape_name: str,
) -> dict[str, object]:
    points = [
        jemi.create("IfcCartesianPoint", {"Coordinates": [x, y]})
        for x, y in ((0.0, 0.0), (width, 0.0), (width, depth), (0.0, depth), (0.0, 0.0))
    ]
    polyline = jemi.create("IfcPolyline", {"Points": points})
    profile = jemi.create(
        "IfcArbitraryClosedProfileDef",
        {"ProfileType": "AREA", "ProfileName": None, "OuterCurve": polyline},
    )
    solid_position = create_axis_placement(jemi, (0.0, 0.0, 0.0))
    extrusion_direction = jemi.create("IfcDirection", {"DirectionRatios": [0.0, 0.0, 1.0]})
    solid = jemi.create(
        "IfcExtrudedAreaSolid",
        {
            "SweptArea": profile,
            "Position": solid_position,
            "ExtrudedDirection": extrusion_direction,
            "Depth": height,
        },
    )
    representation = jemi.create(
        "IfcShapeRepresentation",
        {
            "ContextOfItems": context,
            "RepresentationIdentifier": "Body",
            "RepresentationType": "SweptSolid",
            "Items": [solid],
        },
    )
    jemi.create(
        "IfcProductDefinitionShape",
        {"Name": shape_name, "Description": None, "Representations": [representation]},
    )
    point_selectors = [
        {"IfcCartesianPoint": {"Coordinates": [x, y]}}
        for x, y in ((0.0, 0.0), (width, 0.0), (width, depth), (0.0, depth), (0.0, 0.0))
    ]
    direction_selector = {"IfcDirection": {"DirectionRatios": [0.0, 0.0, 1.0]}}
    world_axis_selector = {
        "IfcAxis2Placement3D": {
            "Location": {"IfcCartesianPoint": {"Coordinates": [0.0, 0.0, 0.0]}},
            "Axis": direction_selector,
            "RefDirection": {"IfcDirection": {"DirectionRatios": [1.0, 0.0, 0.0]}},
        }
    }
    model_context_selector = {
        "IfcGeometricRepresentationContext": {
            "ContextIdentifier": "Model",
            "ContextType": "Model",
            "CoordinateSpaceDimension": 3,
            "Precision": 1e-5,
            "WorldCoordinateSystem": world_axis_selector,
            "TrueNorth": None,
        }
    }
    body_context_selector = {
        "IfcGeometricRepresentationSubContext": {
            "ContextIdentifier": "Body",
            "ContextType": "Model",
            "ParentContext": model_context_selector,
            "TargetScale": None,
            "TargetView": "MODEL_VIEW",
            "UserDefinedTargetView": None,
        }
    }
    solid_selector = {
        "IfcExtrudedAreaSolid": {
            "SweptArea": {
                "IfcArbitraryClosedProfileDef": {
                    "ProfileType": "AREA",
                    "OuterCurve": {"IfcPolyline": {"Points": point_selectors}},
                }
            },
            "Position": {
                "IfcAxis2Placement3D": {
                    "Location": {"IfcCartesianPoint": {"Coordinates": [0.0, 0.0, 0.0]}}
                }
            },
            "ExtrudedDirection": direction_selector,
            "Depth": height,
        }
    }
    return {
        "IfcProductDefinitionShape": {
            "Name": shape_name,
            "Representations": [
                {
                    "IfcShapeRepresentation": {
                        "ContextOfItems": body_context_selector,
                        "RepresentationIdentifier": "Body",
                        "RepresentationType": "SweptSolid",
                        "Items": [solid_selector],
                    }
                }
            ],
        }
    }


def find_decomposition(jemi: Jemi, storey_ref: str) -> tuple[str, str, list[str]]:
    for relation_ref in jemi.refs("IfcRelAggregates"):
        if str(jemi.attr(relation_ref, "RelatingObject")) == storey_ref:
            gid = str(jemi.attr(relation_ref, "GlobalId"))
            related = [str(value) for value in (jemi.attr(relation_ref, "RelatedObjects") or [])]
            return relation_ref, gid, related
    raise RuntimeError("Storey IfcRelAggregates was not found")


def entity_bbox(ifc_file: ifcopenshell.file, entity: object) -> list[float]:
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    shape = ifcopenshell.geom.create_shape(settings, entity)
    vertices = list(shape.geometry.verts)
    xyz = list(zip(vertices[0::3], vertices[1::3], vertices[2::3]))
    return [
        min(point[0] for point in xyz),
        min(point[1] for point in xyz),
        min(point[2] for point in xyz),
        max(point[0] for point in xyz),
        max(point[1] for point in xyz),
        max(point[2] for point in xyz),
    ]


def build_handoff(root: Path, transactions: list[dict[str, object]]) -> dict[str, object]:
    stage1 = root / "stage1.ifc"
    ifc_file = ifcopenshell.open(str(stage1))
    spaces = {str(space.Name): space for space in ifc_file.by_type("IfcSpace")}
    required_names = {"SITE-OFFICE", "PRINT-COPY"}
    if set(spaces) != required_names:
        raise RuntimeError(f"Unexpected space inventory: {sorted(spaces)}")

    bboxes = {name: entity_bbox(ifc_file, spaces[name]) for name in sorted(spaces)}
    areas = {name: (box[3] - box[0]) * (box[4] - box[1]) for name, box in bboxes.items()}
    first, second = (bboxes[name] for name in sorted(bboxes))
    overlap_x = max(0.0, min(first[3], second[3]) - max(first[0], second[0]))
    overlap_y = max(0.0, min(first[4], second[4]) - max(first[1], second[1]))
    if overlap_x * overlap_y > 1e-8:
        raise RuntimeError("Generated spaces overlap")

    counts = {
        name: len(ifc_file.by_type(name))
        for name in (
            "IfcProject",
            "IfcSite",
            "IfcBuilding",
            "IfcBuildingStorey",
            "IfcSpace",
            "IfcWall",
            "IfcSlab",
            "IfcRoof",
            "IfcDoor",
            "IfcWindow",
            "IfcOpeningElement",
            "IfcRelVoidsElement",
            "IfcRelFillsElement",
        )
    }
    if counts["IfcOpeningElement"] != 2 or counts["IfcRelVoidsElement"] != 2 or counts["IfcRelFillsElement"] != 2:
        raise RuntimeError(f"Incomplete opening topology: {counts}")

    stage_hash = sha256_file(stage1)
    records = [
        {
            "name": "SITE-OFFICE",
            "ifc_global_id": spaces["SITE-OFFICE"].GlobalId,
            "thermal_zone": "SITE-OFFICE-ZN",
            "floor_area_m2": round(areas["SITE-OFFICE"], 6),
            "door_count": 1,
            "window_count": 1,
            "bbox_m": [round(value, 6) for value in bboxes["SITE-OFFICE"]],
        },
        {
            "name": "PRINT-COPY",
            "ifc_global_id": spaces["PRINT-COPY"].GlobalId,
            "thermal_zone": "PRINT-COPY-ZN",
            "floor_area_m2": round(areas["PRINT-COPY"], 6),
            "door_count": 0,
            "window_count": 0,
            "bbox_m": [round(value, 6) for value in bboxes["PRINT-COPY"]],
        },
    ]
    return {
        "schema": "engiworld.archicad-openstudio-handoff.v2",
        "case_id": CASE_ID,
        "software_stage": "archicad",
        "authoring_software": "Graphisoft Archicad 27.0.0 R1 (6000) IFCCommandServerApp",
        "native_cli_executable": str(EXE),
        "source_file": "stage1.ifc",
        "source_init_sha256": sha256_file(root / "init.ifc"),
        "source_sha256": stage_hash,
        "source_stage1_sha256": stage_hash,
        "revision_code": REVISION,
        "required_stage_tokens": list(TOKENS),
        "handoff_tokens": [
            "LOW-EQUIPMENT-OFFICE",
            "SIDE-DAYLIGHT",
            "QUIET-OPAQUE-ENVELOPE",
            "SOUTH-ENTRANCE-WINDOW",
        ],
        "spaces": records,
        "thermal_zones": ["SITE-OFFICE-ZN", "PRINT-COPY-ZN"],
        "building_area_m2": round(sum(areas.values()), 6),
        "space_overlap_area_m2": round(overlap_x * overlap_y, 9),
        "bim_counts": counts,
        "door_count": counts["IfcDoor"],
        "window_count": counts["IfcWindow"],
        "opening_count": counts["IfcOpeningElement"],
        "void_relationship_count": counts["IfcRelVoidsElement"],
        "fill_relationship_count": counts["IfcRelFillsElement"],
        "native_transaction_summary": {
            "count": len(transactions),
            "methods": [str(item["request"]["method"]) for item in transactions],
            "first_request": transactions[0]["request"],
            "last_request": transactions[-1]["request"],
        },
        "generated_at_utc": utc_now(),
    }


def run(root: Path) -> None:
    root = root.resolve()
    init_path = root / "init.ifc"
    stage1_path = root / "stage1.ifc"
    if not init_path.is_file() or sha256_file(init_path) != "7badf9b2966d2d409935899c09a80d6291afaac1cb93e920a63dbca7d93b5304":
        raise RuntimeError("The expected task-01 seed IFC is missing or changed")
    if not EXE.is_file():
        raise RuntimeError(f"Missing IFC command server: {EXE}")

    safe_reset_database()
    started = utc_now()
    command = [str(EXE), "--p", str(PORT), "--m", MODEL_NAME, "--d", str(DB), "--sa", "new_ifc4"]
    process = subprocess.Popen(command, cwd=str(EXE.parent), creationflags=subprocess.CREATE_NO_WINDOW)
    jemi = Jemi()
    try:
        wait_for_health(process)
        loaded = jemi.rpc("Model.LoadFile", {"location": init_path.as_posix()})
        if loaded != "init.ifc":
            raise RuntimeError(f"Unexpected Model.LoadFile result: {loaded}")

        context = jemi.refs("IfcGeometricRepresentationSubContext")[0]
        storey = jemi.refs("IfcBuildingStorey")[0]
        original_space = jemi.refs("IfcSpace")[0]
        south_wall = next(
            reference for reference in jemi.refs("IfcWall") if jemi.attr(reference, "Name") == "South Wall"
        )
        storey_placement_selector = {
            "IfcLocalPlacement": {
                "PlacesObject": [
                    {"IfcBuildingStorey": {"GlobalId": "0UXgtbtxnFJOte7WINbb5E"}}
                ]
            }
        }
        south_wall_placement_selector = {
            "IfcLocalPlacement": {
                "PlacesObject": [
                    {"IfcWall": {"GlobalId": "32d8mMREbFNPzh7nfUuBrd"}}
                ]
            }
        }

        site_shape = create_box_shape(jemi, context, 3.4, 3.6, 2.8, "SITE-OFFICE-SHAPE")
        print_shape = create_box_shape(jemi, context, 2.2, 3.6, 2.8, "PRINT-COPY-SHAPE")
        print_placement = create_local_placement(jemi, storey_placement_selector, (3.6, 0.2, 0.0))
        description = " | ".join(TOKENS)

        jemi.modify(
            "IfcSpace",
            {"GlobalId": "3znJ4SF8rBlwVkCHVqICV9", "Name": "UNCLASSIFIED"},
            {
                "Name": "SITE-OFFICE",
                "Description": description,
                "Representation": site_shape,
                "LongName": "SITE-OFFICE-ZN",
            },
        )
        print_guid = new_guid()
        print_space = jemi.create(
            "IfcSpace",
            {
                "GlobalId": print_guid,
                "Name": "PRINT-COPY",
                "Description": description,
                "ObjectType": None,
                "LongName": "PRINT-COPY-ZN",
                "CompositionType": "ELEMENT",
                "PredefinedType": "INTERNAL",
                "ElevationWithFlooring": 0.0,
            },
        )
        jemi.modify(
            "IfcSpace",
            {"GlobalId": print_guid},
            {"ObjectPlacement": print_placement, "Representation": print_shape},
        )

        jemi.modify("IfcQuantityArea", {"Name": "NetFloorArea"}, {"AreaValue": 12.24})
        _, aggregation_guid, related_spaces = find_decomposition(jemi, storey)
        if original_space not in related_spaces:
            raise RuntimeError("Seed space is not owned by the building storey")
        jemi.modify(
            "IfcRelAggregates",
            {"GlobalId": aggregation_guid},
            {"RelatedObjects": related_spaces + [print_space]},
        )

        door_opening_placement = create_local_placement(
            jemi, south_wall_placement_selector, (0.675, -0.01, 0.0)
        )
        door_opening_shape = create_box_shape(
            jemi, context, 0.95, 0.22, 2.15, "SOUTH-ENTRANCE-DOOR-OPENING-SHAPE"
        )
        door_opening = jemi.create(
            "IfcOpeningElement",
            {
                "GlobalId": new_guid(),
                "Name": "SOUTH-ENTRANCE-DOOR-OPENING",
                "Description": f"{REVISION} | hosted by South Wall",
                "PredefinedType": "OPENING",
            },
        )
        jemi.modify(
            "IfcOpeningElement",
            {"GlobalId": str(jemi.attr(door_opening, "GlobalId"))},
            {"ObjectPlacement": door_opening_placement, "Representation": door_opening_shape},
        )
        door_placement = create_local_placement(jemi, south_wall_placement_selector, (0.7, 0.0, 0.0))
        door_shape = create_box_shape(jemi, context, 0.9, 0.2, 2.1, "SOUTH-ENTRANCE-DOOR-SHAPE")
        door_guid = new_guid()
        door = jemi.create(
            "IfcDoor",
            {
                "GlobalId": door_guid,
                "Name": "SOUTH-ENTRANCE-DOOR",
                "Description": f"{REVISION} | SITE-OFFICE entrance",
                "OverallHeight": 2.1,
                "OverallWidth": 0.9,
                "PredefinedType": "DOOR",
                "OperationType": "SINGLE_SWING_LEFT",
                "UserDefinedOperationType": None,
            },
        )
        jemi.modify(
            "IfcDoor",
            {"GlobalId": door_guid},
            {"ObjectPlacement": door_placement, "Representation": door_shape},
        )
        jemi.create(
            "IfcRelVoidsElement",
            {
                "GlobalId": new_guid(),
                "Name": "South wall door opening",
                "Description": REVISION,
                "RelatingBuildingElement": south_wall,
                "RelatedOpeningElement": door_opening,
            },
        )
        jemi.create(
            "IfcRelFillsElement",
            {
                "GlobalId": new_guid(),
                "Name": "South entrance door fill",
                "Description": REVISION,
                "RelatingOpeningElement": door_opening,
                "RelatedBuildingElement": door,
            },
        )

        window_opening_placement = create_local_placement(
            jemi, south_wall_placement_selector, (1.975, -0.01, 0.975)
        )
        window_opening_shape = create_box_shape(
            jemi, context, 1.55, 0.22, 1.25, "SOUTH-ENTRANCE-WINDOW-OPENING-SHAPE"
        )
        window_opening = jemi.create(
            "IfcOpeningElement",
            {
                "GlobalId": new_guid(),
                "Name": "SOUTH-ENTRANCE-WINDOW-OPENING",
                "Description": f"{REVISION} | hosted by South Wall",
                "PredefinedType": "OPENING",
            },
        )
        jemi.modify(
            "IfcOpeningElement",
            {"GlobalId": str(jemi.attr(window_opening, "GlobalId"))},
            {"ObjectPlacement": window_opening_placement, "Representation": window_opening_shape},
        )
        window_placement = create_local_placement(jemi, south_wall_placement_selector, (2.0, 0.0, 1.0))
        window_shape = create_box_shape(
            jemi, context, 1.5, 0.2, 1.2, "SOUTH-ENTRANCE-WINDOW-SHAPE"
        )
        window_guid = new_guid()
        window = jemi.create(
            "IfcWindow",
            {
                "GlobalId": window_guid,
                "Name": "SOUTH-ENTRANCE-WINDOW",
                "Description": f"{REVISION} | SIDE-DAYLIGHT",
                "OverallHeight": 1.2,
                "OverallWidth": 1.5,
                "PredefinedType": "WINDOW",
                "PartitioningType": "SINGLE_PANEL",
                "UserDefinedPartitioningType": None,
            },
        )
        jemi.modify(
            "IfcWindow",
            {"GlobalId": window_guid},
            {"ObjectPlacement": window_placement, "Representation": window_shape},
        )
        jemi.create(
            "IfcRelVoidsElement",
            {
                "GlobalId": new_guid(),
                "Name": "South wall window opening",
                "Description": REVISION,
                "RelatingBuildingElement": south_wall,
                "RelatedOpeningElement": window_opening,
            },
        )
        jemi.create(
            "IfcRelFillsElement",
            {
                "GlobalId": new_guid(),
                "Name": "South entrance window fill",
                "Description": REVISION,
                "RelatingOpeningElement": window_opening,
                "RelatedBuildingElement": window,
            },
        )

        containment = jemi.refs("IfcRelContainedInSpatialStructure")[0]
        containment_guid = str(jemi.attr(containment, "GlobalId"))
        contained = [str(value) for value in (jemi.attr(containment, "RelatedElements") or [])]
        jemi.modify(
            "IfcRelContainedInSpatialStructure",
            {"GlobalId": containment_guid},
            {"RelatedElements": contained + [door, window]},
        )

        jemi.modify(
            "IfcProject",
            {"GlobalId": "3mJ18IVyDD8QigQzh7dRgH"},
            {"Description": description},
        )
        jemi.modify(
            "IfcBuilding",
            {"GlobalId": "0JfFPYCLP5x8_ZoNs7CSSW"},
            {"Description": description},
        )
        jemi.modify(
            "IfcBuildingStorey",
            {"GlobalId": "0UXgtbtxnFJOte7WINbb5E"},
            {"Description": description},
        )
        for guid, name in (
            ("0T_ior$Sz7SvsowI8HyBRU", "North Wall"),
            ("37R08A_U13nB64yNdbGdbf", "West Wall"),
        ):
            jemi.modify(
                "IfcWall",
                {"GlobalId": guid, "Name": name},
                {"Description": f"{REVISION} | OPAQUE-NORTH-WEST | QUIET-OPAQUE-ENVELOPE"},
            )

        for shape_name in (
            "SITE-OFFICE-SHAPE",
            "PRINT-COPY-SHAPE",
            "SOUTH-ENTRANCE-DOOR-OPENING-SHAPE",
            "SOUTH-ENTRANCE-DOOR-SHAPE",
            "SOUTH-ENTRANCE-WINDOW-OPENING-SHAPE",
            "SOUTH-ENTRANCE-WINDOW-SHAPE",
        ):
            orphan_selector = {
                "IfcProductDefinitionShape": {
                    "Name": shape_name,
                    "ShapeOfProduct": [],
                }
            }
            orphan_refs = jemi.rpc("Entity.Get", {"Select": orphan_selector})
            if orphan_refs:
                jemi.rpc("Entity.Delete", {"Select": orphan_selector})

        validation = jemi.rpc("Macro.ValidateIfcModel", {})
        missing = validation.get("MissingMandatoryAttributes", []) if isinstance(validation, dict) else []
        unexpected = [
            item
            for item in missing
            if not (
                item.get("Type") == "IfcOwnerHistory"
                and set(item.get("Attrbiutes", [])) == {"CreationDate"}
            )
        ]
        if unexpected:
            raise RuntimeError(f"Archicad IFC validation failed: {unexpected}")
        jemi.rpc("Model.SaveFile", {"location": stage1_path.as_posix()})
        if not stage1_path.is_file() or stage1_path.stat().st_size < 10000:
            raise RuntimeError("Archicad did not save a nontrivial stage1.ifc")

        handoff = build_handoff(root, jemi.transactions)
        handoff_path = root / "handoff.json"
        handoff_path.write_text(json.dumps(handoff, indent=2), encoding="utf-8")
        native_log = {
            "schema": "engiworld.archicad-native-stage.v2",
            "case_id": CASE_ID,
            "software_stage": "archicad",
            "native_stage_started_at_utc": started,
            "native_stage_completed_at_utc": utc_now(),
            "command_server_process": {
                "pid": process.pid,
                "executable_path": str(EXE),
                "command_line": subprocess.list2cmdline(command),
                "product_version": "27.0.0 R1 (6000)",
                "executable_sha256": sha256_file(EXE),
                "listening_port": PORT,
                "model_name": MODEL_NAME,
                "database_path": str(DB),
            },
            "artifacts": {
                "init.ifc": {"sha256": sha256_file(init_path), "size": init_path.stat().st_size},
                "stage1.ifc": {"sha256": sha256_file(stage1_path), "size": stage1_path.stat().st_size},
                "handoff.json": {"sha256": sha256_file(handoff_path), "size": handoff_path.stat().st_size},
            },
            "native_transactions": {"Items": jemi.transactions},
        }
        (root / "native_stage_log.json").write_text(json.dumps(native_log, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "stage1_sha256": sha256_file(stage1_path), "counts": handoff["bim_counts"]}))
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    run(Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\user\Desktop"))
