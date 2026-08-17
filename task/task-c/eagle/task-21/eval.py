from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqdVm1v2zYQ/q5fceO+SJ2tOGk3dAZUoE2cLmi7DUmzD0sDlpHOsVCJ0kgqiRfkv+9I6jV1g20BHEnkvTx39/COjLHVjSgaYSoFa/oZob/MD55D+Pb8BK5QpptSqC9LKPIrJdQWDiupc21og943mH4BhXWlTBQHwbkW17gMgP7qrdlUEpBsx/UWzs7ffDg5Ozv57Vd+dHIaBNNvKBttIK2kEbmEz+ngIi6zzxASrM9C6ltU7ltXYDYYKFyjIiGEa1U1MuNGNWazBzqtFGq4zQlBYwieFGUury1AB1h7hPsxHGGR36ASVwXCOqd/eEd+dez2D2I4tmu5BlnJOZa12UJdEEKDd2bvA2Ulq24lhK9gf7GAq61BPYMM0yoj70LD+cfj+cvIG3sew6lLE5QoTU4BggBW5loTMqhFxmAP2JXI+ncKCNe5xHaFPjA13tiLncaypi7yVBiEOpdThR+f9m7Fpx4fG/hphwFpNdKK8tdpkA16UrZcLSVp4wg5YyxYq6oEzteNaRRyDnnpjApJOsLZDYJ2TWH3prfaK9bCbIiGndbv9BkEtBvbjTiXGpUJFzPQRoV2MyRPVEHOo5gIURU3GEYkS4Qw7cNCTquyrCSLIu9EpxssRefDEeYUdVOYGdiD4t8Bvqcw/xJLWL1YHATBx9dn7/jJESTAUFwXSAeIBUer9yd/rE5fv3m/shtTVrMgIIHj1eFHfvjL6vDdGYlcuFyHXWE4FZ777PGaAiC8bOZE4EJ1Qp/0D5YfM1CWPaOvvpqjNVnRh27STbt2Gc1alz15OFXw2057MWuASj4Y6DE/pT7CTMpfoWzXJignTnq+Pe2mFxsZpSd9Xbye/ynmf/PF/OfLZ5/0M6IdrQ5kbW04EH7H2WlhTWUtrEuqIsFwbY5aKIa6uXJBVgQvV0tLxQjmr0bU8c2H5KjgjqRTlRFVnaAisUE5tN2Z51nSEs5yHWvH8sSynmwRj51iZnsbKVtPezDiotvN1+6YOqHYd70wWrbRAwiieKfK+s7L+n1SJ5EdimPPJNGvY6FxKqViVKqy4a3Z/QjegwO2tg0dqJncE4gHNtVE6h4SlI9Txalr6rGoa5RZODqxYa9GEwATlg3tnnvofcFpYAmtkRKrGhwW8a52xU5GAIddkZpGFIlPonXht7oKGLUdQrYzg2L1sgrpZNuVkLpBldGRSFhj1vOXRDSXFZ0wmqqFSJF5GuBdirWBlXsQVex8GSX0XyVhSITrihaETcUoB6M8HAuq2HSnTwbrVP2Ic7E9stKmhkprtjWGGMWcW9+cPyzhHh9G4lEU7K4sTV3up24CBcrQuongVWLH7X8tvb+j8N7k14Xvt3ZUn3mnfsZDtX4c8RBtj/PBC7MpJYrqloKxAjG9omoPub13uVBcjmZ20BlUNGTpAEyGxFDxUhjSyOwxk9tQYaxRqHQT1jPrJHIma6vf2Yr+J1lGuHbxpMXxDaasWSXRJuy+g/GwmyjM2fHHntn20sVnGwdQ7/ULU9oEU84EpNaxDBKauJyXdFvjnC27nmfLYy8MQl3fRPBdAgdDRmtFNzuaMe4O+/T9lY6pb7lkSpuMjuyQXbtGzcWEB20D9xeGZDQjWgAX+5dexHv2grFuSrpwb8P2WPTmFhZ/J2NvuDbE/XjhM7QfBf8ATgOdEg==', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('test.lbr', '/home/user/Desktop/test.lbr')]
REQUIRED_OUTPUTS = ('consistency.md',)


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
    if not all((DESKTOP / rel).is_file() for rel in REQUIRED_OUTPUTS):
        return False
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
