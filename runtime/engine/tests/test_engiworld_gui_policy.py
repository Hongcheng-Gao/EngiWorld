import pytest

from mm_agents.agent import validate_pyautogui_code


def test_rejects_gui_direct_file_fabrication():
    code = r"""
import pyautogui
open('/home/user/Desktop/answer.dxf', 'w').write('0\nSECTION\n0\nEOF\n')
pyautogui.click(100, 100)
"""
    with pytest.raises(ValueError):
        validate_pyautogui_code(code)


def test_rejects_gui_terminal_hotkey():
    code = r"""
import pyautogui
pyautogui.hotkey('ctrl', 'alt', 't')
"""
    with pytest.raises(ValueError):
        validate_pyautogui_code(code)


def test_rejects_gui_bulk_cad_command_paste():
    code = r"""
import pyautogui
pyautogui.write('''rectangle 0,0 1800,700
line 0,0 100,0
circle 20,20 5
polyline 0,0 20,20 40,0
offset 5
trim all
text 20,20 PANEL RELEASE DRAWING''')
"""
    with pytest.raises(ValueError):
        validate_pyautogui_code(code)


def test_allows_gui_normal_click_and_filename_entry():
    code = r"""
import pyautogui, time
pyautogui.click(420, 310)
pyautogui.write('/home/user/Desktop/completed_model.FCStd')
pyautogui.press('enter')
time.sleep(0.5)
"""
    validate_pyautogui_code(code)
