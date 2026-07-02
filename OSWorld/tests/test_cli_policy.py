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
