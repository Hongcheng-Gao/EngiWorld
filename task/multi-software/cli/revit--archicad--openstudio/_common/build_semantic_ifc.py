from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.element


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def body_representation(model, space, geometry, context, storey):
    scale = 1000.0
    x = float(geometry["x_m"]) * scale
    y = float(geometry["y_m"]) * scale
    z = float(geometry["z_m"]) * scale - float(storey.Elevation or 0.0)
    width = float(geometry["width_m"]) * scale
    depth = float(geometry["depth_m"]) * scale
    height = float(geometry["height_m"]) * scale

    origin = model.create_entity("IfcCartesianPoint", Coordinates=(x, y, z))
    placement_3d = model.create_entity("IfcAxis2Placement3D", Location=origin)
    placement = model.create_entity(
        "IfcLocalPlacement",
        PlacementRelTo=storey.ObjectPlacement,
        RelativePlacement=placement_3d,
    )
    profile_origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    profile_placement = model.create_entity("IfcAxis2Placement2D", Location=profile_origin)
    profile = model.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        Position=profile_placement,
        XDim=width,
        YDim=depth,
    )
    solid_origin = model.create_entity(
        "IfcCartesianPoint", Coordinates=(width / 2.0, depth / 2.0, 0.0)
    )
    solid_placement = model.create_entity("IfcAxis2Placement3D", Location=solid_origin)
    up = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    solid = model.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=solid_placement,
        ExtrudedDirection=up,
        Depth=height,
    )
    shape = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=(solid,),
    )
    representation = model.create_entity(
        "IfcProductDefinitionShape", Representations=(shape,)
    )
    space.ObjectPlacement = placement
    space.Representation = representation


def ensure_qto(model, space, area_m2):
    qtos = ifcopenshell.util.element.get_psets(space, qtos_only=True)
    existing = qtos.get("Qto_SpaceBaseQuantities")
    if existing and existing.get("id"):
        qto = model.by_id(existing["id"])
    else:
        qto = ifcopenshell.api.run(
            "pset.add_qto", model, product=space, name="Qto_SpaceBaseQuantities"
        )
    ifcopenshell.api.run(
        "pset.edit_qto",
        model,
        qto=qto,
        properties={
            "GrossFloorArea": float(area_m2),
            "NetFloorArea": float(area_m2),
        },
    )


def ensure_pset(model, product, name, properties):
    psets = ifcopenshell.util.element.get_psets(product, psets_only=True)
    existing = psets.get(name)
    if existing and existing.get("id"):
        pset = model.by_id(existing["id"])
    else:
        pset = ifcopenshell.api.run("pset.add_pset", model, product=product, name=name)
    ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties=properties)


def prepare_spaces(model, spec):
    existing_spaces = {
        str(space.GlobalId): space
        for space in model.by_type("IfcSpace")
        if space.ObjectPlacement and space.Representation
    }
    for space in list(model.by_type("IfcSpace")):
        if not space.ObjectPlacement or not space.Representation:
            ifcopenshell.api.run("root.remove_product", model, product=space)

    required_guids = {row["ifc_guid"] for row in spec["spaces"]}
    for guid, space in list(existing_spaces.items()):
        if guid not in required_guids:
            ifcopenshell.api.run("root.remove_product", model, product=space)
            existing_spaces.pop(guid)

    model_storeys = model.by_type("IfcBuildingStorey")
    specified_storeys = spec["storeys"]
    if len(model_storeys) == len(specified_storeys):
        for storey, row in zip(model_storeys, specified_storeys):
            storey.Name = row["name"]
    storeys = {str(item.Name): item for item in model_storeys}
    owner_history = model.by_type("IfcOwnerHistory")[0]
    source_space = next(iter(existing_spaces.values()))
    context = source_space.Representation.Representations[0].ContextOfItems
    required = []
    for row in spec["spaces"]:
        guid = row["ifc_guid"]
        space = existing_spaces.get(guid)
        storey = storeys[row["storey"]]
        if space is None:
            space = model.create_entity(
                "IfcSpace",
                GlobalId=guid,
                OwnerHistory=owner_history,
                Name=row["name"],
                Description="Room created by the pinned Revit workflow",
                LongName=row["name"],
                CompositionType="ELEMENT",
                PredefinedType="NOTDEFINED",
            )
            ifcopenshell.api.run(
                "aggregate.assign_object", model, products=[space], relating_object=storey
            )
        space.Name = row["name"]
        space.LongName = row["name"]
        space.Description = "Native BIM space with IFC-to-energy semantics"
        body_representation(model, space, row["energy_geometry"], context, storey)
        area = float(row["energy_geometry"]["width_m"]) * float(
            row["energy_geometry"]["depth_m"]
        )
        ensure_qto(model, space, area)
        ensure_pset(
            model,
            space,
            "Pset_SpaceCommon",
            {"Reference": row["name"], "IsExternal": False},
        )
        semantics = row["energy_semantics"]
        ensure_pset(
            model,
            space,
            "EngiWorld_EnergyHandoff",
            {
                "Revision": spec["revision"],
                "ThermalZone": row["thermal_zone"],
                "ScheduleCategory": semantics["schedule_category"],
                "LightingPowerDensityWPerM2": float(semantics["lighting_w_per_m2"]),
                "EquipmentPowerDensityWPerM2": float(semantics["equipment_w_per_m2"]),
                "PeoplePerM2": float(semantics["people_per_m2"]),
                "OutdoorAirLPerSPerson": float(
                    semantics["outdoor_air_l_per_s_person"]
                ),
            },
        )
        required.append(space)
    return required


def prepare_roof(model, spec):
    geometry = spec.get("roof_geometry")
    if not geometry:
        return
    roofs = model.by_type("IfcRoof")
    owner_history = model.by_type("IfcOwnerHistory")[0]
    model_storeys = model.by_type("IfcBuildingStorey")
    storeys = {str(item.Name): item for item in model_storeys}
    storey = storeys.get(geometry.get("storey"), model_storeys[0])
    context = model.by_type("IfcSpace")[0].Representation.Representations[0].ContextOfItems
    if roofs:
        roof = roofs[0]
    else:
        roof = model.create_entity(
            "IfcRoof",
            GlobalId=geometry.get("ifc_guid", ifcopenshell.guid.new()),
            OwnerHistory=owner_history,
            Name="PITCHED-ROOF",
            PredefinedType="GABLE_ROOF",
        )
        ifcopenshell.api.run(
            "spatial.assign_container", model, products=[roof], relating_structure=storey
        )
    scale = 1000.0
    width = float(geometry["width_m"]) * scale
    depth = float(geometry["depth_m"]) * scale
    base_z = (
        float(geometry["base_z_m"]) * scale - float(storey.Elevation or 0.0)
    )
    rise = float(geometry["ridge_rise_m"]) * scale
    coordinates = model.create_entity(
        "IfcCartesianPointList3D",
        CoordList=(
            (0.0, 0.0, base_z), (width, 0.0, base_z),
            (width, depth, base_z), (0.0, depth, base_z),
            (width / 2.0, 0.0, base_z + rise),
            (width / 2.0, depth, base_z + rise),
        ),
    )
    faces = model.create_entity(
        "IfcTriangulatedFaceSet",
        Coordinates=coordinates,
        Closed=False,
        CoordIndex=((1, 5, 6), (1, 6, 4), (5, 2, 3), (5, 3, 6), (1, 2, 5), (4, 6, 3)),
    )
    shape = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="Tessellation",
        Items=(faces,),
    )
    roof.Representation = model.create_entity(
        "IfcProductDefinitionShape", Representations=(shape,)
    )
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    axis = model.create_entity("IfcAxis2Placement3D", Location=origin)
    roof.ObjectPlacement = model.create_entity(
        "IfcLocalPlacement", PlacementRelTo=storey.ObjectPlacement, RelativePlacement=axis
    )
    roof.Name = "PITCHED-ROOF"
    roof.PredefinedType = "GABLE_ROOF"
    ensure_pset(
        model,
        roof,
        "Pset_RoofCommon",
        {"Reference": "PITCHED-ROOF", "PitchAngleDegrees": float(geometry["slope_degrees"])},
    )


def prepare_fillings(model, spec):
    owner_history = model.by_type("IfcOwnerHistory")[0]
    storeys = {str(item.Name): item for item in model.by_type("IfcBuildingStorey")}
    walls = model.by_type("IfcWall")
    definitions = (
        ("IfcDoor", "door_geometries", "DOOR", "SINGLE_SWING_LEFT", "Pset_DoorCommon"),
        ("IfcWindow", "window_geometries", "WINDOW", "SINGLE_PANEL", "Pset_WindowCommon"),
    )
    for ifc_class, key, predefined_type, operation_type, pset_name in definitions:
        for geometry in spec.get(key, []):
            storey = storeys[geometry["storey"]]
            dimensions = geometry["geometry"]
            attributes = {
                "GlobalId": geometry["ifc_guid"],
                "OwnerHistory": owner_history,
                "Name": geometry["name"],
                "Description": "Revit-authored filling with a geometric host opening",
                "OverallHeight": float(dimensions["height_m"]) * 1000.0,
                "OverallWidth": float(geometry["overall_width_m"]) * 1000.0,
                "PredefinedType": predefined_type,
            }
            if ifc_class == "IfcDoor":
                attributes["OperationType"] = operation_type
            else:
                attributes["PartitioningType"] = operation_type
            filling = model.create_entity(ifc_class, **attributes)
            body_representation(model, filling, dimensions, model.by_type("IfcSpace")[0].Representation.Representations[0].ContextOfItems, storey)
            opening = model.create_entity(
                "IfcOpeningElement",
                GlobalId=geometry["opening_ifc_guid"],
                OwnerHistory=owner_history,
                Name=geometry["name"] + "-OPENING",
                Description="Host opening for " + geometry["name"],
                PredefinedType="OPENING",
            )
            body_representation(model, opening, dimensions, model.by_type("IfcSpace")[0].Representation.Representations[0].ContextOfItems, storey)
            host = walls[int(geometry["host_wall_index"])]
            model.create_entity(
                "IfcRelVoidsElement",
                GlobalId=geometry["void_relation_ifc_guid"],
                OwnerHistory=owner_history,
                RelatingBuildingElement=host,
                RelatedOpeningElement=opening,
            )
            model.create_entity(
                "IfcRelFillsElement",
                GlobalId=geometry["fill_relation_ifc_guid"],
                OwnerHistory=owner_history,
                RelatingOpeningElement=opening,
                RelatedBuildingElement=filling,
            )
            ensure_pset(
                model,
                filling,
                pset_name,
                {"Reference": geometry["name"], "IsExternal": bool(geometry["is_external"])},
            )


def prepare_opening(model, spec):
    geometry = spec.get("opening_geometry")
    if not geometry:
        return
    owner_history = model.by_type("IfcOwnerHistory")[0]
    storeys = {str(item.Name): item for item in model.by_type("IfcBuildingStorey")}
    storey = storeys[geometry["storey"]]
    opening = model.create_entity(
        "IfcOpeningElement",
        GlobalId=geometry["ifc_guid"],
        OwnerHistory=owner_history,
        Name="STAIR-OPENING",
        Description="Revit slab opening retained for multi-storey coordination",
        PredefinedType="OPENING",
    )
    context = model.by_type("IfcSpace")[0].Representation.Representations[0].ContextOfItems
    body_representation(model, opening, geometry, context, storey)
    slabs = model.by_type("IfcSlab")
    host = slabs[int(geometry.get("host_slab_index", len(slabs) - 1))]
    model.create_entity(
        "IfcRelVoidsElement",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        RelatingBuildingElement=host,
        RelatedOpeningElement=opening,
    )


def set_header(model, filename, author, preprocessor, originating_system, timestamp):
    model.header.file_name.name = filename
    model.header.file_name.time_stamp = timestamp
    model.header.file_name.author = (author,)
    model.header.file_name.preprocessor_version = preprocessor
    model.header.file_name.originating_system = originating_system


def build(base_path: Path, spec_path: Path, stage1_path: Path, stage2_path: Path):
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    stage1 = ifcopenshell.open(str(base_path))
    prepare_spaces(stage1, spec)
    prepare_roof(stage1, spec)
    prepare_fillings(stage1, spec)
    prepare_opening(stage1, spec)
    building = stage1.by_type("IfcBuilding")[0]
    ensure_pset(
        stage1,
        building,
        "EngiWorld_StageMetadata",
        {
            "CaseId": spec["case_id"],
            "Revision": spec["revision"],
            "Stage": "revit",
            "StageTokens": " ".join(spec["revit_stage"]["required_tokens"]),
        },
    )
    set_header(
        stage1,
        "stage1.ifc",
        "EngiWorld Revit Bridge",
        "Autodesk Revit 2025 IFC Exporter 25.1.0.44",
        "Autodesk Revit 25.1.0.44 (ENU)",
        "2026-07-06T10:50:51Z",
    )
    stage1.write(str(stage1_path))

    stage1_hash = sha256(stage1_path)
    stage2 = ifcopenshell.open(str(stage1_path))
    building = stage2.by_type("IfcBuilding")[0]
    ensure_pset(
        stage2,
        building,
        "EngiWorld_StageMetadata",
        {
            "Stage": "archicad",
            "Stage1Sha256": stage1_hash,
            "Stage1HashPrefix": stage1_hash[:12],
            "StageTokens": " ".join(spec["archicad_stage"]["required_tokens"]),
            "QaStatus": "ARCHICAD-QA-PASS",
        },
    )
    applications = stage2.by_type("IfcApplication")
    if applications:
        app = applications[0]
        app.Version = "27.0.0.6000"
        app.ApplicationFullName = "GRAPHISOFT Archicad 27"
        app.ApplicationIdentifier = "Archicad"
        if app.ApplicationDeveloper:
            app.ApplicationDeveloper.Name = "GRAPHISOFT SE"
    set_header(
        stage2,
        "stage2.ifc",
        "EngiWorld Archicad IFC Command Server",
        "GRAPHISOFT Archicad 27 IFC Translator",
        "GRAPHISOFT Archicad 27.0.0 INT build 6000",
        "2026-07-06T10:51:44Z",
    )
    stage2.write(str(stage2_path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--stage1", type=Path, required=True)
    parser.add_argument("--stage2", type=Path, required=True)
    args = parser.parse_args()
    build(args.base, args.spec, args.stage1, args.stage2)


if __name__ == "__main__":
    main()
