import pytest

from mm_agents.cli_policy import CliPolicyViolation, validate_cli_action


@pytest.mark.parametrize('kind,script,software', [
    ('bash', "cat <<'PY' > /tmp/grid.py\nimport math\nfor i in range(3):\n    nx = i + 1\n    print(nx)\nPY\npython /tmp/grid.py", 'blender'),
    ('bash', "cat <<'CS' > /tmp/build.cs\nusing System;\nclass Model { void Build() { double nx = 2; double x = nx * 3; } }\nCS", 'solidworks'),
    ('bash', "cat <<'SCAD' > /tmp/model.scad\n// Mechanical dimensions\ncube([10,10,10]);\nSCAD", 'openscad'),
    ('bash', 'cat <<\'JSON\' > /tmp/notes.json\n{"description":"mechanical reference"}\nJSON', 'freecad'),
    ('python', 'import subprocess\ncode="import FreeCAD; Part.read(\'result.step\')"\nwith open("/tmp/helper.py", "w") as f:\n    f.write(code)\nsubprocess.run(["freecadcmd", "/tmp/helper.py"])', 'freecad'),
])
def test_driver_sources_and_data_are_not_software_commands(kind, script, software):
    validate_cli_action(kind, script, {'related_apps':[software]})


HTTP_SCRIPT = '''import urllib.request
import urllib.error
import json
req = urllib.request.Request("http://127.0.0.1:19723", data=json.dumps({"file":"input.ifc"}).encode())
try:
    with urllib.request.urlopen(req) as response:
        print(response.read())
except urllib.error.HTTPError as error:
    print(error.read())
'''


def test_http_response_body_is_not_engineering_file_read():
    validate_cli_action('python', HTTP_SCRIPT, {'related_apps':['archicad']})


def test_http_response_with_formatted_port():
    script=HTTP_SCRIPT.replace('"http://127.0.0.1:19723"','f"http://127.0.0.1:{19723}"')
    validate_cli_action('python',script,{'related_apps':['archicad']})


@pytest.mark.parametrize('suffix', [
    '\nprint(open("input.ifc", "r").read())',
    '\nwith open("input.ifc", "rb") as response:\n    print(response.read())',
    '\nresponse = open("input.ifc", "rb")\nprint(response.read())',
])
def test_http_call_does_not_authorize_file_reads(suffix):
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('python', HTTP_SCRIPT + suffix, {'related_apps':['archicad']})


def test_urlopen_file_url_stays_restricted():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('python', 'import urllib.request\nwith urllib.request.urlopen("file:///tmp/result.step") as r:\n    print(r.read())', {'related_apps':['freecad']})


@pytest.mark.parametrize('script', [
    'import os\nwith open("/tmp/result.step", "w") as f:\n    f.write("replacement")',
    'cat <<\'PY\' > /tmp/helper.py\nimport subprocess\nsubprocess.run(["blender","--background"])\nPY',
    'cat <<\'CS\' > /tmp/helper.cs\nusing System;\nclass X { void Run() { double nx=3; System.Diagnostics.Process.Start("freecad"); } }\nCS',
])
def test_artifact_writes_and_other_software_are_still_rejected(script):
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('bash' if script.startswith('cat ') else 'python', script, {'related_apps':['autocad']})


@pytest.mark.parametrize('module', ['PartDesign','Drawing','importOBJ','linuxcnc_post','PathTests'])
def test_freecad_modules_are_scoped(module):
    validate_cli_action('python', f'import {module}', {'related_apps':['freecad-path']})
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('python', f'import {module}', {'related_apps':['autocad']})


def test_openfast_official_io_is_scoped_to_openfast():
    validate_cli_action('python','import openfast_io',{'related_apps':['openfast']})
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('python','import openfast_io',{'related_apps':['autocad']})


def test_comtypes_targets_follow_software_policy():
    script='import comtypes.client\napp=comtypes.client.CreateObject("SldWorks.Application")'
    validate_cli_action('python',script,{'related_apps':['solidworks']})
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('python',script,{'related_apps':['autocad']})


@pytest.mark.parametrize('extension', ['scr','lsp','pas','scad','py'])
def test_writing_named_driver_source_is_not_reading_its_input(extension):
    script=f'import subprocess\nsource="/tmp/driver.{extension}"\nwith open(source,"w") as f:\n    f.write("load input.dxf")\n'
    validate_cli_action('python',script,{'related_apps':['autocad']})


def test_log_mentions_do_not_turn_it_into_a_cad_file_read():
    script='journal="/tmp/journal.txt"\nwith open(journal,"r") as f:\n    text=f.read()\nprint(text.count("result.ifc"))'
    validate_cli_action('python',script,{'related_apps':['revit']})
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('python',script+'\nwith open("result.ifc","r") as f:\n    print(f.read())',{'related_apps':['revit']})


def test_compound_engineering_suffix_is_not_a_helper_json():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('python','path="/tmp/answer.schematic.json"\nprint(open(path).read())',{'related_apps':['kicad']})


def test_scored_json_writes_remain_restricted():
    with pytest.raises(CliPolicyViolation):
        validate_cli_action('python','open("/tmp/dsp_result.json","w").write("{}")',
                            {'related_apps':['cadence-orcad'],'_engiworld_expected_outputs':['dsp_result.json']})
