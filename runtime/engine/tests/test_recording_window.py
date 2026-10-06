import ast
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('platform_name,expected_flags', [('Windows',0x08000000),('Linux',0)])
def test_recording_process_window_flags(tmp_path, platform_name, expected_flags):
    source=Path(__file__).parents[1]/'desktop_env/server/main.py'
    tree=ast.parse(source.read_text())
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='start_recording')
    function.decorator_list=[]
    captured={}
    def popen(command,**kwargs):
        captured.update(kwargs)
        def wait(timeout):
            raise subprocess.TimeoutExpired(command,timeout)
        return SimpleNamespace(wait=wait)
    connection=SimpleNamespace(screen=lambda:SimpleNamespace(width_in_pixels=1920,height_in_pixels=1080),close=lambda:None)
    scope={'recording_process':None,'recording_path':str(tmp_path/'recording.mp4'),'platform_name':platform_name,
           'os':os,'Path':Path,'display':SimpleNamespace(Display=lambda:connection),'jsonify':lambda value:value,
           'recording_command':lambda *args,**kwargs:['ffmpeg','output.mp4'],
           'subprocess':SimpleNamespace(Popen=popen,PIPE=subprocess.PIPE,DEVNULL=subprocess.DEVNULL,
                                        TimeoutExpired=subprocess.TimeoutExpired,CREATE_NO_WINDOW=0x08000000)}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),scope)
    assert scope['start_recording']()['status']=='success'
    assert captured['creationflags']==expected_flags
    assert captured['stdin']==subprocess.PIPE
