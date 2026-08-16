from pathlib import Path
from shutil import which
import glob
import math
import os
import re
import subprocess
import tempfile


FLUENT_EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\fluent\ntbin\win64\fluent.exe"
DESKTOP = Path(r"C:\Users\user\Desktop")
CASE_FILE = DESKTOP / "pipe_laminar.cas"
DATA_FILE = DESKTOP / "pipe_laminar.dat"
REQUIRED_FILES = (CASE_FILE, DATA_FILE)
FLOAT_RE = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def is_nonempty_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def find_fluent_executable() -> str:
    explicit = Path(FLUENT_EXEC_FILE)
    if explicit.is_file():
        return str(explicit)
    command = which("fluent")
    if command:
        return command
    candidates = []
    for key, value in os.environ.items():
        if key.startswith("AWP_ROOT"):
            candidates.append(Path(value) / "fluent" / "ntbin" / "win64" / "fluent.exe")
    for pattern in (
        r"C:\Program Files\ANSYS Inc\ANSYS Student\v*\fluent\ntbin\win64\fluent.exe",
        r"C:\Program Files\ANSYS Inc\v*\fluent\ntbin\win64\fluent.exe",
    ):
        candidates.extend(Path(item) for item in glob.glob(pattern))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError("Fluent executable not found")


def decode_case(path: Path) -> str:
    return path.read_bytes().decode("latin-1", errors="ignore")


def extract_zone(text: str, zone_type: str, zone_name: str) -> str:
    start = re.search(
        rf"\(39\s+\([^\n]*\b{re.escape(zone_type)}\s+{re.escape(zone_name)}\s+1\)\(",
        text,
        flags=re.I,
    )
    if not start:
        return ""
    following = text[start.start() :]
    end = following.find("\n(39 ", 5)
    return following if end < 0 else following[:end]


def case_configuration_is_valid(path: Path) -> bool:
    text = decode_case(path)
    low = text.lower()
    required = (
        '(0 "fluent26.1.',
        "(2 3)",
        "(rp-3d? . #t)",
        "(rp-double? . #t)",
        "(rp-seg? . #t)",
        "(rp-unsteady? . #f)",
        "(rp-lam? . #t)",
        "(rp-turb? . #f)",
        "(rp-visc? . #t)",
        "(flow/scheme 20)",
        "(pressure/scheme 12)",
        "(mom/scheme 1)",
        "(density (constant . 998.2)",
        "(viscosity (constant . 0.001003)",
        "(material . water-liquid)",
        "(cfd-post-mesh-info ((0 0 (fluid) (wall wall fluid) (outlet pressure-outlet fluid) (inlet velocity-inlet fluid)))",
    )
    if not all(token in low for token in required):
        return False

    inlet = extract_zone(text, "velocity-inlet", "inlet").lower()
    outlet = extract_zone(text, "pressure-outlet", "outlet").lower()
    wall = extract_zone(text, "wall", "wall").lower()
    return (
        "(vmag (constant . 0.1)" in inlet
        and "(flow-direction-component ((constant . 1)" in inlet
        and "(p (constant . 0)" in outlet
        and "(moving? . #f)" in wall
    )


def extract_predictions(root: Path) -> dict:
    journal = """/file/read-case-data pipe_laminar.cas
/mesh/check
/report/surface-integrals/area-weighted-avg outlet () x-velocity no
/exit yes
"""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="ascii", suffix=".jou", dir=root, delete=False
    ) as stream:
        stream.write(journal)
        journal_path = Path(stream.name)
    try:
        proc = subprocess.run(
            [find_fluent_executable(), "3ddp", "-g", "-t1", "-i", journal_path.name],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if (
            proc.returncode != 0
            or "Error:" in output
            or 'Reading "pipe_laminar.cas"' not in output
            or 'Reading "pipe_laminar.dat"' not in output
            or "Checking mesh" not in output
            or "Done." not in output
        ):
            raise RuntimeError("Fluent did not load and check the case/data cleanly")

        extents = {}
        for axis in "xyz":
            match = re.search(
                rf"{axis}-coordinate:\s*min \(m\) =\s*({FLOAT_RE}),\s*max \(m\) =\s*({FLOAT_RE})",
                output,
                flags=re.I,
            )
            if not match:
                raise RuntimeError(f"{axis} extent not found")
            extents[axis] = (float(match.group(1)), float(match.group(2)))

        patterns = {
            "nodes": r"(\d+)\s+nodes,\s+binary",
            "hexahedral_cells": r"(\d+)\s+hexahedral cells",
            "interior_faces": r"(\d+)\s+quadrilateral interior faces",
            "inlet_faces": r"(\d+)\s+quadrilateral velocity-inlet faces",
            "outlet_faces": r"(\d+)\s+quadrilateral pressure-outlet faces",
            "wall_faces": r"(\d+)\s+quadrilateral wall faces",
        }
        predictions = {"extents": extents}
        for key, pattern in patterns.items():
            match = re.search(pattern, output, flags=re.I)
            if not match:
                raise RuntimeError(f"{key} not found")
            predictions[key] = int(match.group(1))

        volume = re.search(rf"minimum volume \(m3\):\s*({FLOAT_RE})", output, flags=re.I)
        velocities = re.findall(rf"^\s*outlet\s+({FLOAT_RE})\s*$", output, flags=re.I | re.M)
        if not volume or not velocities:
            raise RuntimeError("cell volume or outlet velocity not found")
        predictions["minimum_cell_volume_m3"] = float(volume.group(1))
        predictions["outlet_mean_x_velocity_m_s"] = float(velocities[-1])
        return predictions
    finally:
        try:
            journal_path.unlink()
        except OSError:
            pass


def solution_and_near_wall_layers_are_valid(root: Path, outlet_mean: float) -> bool:
    import ansys.fluent.core as pyfluent
    from ansys.fluent.core.services.field_data import SurfaceDataType

    solver = pyfluent.launch_fluent(
        mode="solver",
        precision="double",
        processor_count=1,
        dimension=3,
        ui_mode="no_gui",
        start_watchdog=False,
    )
    try:
        solver.settings.file.read_case_data(file_name=str(root / CASE_FILE.stem))
        plane_name = "__eval_mid_plane"
        solver.settings.results.surfaces.plane_surface[plane_name] = {
            "method": "yz-plane",
            "x": 0.05,
        }
        surface_data = solver.fields.field_data.get_surface_data(
            data_types=[SurfaceDataType.Vertices, SurfaceDataType.FacesConnectivity],
            surfaces=[plane_name],
        )[plane_name]
        vertices = surface_data[SurfaceDataType.Vertices]
        faces = surface_data[SurfaceDataType.FacesConnectivity]
        if len(vertices) < 25 or len(faces) < 16:
            return False

        radii = [math.hypot(float(row[1]), float(row[2])) for row in vertices]
        if max(radii) > 0.00202 or abs(max(radii) - 0.002) > 2e-5:
            return False

        adjacency = [set() for _ in vertices]
        for face in faces:
            indices = [int(value) for value in face]
            for index, first in enumerate(indices):
                second = indices[(index + 1) % len(indices)]
                adjacency[first].add(second)
                adjacency[second].add(first)

        wall_vertices = [index for index, radius in enumerate(radii) if radius >= 0.00198]
        if len(wall_vertices) < 16:
            return False
        chains = 0
        for start in wall_vertices:
            current = start
            for _ in range(3):
                candidates = [
                    neighbor
                    for neighbor in adjacency[current]
                    if 1e-7 < radii[current] - radii[neighbor] < 5e-4
                ]
                if not candidates:
                    break
                current = min(candidates, key=lambda neighbor: radii[current] - radii[neighbor])
            else:
                chains += 1
        if chains < 0.8 * len(wall_vertices):
            return False

        velocity = solver.fields.field_data.get_scalar_field_data(
            field_name="x-velocity",
            surfaces=[plane_name],
        )[plane_name]
        wall_velocity = [abs(float(velocity[index])) for index in wall_vertices]
        core_velocity = [
            float(value)
            for value, radius in zip(velocity, radii)
            if radius <= 0.0005
        ]
        if not core_velocity or max(float(value) for value in velocity) < 1.25 * outlet_mean:
            return False
        if sum(core_velocity) / len(core_velocity) < 1.15 * outlet_mean:
            return False
        if max(wall_velocity) > 0.05 * outlet_mean:
            return False

        pressure = solver.fields.field_data.get_scalar_field_data(
            field_name="pressure",
            surfaces=["inlet", "outlet"],
        )
        inlet_pressure = sum(float(value) for value in pressure["inlet"]) / len(pressure["inlet"])
        outlet_pressure = sum(float(value) for value in pressure["outlet"]) / len(pressure["outlet"])
        return 1.0 < inlet_pressure - outlet_pressure < 1000.0
    finally:
        solver.exit()


def predictions_are_valid(predictions: dict) -> bool:
    targets = {
        "x": (0.0, 0.100),
        "y": (-0.002, 0.002),
        "z": (-0.002, 0.002),
    }
    for axis, expected in targets.items():
        actual = predictions["extents"][axis]
        if any(abs(got - want) > 2e-5 for got, want in zip(actual, expected)):
            return False
    if not (500 <= predictions["nodes"] <= 2_000_000):
        return False
    if not (500 <= predictions["hexahedral_cells"] <= 2_000_000):
        return False
    if predictions["interior_faces"] <= predictions["hexahedral_cells"]:
        return False
    if predictions["inlet_faces"] < 20 or predictions["outlet_faces"] < 20:
        return False
    if predictions["wall_faces"] < 100:
        return False
    if predictions["minimum_cell_volume_m3"] <= 0.0:
        return False
    return 0.095 <= predictions["outlet_mean_x_velocity_m_s"] <= 0.105


def kill_fluent_related() -> None:
    for image in ("fluent.exe", "cortex.exe"):
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/IM", image],
                capture_output=True,
                creationflags=0x08000000,
            )
        except Exception:
            pass


def evaluate() -> bool:
    kill_fluent_related()
    if any(not is_nonempty_file(path) for path in REQUIRED_FILES):
        return False
    try:
        if not case_configuration_is_valid(CASE_FILE):
            return False
        predictions = extract_predictions(DESKTOP)
        return predictions_are_valid(predictions) and solution_and_near_wall_layers_are_valid(
            DESKTOP,
            predictions["outlet_mean_x_velocity_m_s"],
        )
    except Exception:
        return False


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
