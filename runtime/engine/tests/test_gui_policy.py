import pytest

from mm_agents.agent import _normalize_computer13_action, _validate_pyautogui_cdata


def test_rejects_gui_internal_application_script_paste():
    code = r'''
import pyautogui
payload = """from abaqus import *
from abaqusConstants import *
model = mdb.Model(name='Bypass')
"""
pyautogui.write(payload)
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_rejects_gui_direct_file_fabrication_without_imports():
    code = r'''
import pyautogui
open('/home/user/Desktop/answer.dxf', 'w').write('0\nSECTION\n0\nEOF\n')
pyautogui.click(100, 100)
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_rejects_gui_bulk_cad_command_batch():
    code = r'''
import pyautogui
commands = """rectangle 0,0 1800,700
line 0,0 100,0
circle 20,20 5
polyline 0,0 20,20 40,0
offset 5
trim all
text 20,20 PANEL RELEASE DRAWING"""
pyautogui.write(commands)
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_allows_gui_normal_text_and_filename_entry():
    code = r'''
import pyautogui, time
pyautogui.click(420, 310)
pyautogui.write('/home/user/Desktop/completed_model.FCStd')
pyautogui.press('enter')
time.sleep(0.5)
'''
    _validate_pyautogui_cdata(code)


def test_allows_gui_import_dialog_search_text():
    code = r'''
import pyautogui
pyautogui.click(420, 310)
pyautogui.write('Import STEP')
'''
    _validate_pyautogui_cdata(code)


def test_rejects_gui_browser_local_engineering_artifact_url():
    code = r'''
import pyautogui
pyautogui.click(600, 66)
pyautogui.typewrite('file:///C:/Users/user/Desktop/base_project.schematic.json')
pyautogui.press('enter')
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_rejects_gui_handwritten_json_deliverable():
    code = r'''
import pyautogui
payload = '{"variant":"Lite","fitted":["R1","U1"],"dnp":["R2","C1"],"notes":"direct output"}'
pyautogui.typewrite(payload)
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_rejects_gui_handwritten_csv_deliverable():
    code = r'''
import pyautogui
payload = "variant,ref,value,fitted\nLite,R1,1k,Yes\nLite,R2,10k,No\nLite,C1,100nF,No"
pyautogui.typewrite(payload)
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_allows_gui_plain_text_brief_search():
    code = r'''
import pyautogui
pyautogui.click(420, 310)
pyautogui.write('timer_assembly.txt')
pyautogui.press('enter')
'''
    _validate_pyautogui_cdata(code)


def test_rejects_looped_gui_command_entry():
    code = r'''
import pyautogui
for command in ["circle 0,0 10", "circle 20,20 5"]:
    pyautogui.write(command)
    pyautogui.press("enter")
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_allows_gui_text_entry_helper_for_normal_field():
    code = r'''
import pyautogui
def enter(value):
    pyautogui.write(value)
    pyautogui.press("enter")
enter("M6 mounting hole")
'''
    _validate_pyautogui_cdata(code)


def test_rejects_loop_calling_gui_text_entry_helper():
    code = r'''
import pyautogui, time
def enter(command):
    pyautogui.write(command, interval=0.001)
    pyautogui.press("enter")
    time.sleep(0.08)
for command in ["-LAYER", "RECTANG", "CIRCLE", "SAVEAS"]:
    enter(command)
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_rejects_loop_calling_transitive_gui_text_entry_helper():
    code = r'''
import pyautogui
def type_value(value):
    pyautogui.typewrite(value)
def enter(value):
    type_value(value)
    pyautogui.press("enter")
for value in ["RECTANG", "0,0", "120,80"]:
    enter(value)
'''
    with pytest.raises(ValueError):
        _validate_pyautogui_cdata(code)


def test_allows_looped_gui_clicks_without_typing():
    code = r'''
import pyautogui
for x, y in [(100, 100), (200, 200)]:
    pyautogui.click(x, y)
'''
    _validate_pyautogui_cdata(code)


def test_rejects_computer13_script_typing():
    with pytest.raises(ValueError):
        _normalize_computer13_action({
            "action_type": "TYPING",
            "parameters": {"text": "import bpy\nbpy.ops.wm.save_as_mainfile(filepath='answer.blend')"},
        })


def test_allows_computer13_normal_text_entry():
    kind, payload = _normalize_computer13_action({
        "action_type": "TYPING",
        "parameters": {"text": "M6 mounting hole, 12 mm edge clearance"},
    })
    assert kind == "computer13"
    assert payload["parameters"]["text"].startswith("M6 mounting")
