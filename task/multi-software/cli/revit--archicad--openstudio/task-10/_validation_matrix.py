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


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_osm_provenance(case: Path) -> None:
    digest = sha(case / "result.osm")
    flow_path = case / "flow_report.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["osm_sha256"] = digest
    save_json(flow_path, flow)
    log_path = case / "native_stage_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8"))
    log["stages"][2]["output_sha256"] = digest
    save_json(log_path, log)


def update_idf_provenance(case: Path) -> None:
    digest = sha(case / "in.idf")
    flow_path = case / "flow_report.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["idf_sha256"] = digest
    save_json(flow_path, flow)
    log_path = case / "native_stage_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8"))
    log["stages"][2]["idf_sha256"] = digest
    save_json(log_path, log)


def equivalent_osm_reorder(case: Path) -> None:
    path = case / "result.osm"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"(?ms)^\s*OS:[A-Za-z0-9:]+\s*,.*?;\s*!-[^\r\n]*(?:\r?\n)?")
    blocks = list(pattern.finditer(text))
    assert len(blocks) > 20
    left, right = blocks[10], blocks[11]
    swapped = text[:left.start()] + right.group(0) + left.group(0) + text[right.end():]
    path.write_text(swapped, encoding="utf-8")
    update_osm_provenance(case)


def mutate_ifc(case: Path, operation, filename: str = "stage1.ifc") -> None:
    import ifcopenshell  # type: ignore

    path = case / filename
    model = ifcopenshell.open(str(path))
    operation(model)
    model.write(str(path))


def missing_lab_guid(case: Path) -> None:
    mutate_ifc(case, lambda model: setattr(model.by_guid("1ofMKbkXL90x1LpPKmrjdb"), "GlobalId", "0FAKE00000000000000000"))


def equivalent_ifc_retriangulation(case: Path) -> None:
    def operation(model) -> None:
        roof = model.by_guid("2LzO4ZliP00xdSmna1lWP8")
        representation = next(row for row in roof.Representation.Representations if row.RepresentationIdentifier == "Body")
        face_set = next(row for row in representation.Items if row.is_a("IfcPolygonalFaceSet"))
        face = next(row for row in face_set.Faces if len(row.CoordIndex) == 4)
        a, b, c, d = tuple(face.CoordIndex)
        triangles = (
            model.create_entity("IfcIndexedPolygonalFace", CoordIndex=(a, b, d)),
            model.create_entity("IfcIndexedPolygonalFace", CoordIndex=(b, c, d)),
        )
        face_set.Faces = tuple(row for row in face_set.Faces if row != face) + triangles

    mutate_ifc(case, operation, "stage2.ifc")
    stage2_hash = sha(case / "stage2.ifc")
    arch_path = case / "archicad_handoff.json"
    arch = json.loads(arch_path.read_text(encoding="utf-8-sig"))
    arch["source_sha256"] = stage2_hash
    save_json(arch_path, arch)
    handoff_hash = sha(arch_path)
    report_path = case / "archicad_validation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    report["output_sha256"] = stage2_hash
    save_json(report_path, report)
    report_hash = sha(report_path)
    osm_path = case / "result.osm"
    osm = osm_path.read_text(encoding="utf-8")
    old_stage2 = json.loads((case / "flow_report.json").read_text(encoding="utf-8-sig"))["stage2_sha256"]
    old_handoff = json.loads((case / "flow_report.json").read_text(encoding="utf-8-sig"))["consumed_handoff_sha256"]
    osm = osm.replace(old_stage2, stage2_hash).replace(old_handoff, handoff_hash)
    osm = re.sub(r"Stage2Hash [0-9a-f]{12}", f"Stage2Hash {stage2_hash[:12]}", osm)
    osm = re.sub(r"HandoffHash [0-9a-f]{12}", f"HandoffHash {handoff_hash[:12]}", osm)
    osm_path.write_text(osm, encoding="utf-8")
    osm_hash = sha(osm_path)
    osw_path = case / "workflow.osw"
    osw = json.loads(osw_path.read_text(encoding="utf-8-sig"))
    osw["source_stage2_sha256"] = stage2_hash
    osw["source_handoff_sha256"] = handoff_hash
    save_json(osw_path, osw)
    workflow_hash = sha(osw_path)
    for csv_name in ("model_summary.csv", "energy_report.csv"):
        path = case / csv_name
        text = path.read_text(encoding="utf-8-sig").replace(old_stage2, stage2_hash).replace(old_handoff, handoff_hash)
        path.write_text(text, encoding="utf-8")
    flow_path = case / "flow_report.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8-sig"))
    flow.update({
        "consumed_handoff_sha256": handoff_hash,
        "stage2_sha256": stage2_hash,
        "osm_sha256": osm_hash,
        "energy_report_sha256": sha(case / "energy_report.csv"),
        "workflow_sha256": workflow_hash,
    })
    save_json(flow_path, flow)
    log_path = case / "native_stage_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8-sig"))
    log["stages"][1].update({"output_sha256": stage2_hash, "handoff_sha256": handoff_hash, "validation_report_sha256": report_hash})
    log["stages"][2].update({"input_sha256": stage2_hash, "input_handoff_sha256": handoff_hash, "output_sha256": osm_hash, "workflow_sha256": workflow_hash})
    save_json(log_path, log)


def wrong_space_geometry(case: Path) -> None:
    def operation(model) -> None:
        space = model.by_guid("1ofMKbkXL90x1LpPKmrjdb")
        solid = next(item for rep in space.Representation.Representations for item in rep.Items if item.is_a("IfcExtrudedAreaSolid"))
        solid.Depth = 1.8

    mutate_ifc(case, operation)


def missing_stage2_representation(case: Path) -> None:
    mutate_ifc(case, lambda model: setattr(model.by_guid("1ofMKbkXL90x1LpPKmrjdb"), "Representation", None), "stage2.ifc")


def wrong_stage2_containment(case: Path) -> None:
    def operation(model) -> None:
        space = model.by_guid("1ofMKbkXL90x1LpPKmrjdb")
        relation = next(row for row in space.Decomposes if row.RelatingObject.is_a("IfcBuildingStorey"))
        relation.RelatingObject = model.by_type("IfcBuilding")[0]

    mutate_ifc(case, operation, "stage2.ifc")


def wrong_product_containment(case: Path) -> None:
    def operation(model) -> None:
        wall = model.by_guid("1ofMKbkXL90x1LpPKmrjWL")
        relation = next(row for row in wall.ContainedInStructure if row.RelatingStructure.is_a("IfcBuildingStorey"))
        relation.RelatingStructure = model.by_type("IfcBuilding")[0]

    mutate_ifc(case, operation)


def coherent_forged_revit_log(case: Path) -> None:
    path = case / "native_stage_log.json"
    log = json.loads(path.read_text(encoding="utf-8-sig"))
    revit = log["stages"][0]
    revit["product_version"] = "25.9.9.999"
    revit["product_build"] = "FORGED"
    revit["executable"] = r"C:\fake\Revit.exe"
    revit["started_utc"] = "2026-08-12T13:31:00Z"
    revit["finished_utc"] = "2026-08-12T13:32:00Z"
    save_json(path, log)


def wrong_storey(case: Path) -> None:
    def operation(model) -> None:
        space = model.by_guid("1ofMKbkXL90x1LpPKmrjdb")
        target = model.by_type("IfcBuilding")[0]
        relation = next(row for row in space.Decomposes if row.RelatingObject.is_a("IfcBuildingStorey"))
        relation.RelatingObject = target

    mutate_ifc(case, operation)


def open_roof(case: Path) -> None:
    def operation(model) -> None:
        roof = model.by_guid("2LzO4ZliP00xdSmna1lWP8")
        representation = next(row for row in roof.Representation.Representations if row.RepresentationIdentifier == "Body")
        face_set = next(row for row in representation.Items if row.is_a("IfcPolygonalFaceSet"))
        face_set.Faces = tuple(face_set.Faces[:-1])

    mutate_ifc(case, operation)


def wrong_opening_host(case: Path) -> None:
    def operation(model) -> None:
        relation = model.by_type("IfcRelVoidsElement")[0]
        relation.RelatingBuildingElement = model.by_guid("1ofMKbkXL90x1LpPKmrjWI")

    mutate_ifc(case, operation)


def altered_archicad_rpc(case: Path) -> None:
    path = case / "archicad_validation_report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["native_provenance"]["rpc_transcript"][-1]["request"]["params"]["Location"] = r"C:\fake\stage2.ifc"
    save_json(path, report)


def replace_osm_once(case: Path, pattern: str, replacement: str) -> None:
    path = case / "result.osm"
    text = path.read_text(encoding="utf-8")
    changed, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    assert count == 1, pattern
    path.write_text(changed, encoding="utf-8")
    update_osm_provenance(case)


def wrong_schedule_profile(case: Path) -> None:
    replace_osm_once(case, r"^\s*0\.35,\s*!- Value Until Time 2", "  0.9,                                    !- Value Until Time 2")


def wrong_load(case: Path) -> None:
    replace_osm_once(case, r"^\s*30,\s*!- Watts per Space Floor Area \{W/m2\}", "  80,                                     !- Watts per Space Floor Area {W/m2}")


def wrong_oa(case: Path) -> None:
    replace_osm_once(case, r"^\s*0\.01,\s*!- Outdoor Air Flow per Person \{m3/s-person\}", "  0.001,                                  !- Outdoor Air Flow per Person {m3/s-person}")


def shared_zone(case: Path) -> None:
    path = case / "result.osm"
    text = path.read_text(encoding="utf-8")
    zone_handles = {}
    for match in re.finditer(r"(?ms)^\s*OS:ThermalZone,\s*\n\s*(\{[^}]+\}),\s*!- Handle\s*\n\s*([^,]+),\s*!- Name", text):
        zone_handles[match.group(2).strip()] = match.group(1)
    source = zone_handles["STUDIO-L2-ZN"]
    target = zone_handles["RECEPTION-L1-ZN"]
    prep = re.search(r"(?ms)^\s*OS:Space,.*?^\s*STUDIO-L2,\s*!- Name.*?;\s*!- Design Specification Outdoor Air Object Name", text)
    assert prep
    block = prep.group(0).replace(source, target, 1)
    path.write_text(text[:prep.start()] + block + text[prep.end():], encoding="utf-8")
    update_osm_provenance(case)


def broken_osm_handle(case: Path) -> None:
    replace_osm_once(case, r"\{[0-9a-f-]{36}\};\s*!- Design Specification Outdoor Air Object Name", "{00000000-0000-0000-0000-000000000000}; !- Design Specification Outdoor Air Object Name")


def broken_non_name_osm_handle(case: Path) -> None:
    replace_osm_once(case, r"\{[0-9a-f-]{36}\},\s*!- Zone Air Inlet Port List", "{00000000-0000-0000-0000-000000000000}, !- Zone Air Inlet Port List")


def edited_idf(case: Path) -> None:
    path = case / "in.idf"
    text = path.read_text(encoding="utf-8")
    assert "RECEPTION-L1-ZN" in text
    path.write_text(text.replace("RECEPTION-L1-ZN", "FAKE-CLASSROOM-ZN"), encoding="utf-8")
    update_idf_provenance(case)


def truncated_sql(case: Path) -> None:
    path = case / "run/eplusout.sql"
    path.write_bytes(path.read_bytes()[:4096])
    update_sql_provenance(case)


def update_sql_provenance(case: Path) -> None:
    digest = sha(case / "run/eplusout.sql")
    flow_path = case / "flow_report.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["eplusout_sql_sha256"] = digest
    save_json(flow_path, flow)
    log_path = case / "native_stage_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8"))
    log["stages"][2]["eplusout_sql_sha256"] = digest
    save_json(log_path, log)


def nonannual_zero_sql(case: Path) -> None:
    path = case / "run/eplusout.sql"
    db = sqlite3.connect(str(path))
    db.execute("DELETE FROM Time WHERE TimeIndex > 24")
    db.execute("UPDATE ReportData SET Value=0")
    db.commit()
    db.close()
    update_sql_provenance(case)


CASES = [
    ("native_positive", True, None),
    ("equivalent_osm_reorder", True, equivalent_osm_reorder),
    ("equivalent_ifc_retriangulation", True, equivalent_ifc_retriangulation),
    ("missing_retained_lab_guid", False, missing_lab_guid),
    ("wrong_space_geometry", False, wrong_space_geometry),
    ("wrong_storey_containment", False, wrong_storey),
    ("wrong_product_storey_containment", False, wrong_product_containment),
    ("wrong_stage2_containment", False, wrong_stage2_containment),
    ("missing_stage2_representation", False, missing_stage2_representation),
    ("open_roof_shell", False, open_roof),
    ("wrong_host_opening_graph", False, wrong_opening_host),
    ("altered_archicad_save_rpc", False, altered_archicad_rpc),
    ("wrong_schedule_profile", False, wrong_schedule_profile),
    ("wrong_equipment_load", False, wrong_load),
    ("wrong_outdoor_air", False, wrong_oa),
    ("shared_thermal_zone", False, shared_zone),
    ("broken_osm_handle_graph", False, broken_osm_handle),
    ("broken_non_name_osm_handle_graph", False, broken_non_name_osm_handle),
    ("hand_edited_idf", False, edited_idf),
    ("truncated_sql", False, truncated_sql),
    ("nonannual_zero_energy_sql", False, nonannual_zero_sql),
    ("coherent_forged_revit_log", False, coherent_forged_revit_log),
]


def run(case: Path) -> tuple[bool, list[str]]:
    subprocess.run(["python", str(EVALUATOR), str(case)], check=False, capture_output=True, text=True)
    result = json.loads((case / "multi_metrics.json").read_text(encoding="utf-8"))
    return bool(result["ok"]), list(result["errors"])


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory(prefix="ew3b10-matrix-") as temp:
        for name, expected, mutation in CASES:
            case = Path(temp) / name
            shutil.copytree(SOURCE, case)
            if mutation:
                mutation(case)
            actual, errors = run(case)
            rows.append({"case": name, "expected": expected, "actual": actual, "errors": errors[:6]})
    output = {"passed": all(row["expected"] == row["actual"] for row in rows), "rows": rows}
    (ROOT / "validation_matrix_result.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
