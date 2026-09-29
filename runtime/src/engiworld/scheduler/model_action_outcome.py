"""Attribute Alt+F4 session loss using worker instrumentation and guest events.

An Alt+F4 string, a failed screenshot, or a disconnected port is not proof.
The guest probe runs inside the actual GUI action immediately before the key;
the independent Cloud Assistant reads session events if the action server dies.
"""
from __future__ import annotations

import ast
import hashlib
import json
import time
from pathlib import Path
from typing import Any

ALT_F4_CATEGORY = "model_action_alt_f4"
ALT_F4_REASON = "Model action error: Alt+F4 closed the environment."
POLICY_VERSION = "alt-f4-evidence-v1-20260923"
DESKTOP_CLASSES = {"progman", "workerw"}
SHUTDOWN_TITLES = {"shut down windows", "\u5173\u95ed windows", "\u5173\u95edwindows"}


def _gui_calls(tree: ast.AST) -> dict[str, str]:
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == "pyautogui":
                    aliases[item.asname or item.name] = "module"
        elif isinstance(node, ast.ImportFrom) and node.module == "pyautogui":
            for item in node.names:
                aliases[item.asname or item.name] = item.name
    return aliases


def _event_for_call(node: ast.Call, aliases: dict[str, str]) -> str | None:
    fn = node.func
    name = None
    if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
        if aliases.get(fn.value.id) == "module":
            name = fn.attr
    elif isinstance(fn, ast.Name):
        name = aliases.get(fn.id)
    args = [a.value.lower() for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    if name == "hotkey" and len(args) == len(node.args) and set(args) == {"alt", "f4"}:
        return "alt_f4"
    if name == "press" and args and args[0] in {"enter", "return"}:
        return "confirm_enter"
    return None


def instrument_action(code: str, guest_path: str, prefix: str) -> tuple[str, bool]:
    """Keep original arguments/order; add a read-only foreground probe at key calls."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, False
    aliases = _gui_calls(tree)
    found = any(isinstance(n, ast.Call) and _event_for_call(n, aliases) == "alt_f4" for n in ast.walk(tree))
    events = any(isinstance(n, ast.Call) and _event_for_call(n, aliases) for n in ast.walk(tree))
    if not events:
        return code, False
    helper = f'''def {prefix}(event, function, *args, **kwargs):
    try:
        import ctypes as c, json as j, os as o, time as t, getpass as g
        u=c.windll.user32
        u.GetForegroundWindow.restype=c.c_void_p
        u.GetClassNameW.argtypes=[c.c_void_p,c.c_wchar_p,c.c_int]
        u.GetWindowTextW.argtypes=[c.c_void_p,c.c_wchar_p,c.c_int]
        h=u.GetForegroundWindow(); cl=c.create_unicode_buffer(256); title=c.create_unicode_buffer(1024)
        u.GetClassNameW(h,cl,256); u.GetWindowTextW(h,title,1024)
        row={{'event':event,'epoch':t.time(),'user':g.getuser(),'foreground_class':cl.value,'foreground_title':title.value}}
        p={guest_path!r}; o.makedirs(o.path.dirname(p),exist_ok=True)
        with open(p,'a',encoding='utf8') as f: f.write(j.dumps(row,ensure_ascii=False)+'\\n'); f.flush()
    except Exception:
        pass
    return function(*args, **kwargs)
'''
    class Instrument(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            event = _event_for_call(node, aliases)
            if not event:
                return node
            return ast.copy_location(ast.Call(func=ast.Name(id=prefix,ctx=ast.Load()),args=[ast.Constant(event),node.func,*node.args],keywords=node.keywords),node)
    tree = Instrument().visit(tree)
    # Future imports must remain at the beginning of the module.
    index = 0
    while index < len(tree.body) and (isinstance(tree.body[index],ast.Expr) and isinstance(tree.body[index].value,ast.Constant) or isinstance(tree.body[index],ast.ImportFrom) and tree.body[index].module=='__future__'):
        index += 1
    tree.body[index:index] = ast.parse(helper).body
    return ast.unparse(ast.fix_missing_locations(tree)), found


def confirm_session_loss(evidence: dict[str, Any]) -> dict[str, Any] | None:
    """A desktop Alt+F4 or its Enter confirmation must precede the same user's event."""
    probes = evidence.get("probes") or []
    events = evidence.get("events") or []
    for event in events:
        if event.get("id") not in {4647, 1074}:
            continue
        # 1074 includes process/account fields: only interactive Explorer requests.
        if event.get("id") == 1074 and "explorer.exe" not in str(event.get("process", "")).lower():
            continue
        for probe in probes:
            try:
                delta = float(event["epoch"]) - float(probe["epoch"])
            except (KeyError, ValueError, TypeError):
                continue
            user = str(probe.get("user", "")).lower()
            event_user = str(event.get("user", "")).lower().rsplit("\\", 1)[-1]
            if not user or user != event_user or not 0 <= delta <= 5:
                continue
            cls = str(probe.get("foreground_class", "")).lower()
            title = str(probe.get("foreground_title", "")).strip().lower()
            direct = probe.get("event") == "alt_f4" and cls in DESKTOP_CLASSES
            confirmation = probe.get("event") == "confirm_enter" and cls == "#32770" and title in SHUTDOWN_TITLES
            if confirmation:
                confirmation = any(p.get("event") == "alt_f4" and p.get("user", "").lower() == user and p.get("foreground_class", "").lower() in DESKTOP_CLASSES and 0 <= float(probe["epoch"])-float(p.get("epoch",0)) <= 180 for p in probes)
            if direct or confirmation:
                return {"probe": probe, "windows_event": event, "basis": "actual_gui_action_and_original_vm_session_event"}
    return None


def collect_guest_evidence(instance, guest_path: str, start_epoch: float) -> dict[str, Any]:
    from engiworld.scheduler.volcengine_ecs import VolcengineEcsClient, VolcengineLaunchConfig
    # Task metadata and model output are never interpolated into PowerShell.
    if not guest_path.startswith("C:\\ProgramData\\ArenaActionEvidence\\") or not guest_path.endswith(".jsonl"):
        raise ValueError("unexpected action evidence path")
    script = r'''$ErrorActionPreference='Stop'
$start=[DateTimeOffset]::FromUnixTimeSeconds(__START__).UtcDateTime
$probes=@(); if(Test-Path -LiteralPath '__PATH__'){ $probes=@(Get-Content -LiteralPath '__PATH__' | ForEach-Object { $_ | ConvertFrom-Json }) }
$events=@()
foreach($spec in @(@('Security',4647),@('System',1074))){
  $items=Get-WinEvent -FilterHashtable @{LogName=$spec[0];Id=$spec[1];StartTime=$start} -ErrorAction SilentlyContinue
  foreach($ev in $items){
    $xml=[xml]$ev.ToXml();$d=@{};foreach($v in $xml.Event.EventData.Data){$d[$v.Name]=[string]$v.'#text'}
    $user=if($ev.Id -eq 4647){$d['SubjectUserName']}else{$d['param7']}
    $events+=@{id=[int]$ev.Id;epoch=([DateTimeOffset]$ev.TimeCreated).ToUnixTimeMilliseconds()/1000.0;user=$user;process=$d['param1'];record_id=$ev.RecordId}
  }
}
@{probes=@($probes);events=@($events)} | ConvertTo-Json -Depth 8 -Compress
'''.replace('__START__',str(int(start_epoch)-2)).replace('__PATH__',guest_path)
    client = VolcengineEcsClient(VolcengineLaunchConfig.from_env())
    invocation, results = client.run_cloud_assistant_command([instance.instance_id],script=script,command_type="PowerShell",invocation_name="arena-alt-f4-evidence",timeout_seconds=30)
    if len(results)!=1 or results[0].instance_id!=instance.instance_id or results[0].exit_code!=0:
        raise RuntimeError("guest evidence command did not complete successfully")
    result=json.loads(results[0].output.lstrip('\ufeff'))
    if not isinstance(result,dict):
        raise ValueError("unexpected guest evidence shape")
    result["invocation_id"]=invocation
    return result


class ModelActionAudit:
    def __init__(self, task, instance, run_id: str, result_dir: Path):
        self.task,self.instance,self.run_id,self.result_dir=task,instance,run_id,result_dir
        self.attempt=int(task.metadata.get('attempt',1));self.started=time.time();self.saw_alt=False
        key=hashlib.sha256(f'{run_id}|{task.task_id}|{self.attempt}|{instance.instance_id}'.encode()).hexdigest()
        self.guest_path='C:\\ProgramData\\ArenaActionEvidence\\'+key+'.jsonl';self.prefix='_arena_key_audit_'+key[:12]

    def attach(self, env):
        if str(self.instance.os_type).lower()!='windows':
            return
        original=env.step
        def step(action,*args,**kwargs):
            if isinstance(action,tuple) and len(action)==2 and action[0] in {'pyautogui','python'} and isinstance(action[1],str):
                code,found=instrument_action(action[1],self.guest_path,self.prefix)
                self.saw_alt |= found
                action=(action[0],code)
            return original(action,*args,**kwargs)
        env.step=step

    def resolve(self, error: str, category: str | None, collector=None) -> dict[str, Any] | None:
        if not self.saw_alt or category not in {'infra','model_environment'} or str(self.instance.os_type).lower()!='windows':
            return None
        if not any(s in error.lower() for s in ['connection refused','connection reset','get_screenshot','sandboxunavailable']):
            return None
        audit={'policy_version':POLICY_VERSION,'run_id':self.run_id,'task_id':self.task.task_id,'attempt':self.attempt,'instance_id':self.instance.instance_id,'guest_probe_file':self.guest_path,'native_evaluator_executed':False}
        decision=None
        try:
            evidence=(collector or collect_guest_evidence)(self.instance,self.guest_path,self.started)
            audit['guest_evidence']=evidence;decision=confirm_session_loss(evidence)
        except Exception as exc:
            audit['collection_error']=f'{type(exc).__name__}: guest causal evidence unavailable'
        if decision:
            audit.update({'confirmed':True,'status':'completed','score':0.0,'failure_reason':ALT_F4_REASON,'error_category':ALT_F4_CATEGORY,'decision':decision})
        else:
            audit.update({'confirmed':False,'status':'needs_causal_review','reason':'Alt+F4 alone or service loss alone does not establish model responsibility'})
        self.result_dir.mkdir(parents=True,exist_ok=True)
        (self.result_dir/'model_action_outcome.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
        if decision:
            # Separate adjudication from the native evaluator; never fabricate evaluation.json.
            (self.result_dir/'result.txt').write_text('0.0\n',encoding='utf8')
            return audit
        return None
