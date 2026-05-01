from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': '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', 'ground_truth/variants.PrjPcb': 'eNqllk+PmzAQxe9IfAcuPRJhQ5LNgUME2XbV/CEhm8uqBy9MEiRiR8Zs1W9fkyXaDaT1qL3BKPN7b4ZnKy8xVMWB/7CtHciqEDwkA8+2vhUgmcyOvxYih1AXVmfgq1qda1WFxLZi2LO6VJHg++JQS6aazlTUMoPKtmzrJZGwBwlcv2t281btmo6vz09x2BY28FY0km1Nd8Uiq0/AFdE91+eEqWOYsAOQQZodddW2ppwLddGccfZaQt5Y+tRO77VTdLt/r903tu+YLBhXVWO+fV6yE4SpYjxnMm+2VmWyOF+W9ViXpbsHpmoJziuroCw43HBohzMvFNwyIlEpV0JeZ5A7b+/fz/lZqKNTiRM48TK5Afod4ALyImPlLbMtugfJcnBYqUByptqveiVF4nT+NOYG9s0O5uLQtL4niikhww1pf3NBez0GxTDo3xk+huF3GAmT7PRR2YpS512HNSRfegIBQiAyDDrEMAyDjhCMZ4OPMYZh8PGAYMQGHxMMw+CDeAjI2mCEdGJM/yXGhGIgN+No4vR6thqE4PqyCTez1PUCj7rE+95X8TEqvsFqgICY0kyGGEh33i5khICY8kzGGAhi89u5Nw7cdPUUkaCv8oBQMUWeTDAQw9Koh4CYMk87mfdRmf/jlekN7lyalGI0DCec+hiI/39GA4SG6UDQIQZimnaEgPQOxJ0sp9uFT3WeiTtfPyajfp7pGKNksvuAgJgOBZ1gIKZ/AB4CskYsbrlYpfoO2FLfnc4i2/oNMail/Q=='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('base.PrjPcb', 'C:\\Users\\Administrator\\Desktop\\base.PrjPcb'), ('variants.json', 'C:\\Users\\Administrator\\Desktop\\variants.json')]


def _decode(payload: str) -> bytes:
    return zlib.decompress(base64.b64decode(payload.encode("ascii")))


def _materialize_bundle(root: Path) -> None:
    for rel, payload in BUNDLE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_decode(payload))
    for dirname in ("init_file", "ground_truth", "_internal"):
        (root / dirname).mkdir(parents=True, exist_ok=True)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        dst = root / "init_file" / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _bundle_python_paths(root: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        text = str(path)
        if text not in seen:
            seen.add(text)
            paths.append(text)

    add(root)
    for rel in BUNDLE:
        rel_path = Path(rel)
        if rel_path.suffix == ".py" and rel_path.parent != Path("."):
            add(root / rel_path.parent)
    return paths



def _load_module(root: Path):
    spec = importlib.util.spec_from_file_location("eval_inner", root / "eval_inner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load eval_inner.py")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["eval_inner"] = module
    added_paths = _bundle_python_paths(root)
    for path in reversed(added_paths):
        sys.path.insert(0, path)
    try:
        spec.loader.exec_module(module)
    finally:
        for path in added_paths:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
    return module
def _is_pass(result) -> bool:
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "pass" in result:
            return bool(result["pass"])
        if "passed" in result:
            return bool(result["passed"])
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
        except Exception:
            pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    return spec


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
