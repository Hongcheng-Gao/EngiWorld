from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'eval_inner.py': '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', 'ground_truth/bjt_ref.dat': 'eNrtlU9o03AUx3+bB8ExRBw76KUgyKa0S9JmW6Oha9NNO2zt2trhn4OZy2pZ25Qk67opwxUUD15kGwxkQ+ZED9OB4CF1KIJ/EGUMUXcZDHXgxaMHd5D58ss6dO2h3dip+cE3733f++WX14YPWVvDa9XTtQvhtQyKskSa2LTQybyiuw1dLrTTt7lINdlQotDOYN7ONg7JhXY6NxetJInchXZ6Cw6P1tdYBULOWIwTYywcmuAhkVmyWUtjA3JUZt2cKdgvCEmtEhD7/xmGRFxU8vFxgT1i8vFKNCWYXO0hkyT0CJKQuCSYFCGeFCRe6ZMEs6ydYVJ4udei3Rbs62IRJ8aTMSHNwuC8wocGkgLMACkEWwPV1EA1Inc0gicitOz/xxOoNdGNR2OJ0haN/LzEx0k2zHF6SrHIL4kRj5ttJG2kFQWElE9kKdpCWuClKLyk6A+iEY5esVuAqUPw+1izjUChKPwJFMXQVsZGI65PwoWSp/LlXspNkDZbuM5H1WtXUrtCpR55ciHg8jiDkATrOmCPp1UPLj1weoAeqfdIvUfqPQid+jmduXM68R2duBfMzVGDNrIWZy71a1rwOPwL7xwI3W355hNVkF3r/Totql9q39Nv1Hie994ey76eP8VkHh63a1ozSDNIK4k0qgxJYwadDmbwJSaNX5JVECaL+CGroT/zdKNHwr4BfAC8DfxcdDw7OxNiXpxptj8HbZB2cUdJo4omzVksaUTbVkgbMUjbHmllyFlltd1RWa1izjKptArCXM1dSasjXz/Sq59T2D9b97/B72u/k614e4HZM2m1a9rgjN9RzqxFc+Yq+otGbIWzUYOz7XFG0eUHWjhicYQjjzFotSeGVBAG6xM/pM6uLNJVT65ivwB+Bvxu8Imfk1n+WIQxe832oyADNAO0kkCjy/CLNjF9yDExfQ+D9mp/RgVhsKgDGbV1cYk+zw5jT4LnwJ8D/3R8KktWScyj0GH7DMgAzQCtJNCay/CLpvTUOJSeUQxaB3tDBWGweiEfXv5O3zp7Pc/f//Agu3flGtM/ddCu6S+1rAvN', 'ground_truth/bjt_ref.out': 'eNrtWVFz4jYQfmfKf9iZviTpoUgyss3N8GAb5cZpMJxlmPbRTXx3NBdgwLnez+9KTojJ2c6UlClTIgaM9e2uPq33W5uh3TrDAbR7zp1zbgPn74X1vivgzMyP1XJ2nQEXhBEKJ1zAMF1dfwFOuX1qbCAc/Ay0MMfRbrVbcAZRms++ZeBfJrDKPmWrbI5R8uxuma3S/H6VddZ/ZdkS8nR9S7SLdtLB9AjCOJiECQykCuJwnISjqDA5+1dHEROjQnw/h/xLBvOC9MOeB0GZMBjC7+DW0Ebjz9lcQ9mNjkAW9/k5uUnx4y5L19o+XeWzT+l1vn4H6fwGsu/LxSo3nuvZd5jG8gKWi9k8X5v9T4MAd64/KeiVRbsV+6GnzFTEgInbdusj0+nBM/2OOHzEIDjLzSw3b/QuZslwNJBX5gSicQQnoeoz2WEC/Is+ExSmHh4phfDXiz4lHIJL2XfHeAj61hgSPSmiU82NIB9NQ+CL4Wkih2PodCl0OMUFsSYwnCv0mhIZa2u96kUYDWB6ErFT8JK+hsfxyJcmoowG7dZP7cOrPe1UZG7sxd5QJjJW+yw+XHt7mAtWGj8Y6ItZaXAlp0gbB6vzD5WBCTXDFEMZ9nFhXRk13tFFU3AsJwRpnTdWmTkSXh3cjxuZR41wqMzGapnHshkOmmDUhT64T1njW/suYCCOqPY2wa1a76DJe/gIW1YF/NtDcFbLvDEt0wKuWxtbAKCwaQ1zKC5obVK9xmqBwBQxJ11eXemDgprrlODD7Bi6G8rYSyax7HiDy4lKJLY972oiFTw3gD7oxqlTine3DxDsubUYknUtDSrGU/fZsvA3LYkRLAn5C+Xl6xUq+fjV7A1xWsYfNWJkZFtcdigr48ET7hBhMVNr5XqIm+ND7DfjRXfZNL/neKiCF/gHL/Df4Jy4vPsj/+b4sT9s5h+qp/jUxvicbfNXL/BXL/Bv8v/gDYfedv46bMs/DkbN/Kej5/ln/yNB8+MWtEWbBW3b7kELupJ/WdCOvV9BOzo/vZ0FXcn/TdC7C/ph00cqaIf0bNEoaJcesqBr+JcE3ePuHgWN/F39BODsKOga/m+CfoWgkd0xC1pYzYLuufZBC7qSf1nQPbFHQTvEElpQ9s6CruT/JuhXCFoc9x2a9poE7RJmOwct6Er+G9zC37jWXh+57a7OT3dnQVfyfxP0KwTtHvMd2iZd224UdJeLAxZ0Df+SoJno7fWR23H48/j/QNA1/P8rQW/X4eXIh2AUBVeTgTzQP800RZV4SaiSMFCgJpib+Pd9yhgbyCJPv8Kfiz8gn91lcHK/ns0/g1p8/ZatgJ0iq/4mhfiLDBP3NypDeSQ=', 'ground_truth/bjt_ref_measure.txt': 'eNoLSc0tSC1KLCktSlXQNTHQM1BwSU3n5eIMC3J1s1II0/Az1LRVMNQzNTczd9U2MFBwDFEw1TMAAhCPl4uXKwTZACPcBhgamhI2AKd2ExNTIuw3MsWl39jMiAjrTXHab2RuQYR+C5z2G5pammDXDwDf3lji', 'ground_truth/t_curve.csv': 'eNoLiXfWCcsvLYkP4+XSNTHQMdQzNTczNzAA8ozAPENDUxAPxDYxMQXLGJkCOcZmRmAJU5CMkbkFmGMBkjE0tTQBcQBcbhEk'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('bjt_ref.cir', r'C:\Users\user\Desktop\bjt_ref.cir')]


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
