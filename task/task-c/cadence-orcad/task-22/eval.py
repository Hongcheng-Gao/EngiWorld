from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqVVE1vnDAQvfMrXF+Kmyxpox4qFCKt1FQ5RlVOXbaOgwfiFoxlm2jV1f73jg3sElWJ1D3AzsybN59MbfuOcF4PfrDAOVGd6a0nQuveC6967ZJk0v1yvZ7/W0jq4GmEf2rV4+x2h2KS3N58vyFFFFKkVi0Ss8yC69tnSFlmhAXtk6/r+xsekRayqu8MAlNLN+vVj+1GrP5s95cH8kIq3Vkp95/OUV/KUubHB4r7zwfKkrv1/e0rnIEjv9j8vLp+X9LSfdieIT5JJNSE6952olV/IPWw8zlx3jKyug7vPCH4C2oknVLO3PCY0qsgXdPzaGRL2JRFhLWie5SCdPnYjy5rbD+Y9CNjmRYdLL0t4BB0VGC3TCsqSGlpS40xKD5Zhvkok85pw7NoeT94M3iXjm8ulT2lL1Xlx/xH6zyUE3YxlogT2iFoQl8Quls5qMIaZH7naYQ0gSaOGO2hGC25t4N/oq84YClhNwqyp0Y4R3PyTbQOK6enPGhMekqMHaKfqgkuYUgpg51yWCMbizmRbqgFgWtJt0hfU9gZDA5yLqBTzind5GQfSEK7D3TBELs9Es0BF5sQXJAdi8N5pKCrXiJXQQdfr77gRMDa3rqCqgZ9gDJG3hVL/2Ogxv8XT/R7u1Ja2d65udNzg6Wqa7COxA/z2Ip12wJOKSgQ9Fb5c6A4pBDm3g7wwlI9QfV7tG3owxR29UyOQ384dl54BDsiag82XokLKTyQuT3xtNBt8m8meG5wDDwMC89RgcVy3gmlOadjT+YLZRu8Iw6ScW8N5jSrsrVthg5PzF2Q7LzaJhNScjHZ0uX2TQjbhO1HYKQJUDc5G6vQJVzATA6dcemLby8As8VHdU6UlhijuMTxahcuq3CVUkVcfMaSv5u3xj8=', 'ground_truth/routing.json': 'eNqr5uVSUFBKKVCyUqgGMYGcnNS89JKM+NzMHKCgmYGBqZ6BDlSqLDMxPjm/NK8EKGOIJFgM5EdDuAowc8ByFUAJY1MDmAFgsUqgmJGJKbJQTmJlalF8WlF+LlBOycdQCVOyJB8sZawEk6mFMGJBVK0OxBt5eLxhrmdKfW+Y0sIbBRmJxanxKZlpaVDXG0GdrpSZW5CakpiXDJXNzwBZZGmoZ8DLVQsAgRRjQg==', 'ground_truth/x-section.txt': 'eNq9VF1vmzAUfUfiP/ix1VzApqxK3hiQLlL4EJBVe4oc8BKrxEbG2dR/30u2VtEU9lBFs2Vk+557j8+1L5FWw4Aq3hihJCp5r7SxrXjudqph3S+ln91E7gRMutZ1zKHfKN2wdtNrteXk3v1axZtF8RhufgjJOmerW9tKIVLYa0QfEJnNiTf3KaIe/WxbEJkPYidRdE5rW9Vx23QMdjJ24Lh+6TlOmeFasA7Xe9E8Sw7GmzS9xbXq0KfT9w5HSrZHCPFTmBd0c9grtznc4ljwDgJr0SAADIZJg1cjXc3kjsMi4zsGThyF2owKcbUHlxY/idbsf7Os5XHgLSqERAVrUXXsew1HgMO+mb4J9rfJtnC1LhdhlOBwWWJoHiYwxga2eJmskqgulxFelHf32HO80Tr208IP/iDrvMBRnsXrqM5LmBVFUo6AIDiBg1kw88DHCd69PId4sHWZhQRvLGceI/YxiwkuVmGWnJH4Exzf+TAlg04RLMlFHb7/IR2TNEX+dEHHB4SQ6UTRqxBMZ4r+r0zRa9z45JP6ktd1nl7z9U7UyL8qDSpIGdah9z/HHBHngVKUprb1CrrZOGQ='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('HSD_FPGA_final.brd', '/home/user/Desktop/HSD_FPGA_final.brd'), ('README.md', '/home/user/Desktop/README.md')]


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
    print("True" if _run() else "False")
