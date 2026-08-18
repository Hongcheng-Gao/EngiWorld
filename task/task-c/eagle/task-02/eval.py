from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqVWG1v2zYQ/q5fwXEfIm2JkngbMBh1irXNhmBbV/RlGJBkAm3RMRHqZSTlWsvy33d3pCTLdlrUaCOJfO5473cS5/xyLXQjXGXYEv47Ye9PziYs/uXDFZvLcrEqhLmfMtOUzCp9n4kmVy5tdM1EmTMr1pIZWVfGJSnnPFqaqmBZtmxcY2SWMVXgHmDLygmnqtJGUVgzsruzre1uN4VOpTNSppdaFrJ07+GeCcsu33vetXArreYd4zfwGEXAIMWNVJVWGhefHTPrTIybMQijNIiSpEbaSq9lnADWAOtwYaeML6qiqEqeJP4Qu1jJQnRnvFzJxf1baRvtjhmay98z9jUrq3/ElF1+fzaJovc/vfs1u3rFZoxLcaclmJH7xVdXb2H1M9JEV6+v3mcv3iKDngpEU6VyRMTxyZt/bnIeRb9dvb7M3l4C3sgUNKgBFEcMfubIyY2b8fj5m2foXnlx/Te//SbhN/bbo4DYzHB3c3Hy/Cb/Nn4+vUnhmjxPtiAtQdpPQaz6VxIKbz4F1KKVhpB0d+HeaLGQ/83pkhxFSRRFuVyyTG5quXAyz9aq0j5k4oSdXDCtrLvO1cLdToknhNtLULpxkrmVZD2cWekYuRGX7UrVtcxZbzgKU6RXS3CfY53ZU7mBA+Asz52klhDFJbu+9TpUgJ5BIKLDrIw7wiS9g4iFzTghHApiARjIMKtqLVTJ4B/C0qUqc6F1zNPT03klTH5K+3zrZEpFJKCdgQLduo3DnzPteAF/ZGQQQpUudihgzGmJHzN+hnG+S4D+A/xSV6KnwLUnCTa76M2T0HYX2h6Eys1C1o79iQF7aUxl9tVaVKVTZSNHG+BIry7YK56cH7PJJPHVCXV6xs7SH/c5kZdSAbFR5vHD3jYFmLfY1HMHiTdwv4FrC9cWrmSfKR1zfJgDJR9AQHF0HQO3cp6kUJxUHSf7RI/eIiHwSMaQF9KXaRnbZl4oayHQs1yZKRY6So+hMHllAdcVnTHJVunxh2FQ98QxdoBM5bNQzrCSypoK0AxrKvACtxHhAmyscpApK0UhKeT5Vo9wEKpgJFHaj9LQk08IJwwEAaBfV6XsUwRZoAN3mA6Oq4ECdTolaLTl/PpA6o4OqkfLcyPFfVcBAkZZkmYr9VOJEYiBy3Op1VoaMdeSKsayaiC4QNYHkOeRxV3FYsCBVUv2sKPDY8J3S4rxFhylLgXILEgEPhJ5hkvBSyE5LumCVQ564kjeBXapPqK3elaMQsw4MkQVwCe1sFbms5+Ftk8E7u6vU3FgQ+ICL7FwjdAUGjLZSuixol/7JsrOpwwjCe1dVuWJLGrXRp+Tv+fpFQHCjAj5IHvQaF5VOkbBugzbSrFBBeGYlsI68pdWpdxiFNRZ8gctS2KVPLJ566QNoC74O40mU0hNaVrSZ65FeU8sWSEcaGSpB3347c2RZVXjoFlhsMMe8UAgpY0uKQc09Qgvf62Vo31ofljgyk4ln0Rzke8RenahrYXhILVSmMUq1mUg/AJDQ8fJiGfmZQbj7Zs8xsNAmoOWlmKxGpvDDyY3/K8bzjazNGUt/qEpAq5+SEjTo32PxMEleNQjGRt6AcqlyjuvOUfV0S4Swprx6p4nh1323ZSVTTGHhgHJOowN3nydoF4J2hl19cPzyZeatqfNFlBMXBZOPWBe1JkkS9hsxvCJJDkY2cPunvkGNodt8v2UAokc1tezXspjDGNDaSu8hTqrR15WmIfy8cizFZJDlSoAsx+Y27Uco6kYl/G9nu+PO9y7+45bpHemauo4LOz0WmrlfiTpgRue7KLafVS7jwpjwA6QVvew3UgxOUdte7BfJhdzPxlzH8aTycAgDAfUysH8I3Ov0drk+8F4K4X9RJRtPJKhvg42ucXj1v3TCITjk5jbGMAbAJ4gDm4SGqfOzp/Cth22/TyWDBTg/v5JCkB7C3Uih6cRkAZtmpkpPvq9vfgCu4wjLFi0i6jBJF+c15g/Q2HI/Jvxk2UznHsolZfc05JWD9fr6yMS6eh2x9u3jwdKJda+PplCtFA0LXl4nLKHcPf4VJX8YQr9UbdhtJ6cn04m1Jos+6jcikr2M5isWacjA5XYEkcKVldWORiZrLffEke363rXQTS69WFwMcM5/fbLh4GMzsz6M5+w9bI+PAtoPWjg1VvhN43h1eEz9gXlvGnrHTsOA1AE0IxGwSyjDM+g3qsyy/i0G0OxPONHDJj91gn7agZjxaCFwZc43lhxJ6esbt0KmhW+DqR1y959ePH71bt3V3+8xu8FMI/5QR1YWZfDCDsEP67BnOziSfeOQR8xZltvFkGA6/MQ+P5kD0xtUxTCtHGY8Xp2Zyh/h1lU0CVAxfP0zJvlPIn+B9BdUys=', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('audit.brd', '/home/user/Desktop/audit.brd'), ('silk_audit.ulp', '/home/user/Desktop/silk_audit.ulp')]
REQUIRED_OUTPUTS = ('silk_audit.txt',)


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
