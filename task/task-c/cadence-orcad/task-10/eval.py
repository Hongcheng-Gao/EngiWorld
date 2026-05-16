from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqNV82O2zYQvuspJrqsBHiVpKfCWC8QNBu0RZAGSXoyFjQtUTKzsqSS1O4aCwN9iD5hn6QzpCjR8Q/qgy2R8//zzTiOY/HI66zbQdkqMFw/XL99A//+/Q9spFBc5ZsdiGejeG5k24Bp4fevf3zKoujbRsC736BTbdHnQsOq7U3XG1ZI9Xpkzb7rtllBIXSu5Fo2FRhkmyS3ZbSSjTSslLV4/eHPjx/fvX+fvf/6aZUB3KFhPbdqpQYO2qg+N73itbUB8nbbcSVRQ8QrLhttYFWptm8KhpRmc2QGedW08AvvUIoA2Ty29aPYisagP3fPnciNKJxsveGdmEcR4OfFfgPEqm1NPIf4hh5A5xuxRfNyaPhW3MYzTzZeaCT2zHh+4+jCMzzteCVYjlaT6BvZmNtZeG1aw2uGfhp98l6JUijR5KJg5C5b123+QKTL+AYNYYNtkGXZ/ci3n0Tg+fC8j9y3zezqtNwV1BLDjOloVSHUtRaNlkY+Cmibegd9hwUSbfvaSC0MiL96iTkkKXN4EkPCBHANulUUa5KmsyiO46hU7RYYK3vKDWMgtx3SAG8ajAAVgY6i4Yyy6Z/1TjvWjptNLdee7zO+RtGvd1/uYGFfEmaLjLE0U0JT4pM0I3MaE0VRIUpgdcuLhOTMLUc6txGRJRaNsfIz8UwGJ8MNfZRAexv41DbCnhm1O7okezMSrq101M+xRLGrEgxNW2BbLOLelNc/x2lqecVzLjoDd/aH6h8jJo7EvsSMCaVaxRjmu4xJDZqptICSyxrDiKUm9vHe+zfEP+GNnkFlBi8w+F8mJ8hdLF4sYaQRNcriQ/t2Ns9oO6nBXkSzM0pcECOpqQs55tvpKGRujmNVxnj5JBSVEXFx13Lt+js24BwqPHoxu87KSDNmS5ix/agJj7NKmMT1YwqvFuhMeHJC4xXdXMFWauvcoMVLcrfpK7WfwRNv8GYQOF3EDgs401hPowVBq7vMVfbem3N0fSJO7GycfJg2nOIEV5O0K8vhAoIuaQLWBWDLJag/hWv7iJJ9NSF84+9iPB4oKk9BOR/E4BCw9CdiOAEeNXchS0QInXnOxYvr6WR4T/dO0Hhu31IfSJo2lNgh4LKh0GXSiO1Be1GaFhT1JRFPCHYcSKQ8CuQZ869eSNj+airAKZzetgexI6OSEJ9nh3D8gyI0CW2wiUdmW5bk2nhwSH1YnYNB2QsS7ofiDIUFlXkg0xbmGKs1pdgF2zOfmw8pJXp5n47MTwHzqOJ/c5Pva+vx+kz0RxdPi/Q+ryc/14NrIcI6IKONhbl1QyfT2oFlfWsz6UyYLvwECEinGeDautGMoBkpA7bXEB+uEM6gynhaO16QKtw64nNsStjBtEDc7rimEf2BI75iUU0q8RCRNTR0H4XA4e08OYhI/DJ2AB3fo6IyFn6pcRKBJqBv2LnFPysuKKIh2k5a5IODwtx09BxpAMbURpSdi7Z4MAstOKd1EH1ymqDCYsLfaQBejgQyLAPi+0vuVmb0dsj06GxlvK/UAEmIPia0z+N/YN5l++ILeyv0DS0MfI2BS9bYOZstVw+EwbhuWfnpxfQNE3txPP+9WwPF2TTaciUzv6leHN0irBIm0P3yoPdLO46p4CuzdJP0ngBr9gPVNNewJD1+IUcw7+4zRDss9/RH7gCeZxCA8wxO4wzwunb7TSDIlQMtOxeT5B6jE2GOMIh+T4EFppOxLf4hob3MxXjYZVVl1zPXVR3V5XCSvVNVT39EPtOb8qjUZbwoGB/ukhAoBgpV2X2ky6wYItUDM6HeAVDSXRYgi6XqcI0ziV1Qi37b6UTNcOwVqG3xE+5/jaZlnOtcyoVFq2FBxa2bIMgkb2z9uGq3ZZK6pfFtGv0HFUeEgg==', 'ground_truth/hierarchy.json': 'eNqr5uVSUFAqys8vUbJSUHIL9fFxdHFR0gGLFidnpOYmlmQmFwPlqpU8HH3cQJJW1UoFiemp8cn5pXlAXYY6SiX5JYk58QWJRSVAlWY6SkWpaalFqXnJqSnxGZmpRfFJOfnJ2UCp6NhaHbgdBIwxxmMM3Ck6cFZsbS0vFxABADbdQUI='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('FULLADD.DSN', '/home/user/Desktop/FULLADD.DSN'), ('FULLADD.OPJ', '/home/user/Desktop/FULLADD.OPJ')]


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
