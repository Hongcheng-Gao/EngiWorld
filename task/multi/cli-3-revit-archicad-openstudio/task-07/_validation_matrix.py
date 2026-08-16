from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "ground_truth" if (ROOT / "ground_truth").is_dir() else ROOT
EVALUATOR = ROOT / "eval.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update_osm_reports(case: Path) -> None:
    digest = sha(case / "result.osm")
    flow = json.loads((case / "flow_report.json").read_text())
    flow["osm_sha256"] = digest
    (case / "flow_report.json").write_text(json.dumps(flow, indent=2) + "\n")
    log = json.loads((case / "native_stage_log.json").read_text())
    log["stages"][2]["output_sha256"] = digest
    (case / "native_stage_log.json").write_text(json.dumps(log, indent=2) + "\n")


def mutate_zone(case: Path) -> None:
    path = case / "result.osm"
    text = path.read_text()
    lobby = re.search(r"(?ms)^OS:ThermalZone,\s*\n\s*(\{[^}]+\}),\s*!- Handle\s*\n\s*LOBBY-ZN,", text).group(1)
    reading = re.search(r"(?ms)^OS:ThermalZone,\s*\n\s*(\{[^}]+\}),\s*!- Handle\s*\n\s*READING-ROOM-ZN,", text).group(1)
    block = re.search(r"(?ms)^OS:Space,.*?^\s*LOBBY,\s*!- Name.*?;\s*!- Design Specification Outdoor Air Object Name", text)
    path.write_text(text[:block.start()] + block.group(0).replace(lobby, reading, 1) + text[block.end():])
    update_osm_reports(case)


def replace_once(case: Path, old: str, new: str) -> None:
    path = case / "result.osm"
    text = path.read_text()
    assert text.count(old) >= 1, old
    path.write_text(text.replace(old, new, 1))
    update_osm_reports(case)


def fake_archicad(case: Path) -> None:
    shutil.copy2(case / "stage1.ifc", case / "stage2.ifc")
    stage2_hash = sha(case / "stage2.ifc")
    report = json.loads((case / "archicad_validation_report.json").read_text())
    report["output_sha256"] = stage2_hash
    (case / "archicad_validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    handoff = json.loads((case / "archicad_handoff.json").read_text())
    handoff["source_sha256"] = stage2_hash
    (case / "archicad_handoff.json").write_text(json.dumps(handoff, indent=2) + "\n")


def fake_jemi(case: Path) -> None:
    report_path = case / "archicad_validation_report.json"
    report = json.loads(report_path.read_text())
    report["native_provenance"]["rpc_transcript"][17]["response"]["result"]["GlobalId"] = "0FAKE"
    report_path.write_text(json.dumps(report, indent=2) + "\n")


def fake_sql(case: Path) -> None:
    db = sqlite3.connect(str(case / "run/eplusout.sql"))
    db.execute("UPDATE Zones SET FloorArea=999 WHERE ZoneName='LOBBY-ZN'")
    db.commit()
    db.close()
    digest = sha(case / "run/eplusout.sql")
    flow = json.loads((case / "flow_report.json").read_text())
    flow["eplusout_sql_sha256"] = digest
    (case / "flow_report.json").write_text(json.dumps(flow, indent=2) + "\n")


def add_profile_hole(case: Path, guid: str) -> None:
    import ifcopenshell  # type: ignore
    path = case / "stage1.ifc"
    model = ifcopenshell.open(str(path))
    product = model.by_guid(guid)
    body = next(rep for rep in product.Representation.Representations if rep.RepresentationIdentifier == "Body")
    solid = next(item for item in body.Items if item.is_a("IfcExtrudedAreaSolid"))
    profile = solid.SweptArea
    center = profile.Position.Location.Coordinates
    direction = profile.Position.RefDirection.DirectionRatios if profile.Position.RefDirection else (1.0, 0.0)
    x_axis = (float(direction[0]), float(direction[1])); y_axis = (-x_axis[1], x_axis[0])
    half_x, half_y = float(profile.XDim) / 2.0, float(profile.YDim) / 2.0

    def point(local_x: float, local_y: float):
        return model.create_entity("IfcCartesianPoint", Coordinates=(float(center[0]) + local_x * x_axis[0] + local_y * y_axis[0], float(center[1]) + local_x * x_axis[1] + local_y * y_axis[1]))

    def rectangle(scale: float):
        points = [point(-half_x * scale, -half_y * scale), point(half_x * scale, -half_y * scale), point(half_x * scale, half_y * scale), point(-half_x * scale, half_y * scale)]
        return model.create_entity("IfcPolyline", Points=tuple(points + [points[0]]))

    solid.SweptArea = model.create_entity("IfcArbitraryProfileDefWithVoids", ProfileType="AREA", ProfileName=None, OuterCurve=rectangle(1.0), InnerCurves=(rectangle(0.2),))
    model.write(str(path))


def open_roof_shell(case: Path) -> None:
    import ifcopenshell  # type: ignore
    path = case / "stage1.ifc"
    model = ifcopenshell.open(str(path))
    roof = model.by_type("IfcRoof")[0]
    body = roof.Representation.Representations[0]
    face_set = next(item for item in body.Items if item.is_a("IfcPolygonalFaceSet"))
    face_set.Faces = tuple(face_set.Faces[:-1])
    model.write(str(path))


MUTATIONS = {
    "osm_zone_rewire": mutate_zone,
    "osm_load_orphan": lambda c: replace_once(c, "{583a7391-671f-447a-b198-b4a53e2dc073}, !- Space or SpaceType Name", "{00000000-0000-0000-0000-000000000000}, !- Space or SpaceType Name"),
    "osm_wrong_schedule": lambda c: replace_once(c, "{0ec0c9c2-a596-42a2-8fbe-a322642db0ac}, !- Schedule Name", "{62e4f67a-088e-486c-8af3-1179ebe12f99}, !- Schedule Name"),
    "osm_wrong_density": lambda c: replace_once(c, "  9,                                      !- Watts per Space Floor Area {W/m2}", "  19,                                     !- Watts per Space Floor Area {W/m2}"),
    "osm_wrong_oa": lambda c: replace_once(c, "  0.01,                                   !- Outdoor Air Flow per Person {m3/s-person}", "  0.02,                                   !- Outdoor Air Flow per Person {m3/s-person}"),
    "osm_surface_vertex": lambda c: replace_once(c, "  4.1, 0.1, 0;                            !- X,Y,Z Vertex 4 {m}", "  4.2, 0.1, 0;                            !- X,Y,Z Vertex 4 {m}"),
    "archicad_stage1_copy": fake_archicad,
    "archicad_fake_jemi": fake_jemi,
    "sql_wrong_zone_area": fake_sql,
    "roof_topology_open_shell": open_roof_shell,
    "seed_wall_topology_hole": lambda c: add_profile_hole(c, "0aVENBQ497bg_zKWR$4g_C"),
    "seed_slab_topology_hole": lambda c: add_profile_hole(c, "0aVENBQ497bg_zKWR$4g_6"),
}


def run(case: Path) -> tuple[bool, list[str]]:
    subprocess.run(["python", str(EVALUATOR), str(case)], check=False, capture_output=True, text=True)
    data = json.loads((case / "multi_metrics.json").read_text())
    return bool(data["ok"]), data["errors"]


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory(prefix="ew3b07-matrix-") as temp:
        positive = Path(temp) / "positive"
        shutil.copytree(SOURCE, positive)
        ok, errors = run(positive)
        rows.append({"case": "native_positive", "expected": True, "actual": ok, "errors": errors})
        for name, mutation in MUTATIONS.items():
            case = Path(temp) / name
            shutil.copytree(SOURCE, case)
            mutation(case)
            ok, errors = run(case)
            rows.append({"case": name, "expected": False, "actual": ok, "errors": errors[:5]})
    print(json.dumps({"passed": all(row["expected"] == row["actual"] for row in rows), "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
