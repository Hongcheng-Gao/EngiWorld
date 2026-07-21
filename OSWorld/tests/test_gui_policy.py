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
