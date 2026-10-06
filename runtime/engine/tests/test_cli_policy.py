import pytest

from mm_agents.cli_policy import CliPolicyViolation, validate_cli_action


@pytest.mark.parametrize("kind,script", [
    ("python", "import math\nnx = 30\nx2 = nx * 2\nprint('mechanical requirements:', x2)"),
    ("python", "import json\nprint(json.load(open('/tmp/mechanical_requirements.json')))"),
    ("bash", 'python3 -c "\nimport math\nnx = 30\nx2 = nx * 2\nprint(\'mechanical requirements:\', x2)\n"'),
    ("bash", "cat <<'PY' > /tmp/grid.py\nimport math\nnx = 30\nx2 = nx * 2\nprint('mechanical requirements:', x2)\nPY"),
    ("python", 'code = """import math\nnx = 30\nx2 = nx * 2\nprint(\'mechanical requirements:\', x2)\n"""\nopen("/tmp/grid.py", "w").write(code)'),
])
def test_python_data_and_grid_names_are_not_software_commands(kind, script):
    validate_cli_action(kind, script, {"related_apps": ["fenics"]})


@pytest.mark.parametrize("kind,script", [
    ("python", "import subprocess\ncmd = ['blender', '--background']\nsubprocess.run(cmd)"),
    ("python", "from subprocess import run as launch\nexe = 'blender'\nlaunch([exe, '--background'])"),
    ("python", "import os\nlaunch = os.system\ncmd = 'blender --background'\nlaunch(cmd)"),
    ("python", "import subprocess\nsubprocess.run('blen' + 'der --background', shell=True)"),
    ("python", "import win32com.client\nshell = win32com.client.Dispatch('WScript.Shell')\nshell.Run('blender --background')"),
    ("python", "import win32com.client\nwin32com.client.Dispatch('SldWorks.Application')"),
    ("python", "import win32com.client\nwin32com.client.Dispatch('AutoCAD.Application.24')"),
    ("python", 'code = """import os\nos.system(\'blender --background\')\n"""\nopen("/tmp/helper.py", "w").write(code)'),
    ("bash", 'python3 -c "import os; os.system(\'blender --background\')"'),
    ("bash", "cat <<'PY' > /tmp/helper.py\nimport subprocess\nsubprocess.run(['blender', '--background'])\nPY"),
    ("bash", "python3 -c 'print(123)'\nblender --background"),
    ("bash", '"/opt/blender/blender" --background'),
])
def test_cross_software_launches_stay_restricted(kind, script):
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(kind, script, {"related_apps": ["freecad"]})


@pytest.mark.parametrize("module,software", [
    ("MeshPart", "freecad"), ("MeshPart", "freecad-path"),
    ("bpy_extras", "blender"), ("bpy_extras", "bonsai"),
    ("_pcbnew", "kicad"), ("backwardCompatibility", "abaqus"),
])
def test_official_modules_are_scoped_to_their_software(module, software):
    validate_cli_action("python", f"import {module}", {"related_apps": [software]})
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", f"import {module}", {"related_apps": ["autocad"]})
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", f"import {module}\nimport numpy", {"related_apps": [software]})


@pytest.mark.parametrize("script", [
    "import ctypes\nsend = ctypes.windll.user32.SendMessageW\nsend(123, 0x00f5, 0, 0)",
    "from win32gui import SendMessage as send\nsend(123, 0x186, 2, 0)",
])
@pytest.mark.parametrize("text_only", [False, True])
def test_orcad_native_dialog_messages_are_allowed(script, text_only):
    validate_cli_action("python", script, {"related_apps": ["cadence-orcad"]}, text_only=text_only)


def test_solidcam_host_api_is_allowed():
    script = ("import win32com.client\n"
              "app = win32com.client.Dispatch('SldWorks.Application')\n"
              "cam = app.GetAddInObject('CAMWorks.Addin')\n"
              "print('SOLIDWORKS CAM:', cam)")
    validate_cli_action("python", script, {"related_apps": ["solidcam"]})
    validate_cli_action("bash", '"C:/Program Files/SOLIDWORKS Corp/SOLIDWORKS/SLDWORKS.exe"',
                        {"related_apps": ["solidcam"]})


def test_orcad_native_simulator_command_is_allowed():
    validate_cli_action("python", "import subprocess\nsubprocess.run([r'C:\\Cadence\\SPB_24.1\\tools\\bin\\psp_cmd.exe', r'C:\\temp\\test.cir'])",
                        {"related_apps": ["cadence-orcad"]})


def test_native_cli_process_output_is_not_an_engineering_file_read():
    script = ("import subprocess\n"
              "proc = subprocess.Popen(['IFCCommandServerApp.exe', '--c'], "
              "stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)\n"
              "proc.stdin.write('load input.ifc')\n"
              "print(proc.stdout.read())")
    validate_cli_action("python", script, {"related_apps": ["archicad"]})
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", script + "\nprint(open('input.ifc').read())",
                            {"related_apps": ["archicad"]})


@pytest.mark.parametrize("kind, script, software", [
    ("python", "from PIL import Image\nImage.open('/tmp/input.png').crop((0, 0, 10, 10)).save('/tmp/crop.png')", "freecad"),
    ("bash", 'python3 -c "import PIL; print(PIL.__version__)"', "freecad"),
    ("python", "import bpy\nnx = 64\nny = 64\nprint(nx * ny)", "blender"),
    ("bash", '/opt/blender/blender -b --python-expr "\nimport bpy\nimport addon_utils\nprint(addon_utils.paths())\n"', "blender"),
    ("bash", 'freecadcmd-python3 -c "import FreeCAD, Part, math; import ImportGui; print(FreeCAD.Version())"', "freecad"),
    ("bash", 'freecadcmd -c "import Part; shape = Part.read(\'/home/user/Desktop/result.step\'); print(shape.isValid(), shape.Volume)"', "freecad"),
    ("python", 'import subprocess\ncode = """\nimport FreeCAD\nprint(FreeCAD.Version())\n"""\nsubprocess.run(["python3", "-c", code], check=True)', "freecad"),
    ("python", '# Do not use System.Drawing.CopyFromScreen (screen capture).\n', "solidworks"),
])
def test_allows_image_processing_and_official_api_actions(kind, script, software):
    validate_cli_action(kind, script, {"id": f"{software}-task-01-ubuntu"})


@pytest.mark.parametrize("kind, script", [
    ("bash", 'python3 -c "import numpy; print(numpy.__version__)"'),
    ("python", 'import os\nos.system("blender --background")'),
    ("python", 'import subprocess\nsubprocess.run(["blender", "--background"])'),
    ("bash", "blender"),
    ("bash", "code /tmp/script.py"),
    ("python", 'import subprocess\nsubprocess.run(["code", "/tmp/script.py"])'),
])
def test_command_and_import_checks_remain_active(kind, script):
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(kind, script, {"id": "freecad-task-01-ubuntu"})


@pytest.mark.parametrize("script", [
    "from PIL import ImageGrab as capture\ncapture.grab()",
    "from PIL.ImageGrab import grab\ngrab()",
    "import PIL.ImageGrab as capture\ncapture.grab()",
])
def test_pillow_desktop_capture_aliases_are_rejected(script):
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", script, {"id": "freecad-task-01-ubuntu"})


@pytest.mark.parametrize("text_only", [False, True])
@pytest.mark.parametrize("script", [
    "from PIL import Image\nImage.open('/tmp/input.png').rotate(90).save('/tmp/crop.png')",
    "from PIL import Image as Img\np='/tmp/render.png'\nImg.open(p)",
    "import struct, zlib\np='/tmp/render.png'\ndata=open(p, 'rb').read()",
    "import bpy\nimg=bpy.data.images.load('/tmp/render.png')\nprint(list(img.pixels)[:12])",
])
def test_programmatic_image_processing_in_both_profiles(text_only, script):
    validate_cli_action("python", script, {"id": "blender-task-01-ubuntu"}, text_only=text_only)


@pytest.mark.parametrize("text_only", [False, True])
def test_desktop_capture_stays_restricted_in_both_profiles(text_only):
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", "from PIL import ImageGrab\nImageGrab.grab()",
                           {"id": "blender-task-01-ubuntu"}, text_only=text_only)


@pytest.mark.parametrize(
    "kind, script",
    [
        (
            "bash",
            "Add-Type -AssemblyName System.Drawing; "
            "$g = [System.Drawing.Graphics]::FromImage($b); "
            "$g.CopyFromScreen(0, 0, 0, 0, $b.Size)",
        ),
        ("python", "from PIL import ImageGrab\nImageGrab.grab().save('screen.png')"),
        ("bash", "xwd -root -out /tmp/screen.xwd"),
        ("python", "import pyautogui\npyautogui.click(100, 200)"),
        ("bash", "[System.Windows.Forms.SendKeys]::SendWait('%{F4}')"),
        ("bash", "xdotool mousemove 100 200 click 1"),
    ],
)
def test_rejects_terminal_desktop_capture_and_input(kind, script):
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(kind, script, {"id": "freecad-task-01-windows"})


def test_allows_system_drawing_without_desktop_capture():
    script = (
        "Add-Type -AssemblyName System.Drawing; "
        "$bitmap = New-Object System.Drawing.Bitmap(100, 100); "
        "$bitmap.Save('C:\\\\Users\\\\user\\\\Desktop\\\\preview.png')"
    )
    validate_cli_action("bash", script, {"id": "freecad-task-01-windows"})


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


def test_rejects_placeholder_step_write_hidden_in_path_join():
    script = r"""
import bpy, os
path = os.path.join('/home/user/Desktop', '03_freecad_assembly.step')
payload = "ISO-10303-21;\nEND-ISO-10303-21;\n"
open(path, 'w', encoding='utf-8').write(payload)
bpy.ops.wm.save_as_mainfile(filepath='/home/user/Desktop/review.blend')
"""
    task = {
        "id": "c-cli-4-kicad-openscad-freecad-blender-task-01-ubuntu",
        "related_apps": ["kicad", "openscad", "freecad", "blender"],
    }
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", script, task)


def test_rejects_inline_path_join_artifact_write_with_target_api_present():
    script = r"""
import pcbnew, os
board = pcbnew.NewBoard()
open(os.path.join('/home/user/Desktop', 'fake.step'), 'w').write('ISO-10303-21;')
"""
    task = {
        "id": "c-cli-4-kicad-openscad-freecad-blender-task-01-ubuntu",
        "related_apps": ["kicad", "openscad", "freecad", "blender"],
    }
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", script, task)


def test_allows_target_api_with_artifact_path_variable():
    script = r"""
import pcbnew, os
board = pcbnew.NewBoard()
output = os.path.join('/home/user/Desktop', '01_kicad_board.kicad_pcb')
pcbnew.SaveBoard(output, board)
"""
    validate_cli_action("python", script, {"id": "kicad-task-01-ubuntu"})


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


@pytest.mark.parametrize("family", ["open", "software-selection"])
def test_software_selection_retains_its_integrity_rules_after_rename(family):
    task = _open_task_config()
    task["_engiworld_task_family"] = family
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("bash", "pip install cadquery", task)


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


def _archive_task_config():
    return {
        "id": "c-multi-archicad-openstudio-task-01-windows",
        "related_apps": ["archicad", "openstudio"],
        "_engiworld_task_family": "multi",
        "_engiworld_expected_outputs": [
            "stage1.ifc",
            "handoff.json",
            "result.osm",
            "flow_report.json",
            "model_summary.csv",
        ],
        "config": [{
            "type": "upload_file",
            "parameters": {"files": [{
                "local_path": "task-01/init_file/assets.zip",
                "path": r"C:\Users\user\Desktop\assets.zip",
            }]},
        }],
    }


def test_rejects_historical_ground_truth_archive_extraction():
    script = r"""
unzip -j /c/Users/user/Desktop/Engiworld/task/multi/cli-2-archicad-openstudio-native-gt.zip \
  task-01/ground_truth/stage1.ifc \
  task-01/ground_truth/handoff.json \
  task-01/ground_truth/result.osm \
  task-01/ground_truth/flow_report.json \
  task-01/ground_truth/model_summary.csv
"""
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("bash", script, _archive_task_config())


def test_rejects_listing_archive_not_declared_as_task_input():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "unzip -l /c/Users/user/Desktop/cli2_archicad_openstudio_task.zip",
            _archive_task_config(),
        )


def test_rejects_python_archive_not_declared_as_task_input():
    script = r"""
import zipfile
with zipfile.ZipFile(r'C:\Users\user\Desktop\answers.zip') as archive:
    print(archive.namelist())
"""
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("python", script, _archive_task_config())


def test_rejects_direct_evaluator_material_read():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action(
            "bash",
            "cat /c/Users/user/Desktop/task-01/ground_truth/GT_GENERATION.md",
            _archive_task_config(),
        )


def test_allows_declared_open_input_read_when_target_app_is_also_invoked():
    task = _open_task_config()
    task["config"][0]["parameters"]["files"].append({
        "local_path": "task-01/init_file/base_project.schematic.json",
        "path": r"C:\Users\user\Desktop\base_project.schematic.json",
    })
    task["config"][0]["parameters"]["files"].append({
        "local_path": "task-01/init_file/base_project.edif",
        "path": r"C:\Users\user\Desktop\base_project.edif",
    })
    script = r'''
cat /c/Users/user/Desktop/base_project.schematic.json
"/c/Cadence/SPB_24.1/tools/bin/Capture.exe" "C:\Users\user\Desktop\base_project.edif"
'''
    validate_cli_action("bash", script, task)


def test_rejects_undeclared_open_artifact_read_even_when_target_app_is_invoked():
    task = _open_task_config()
    script = r'''
cat /c/Users/user/Desktop/answer.sch
"/c/Cadence/SPB_24.1/tools/bin/Capture.exe" "C:\Users\user\Desktop\design_a.schematic.json"
'''
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("bash", script, task)


def test_rejects_windows_type_read_of_undeclared_artifact_even_with_target_app():
    task = _open_task_config()
    script = r'''
type C:\Users\user\Desktop\answer.sch
"C:\Cadence\SPB_24.1\tools\bin\Capture.exe" C:\Users\user\Desktop\fulladd.edif
'''
    with pytest.raises(CliPolicyViolation):
        validate_cli_action("bash", script, task)


def test_allows_declared_task_input_archive():
    validate_cli_action(
        "bash",
        "unzip -l /c/Users/user/Desktop/assets.zip",
        _archive_task_config(),
    )
