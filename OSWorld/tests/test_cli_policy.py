import pytest

from mm_agents.cli_policy import CliPolicyViolation, validate_cli_action


def test_allows_target_application_helper_script():
    code = r"""
cat > /c/Users/user/Desktop/build_plate.py <<'PY'
from abaqus import *
from abaqusConstants import *
import os
PY
cmd.exe /c "C:\SIMULIA\Commands\abaqus.bat cae noGUI=C:\Users\user\Desktop\build_plate.py"
"""
    validate_cli_action("bash", code, {"id": "abaqus-task-01-windows"})


def test_rejects_package_install():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "import subprocess, sys\nsubprocess.run([sys.executable, '-m', 'pip', 'install', 'olefile'])",
            {"id": "altium-designer-task-01-windows"},
        )


def test_rejects_third_party_file_parser():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "import olefile\nprint(olefile.OleFileIO('x.PcbDoc'))",
            {"id": "altium-designer-task-01-windows"},
        )


def test_rejects_disallowed_module_in_multi_import():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "import os, re, olefile, struct\nprint(olefile.OleFileIO('x.PcbDoc'))",
            {"id": "altium-designer-task-01-windows"},
        )


def test_rejects_manual_binary_artifact_parser():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "import struct\np='C:/Users/user/Desktop/broken.PcbDoc'\ndata=open(p,'rb').read()\nprint(struct.unpack_from('<I', data, 0x30))",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_python_artifact_copy():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "import shutil\nshutil.copy2('broken.PcbDoc', 'fixed.PcbDoc')",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_indirect_python_artifact_write():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "src = 'broken.PcbDoc'\ndst = 'fixed.PcbDoc'\ndata = open(src, 'rb').read()\nopen(dst, 'wb').write(data)",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_indirect_python_artifact_read_for_manual_inspection():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "path = 'broken.PcbDoc'\ndata = open(path, 'rb').read()\nprint(data[:64].hex())",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_shell_artifact_copy():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "cp /c/Users/user/Desktop/broken.PcbDoc /c/Users/user/Desktop/fixed.PcbDoc",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_shell_artifact_inspection():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "strings -a /c/Users/user/Desktop/broken.PcbDoc | grep RECORD",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_indented_shell_artifact_inspection():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "if [ -f broken.PcbDoc ]; then\n  file broken.PcbDoc\nfi",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_shell_artifact_variable_inspection():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "f=/c/Users/user/Desktop/broken.PcbDoc\nfile \"$f\" || true\nhead -c 256 \"$f\" | od -An -tx1",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_shell_for_loop_artifact_variable_inspection():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "for f in /c/Users/user/Desktop/a.PcbDoc /tmp/a.PcbDoc; do\n  file \"$f\"\ndone",
            {"id": "altium-designer-task-02-windows"},
        )


def test_rejects_direct_in_place_text_edit():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "sed -i 's/old/new/g' /c/Users/user/Desktop/design.kicad_pcb",
            {"id": "kicad-task-01-windows"},
        )


def test_rejects_perl_in_place_option_variants():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "perl -0pi -e 's/old/new/' /home/user/Desktop/lift_drag.py",
            {"id": "fenics-task-19-ubuntu"},
        )


def test_allows_sed_print_piped_to_grep():
    validate_cli_action(
        "bash",
        "sed -n '1,120p' /tmp/report.txt | grep -i report",
        {"id": "cadence-orcad-task-30-windows"},
    )


def test_rejects_non_target_software():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "blender --background --python fix.py",
            {"id": "kicad-task-01-ubuntu"},
        )


def test_allows_code_named_installation_path():
    validate_cli_action(
        "bash",
        r'"/c/SIMULIA/CAE/2025LE/win_b64/code/bin/SMALauncherLE.exe" information=system',
        {"id": "abaqus-task-01-windows"},
    )


def test_allows_freecad_path_official_module():
    validate_cli_action(
        "python",
        "import FreeCAD\nimport Path\nimport Path.Main.Job as PathJob\nprint(PathJob)",
        {"id": "freecad-path-task-01-ubuntu"},
    )


def test_allows_target_api_saving_artifact():
    validate_cli_action(
        "python",
        "import bpy\nbpy.ops.wm.save_as_mainfile(filepath='/home/user/Desktop/result.blend')",
        {"id": "blender-task-01-ubuntu"},
    )


def test_allows_multi_task_related_app_commands():
    task = {
        "id": "c-cli-4-kicad-openscad-freecad-blender-task-01-ubuntu",
        "related_apps": ["kicad", "openscad", "freecad", "blender"],
    }
    validate_cli_action(
        "bash",
        "kicad-cli version\nopenscad --version\nfreecadcmd --version\nblender --background --version",
        task,
    )


def test_related_apps_still_reject_unlisted_software():
    task = {
        "id": "c-cli-4-kicad-openscad-freecad-blender-task-01-ubuntu",
        "related_apps": ["kicad", "openscad", "freecad", "blender"],
    }
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("bash", "abaqus cae noGUI=solve.py", task)


def _open_task_config():
    return {
        "id": "c-open-altium-designer-cadence-orcad-openscad-task-01-windows",
        "related_apps": ["altium-designer", "cadence-orcad", "openscad"],
        "_engiworld_task_family": "open",
        "_engiworld_expected_outputs": ["merged_refdes.txt"],
        "config": [{
            "type": "upload_file",
            "parameters": {"files": [{
                "local_path": "task-01/init_file/design_a.schematic.json",
                "path": "C:\\Users\\user\\Desktop\\design_a.schematic.json",
            }]},
        }],
    }


def test_rejects_open_task_neutral_json_parsing_with_powershell():
    script = r"""
$j = Get-Content C:\Users\user\Desktop\design_a.schematic.json -Raw | ConvertFrom-Json
$j.parts.ref | Set-Content C:\Users\user\Desktop\merged_refdes.txt
"""
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("bash", script, _open_task_config())


def test_rejects_open_task_neutral_json_parsing_with_generic_python():
    script = r"""
import json
data = json.load(open(r'C:\Users\user\Desktop\design_a.schematic.json'))
with open(r'C:\Users\user\Desktop\merged_refdes.txt', 'w') as out:
    out.write('\n'.join(data['refs']))
"""
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", script, _open_task_config())


def test_rejects_ifcopenshell_for_non_bonsai_open_task():
    task = {
        "id": "c-open-revit-archicad-abaqus-task-01-windows",
        "related_apps": ["revit", "archicad", "abaqus"],
    }
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "import ifcopenshell\nmodel = ifcopenshell.open('init.ifc')",
            task,
        )


def test_rejects_base64_wrapped_execution():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "python",
            "import base64\nexec(base64.b64decode(payload).decode())",
            {"id": "kicad-task-01-ubuntu"},
        )


def test_rejects_manual_gcode_even_with_freecad_import():
    script = r"""
import FreeCAD
out = '/home/user/Desktop/task-01.nc'
lines = ['G21', 'G90', 'G0 X0 Y0', 'M30']
with open(out, 'w') as stream:
    stream.write('\n'.join(lines))
"""
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", script, {"id": "freecad-path-task-01-ubuntu"})


def test_allows_freecad_path_official_postprocessor():
    script = r"""
import FreeCAD
import Path
from PathScripts import PathPost
PathPost.export(job, '/home/user/Desktop/task-01.nc', 'linuxcnc')
"""
    validate_cli_action("python", script, {"id": "freecad-path-task-01-ubuntu"})


def test_allows_openscad_source_creation_and_compile():
    script = r"""
cat > /home/user/Desktop/model.scad <<'SCAD'
difference() { cube([20, 20, 10]); cylinder(h=10, d=5); }
SCAD
openscad -o /home/user/Desktop/model.stl /home/user/Desktop/model.scad
"""
    validate_cli_action("bash", script, {"id": "openscad-task-01-ubuntu"})


def test_allows_fenics_program_source():
    script = r"""
cat > /home/user/Desktop/solve.py <<'PY'
from fenics import *
mesh = UnitSquareMesh(16, 16)
print(mesh.num_cells())
PY
python /home/user/Desktop/solve.py
"""
    validate_cli_action("bash", script, {"id": "fenics-task-01-ubuntu"})
