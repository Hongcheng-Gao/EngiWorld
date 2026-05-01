from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqlVm1v2zYQ/q5fcWO/SECqOi8DNgMekCZeETTtisQpBgQFy0hnW4hMaSSVxgj833dHSpa0ZEOLGUgkkcd7eZ57oRBi/qDKRrnKwJL+nLL3r09+hfjdzQXcoc7WG2Xup6CsLVYazi7fg9I5nJ8uTsFVkJW0AcdJGkU3Vq1wGgH96q1bVxqQNKf1Fq5v3n64uL6++OOjPL+4iqLxN2wa6yCrtFOFhq/BEOapzdZfISaXviptv6EJC7YCt8bI4BINeYewMlWjc+lM49ZvwGaVQQvfCnKgcUAialPoFft3tsbs3gYHD1M4x7J4QKPuSoRlQf/wsbDOpn7/KIVPyljSpCz8+eEyrB6nPn7Q6KAmM6idByNTxhQk68GYiWMRxE/SANN3iv+cwuezswN49/H8AK7m1/MFn7RgXVGWnYKD9lO57viEjgshoqWpNiDlsnGNQSmh2NSVYYO6csoVlbZR1K7Zre1eHzdlis4gpvMSN2RgQe8c9HwRNNbKrcvirlP3iT6jiBSkvJEW2qJx8YTdMjFvxuQCoSllkpLHVfmAcUKyRIRrH/AGRFZtNpUWSRKMELO4UZ0NT9QV2qakcDk7wzvAK9DVX2oK85PJURQtTq/fy4tzmIFAtSqRslZE5/PLi8/zq9O3l3PeGCaTiKIoxyVIRlXebSWlBsamqhxpXHTxJ/D6N8iLzN1SRAeDjS8hcwwSvhqedLpCFwvWIZIpaF88GiiDWWNaODS0i04kUCxhJA2FpUAcfKw07lqnMBQhxra52xTkdaVlXpgp4+pd6nEIfpAcBegRHx8Z4B4cJrH+cMz1LYt81qLHxGHtKZsxhaSLSPEHcy4QOsyW3sAAWL/LQVEMXigNpRMnwTX+KeKrOyr6+hV7ATpPMi+cHJomif06lhbHUiZFYyqObymeBv7tvGdLbgvMxxN5sRPjk4FEEwI1aeZbQ6rqGnUeD/Iv3h9j6mYi75uGDK6Lg71ITdmGhKxpsF/ExxozR8sDB/tdlblGlbOAIpsIWx0FDh8ZxrBtUFGbo5WY+l6VU1ebicYtX/8iDsADQc3AYF2qjHIsHDfbHjFOS06FRcolR1yTgpjVJXsRagayuichDmG0Svq5nAKK+Jhh7WDuH5R13C7wmSHO7ueaf1dE4wuqiUG3rTHGJJW+MKXcTeEJW+J+gKLa922prCTtz9kJnrzATzjox8H89B21D5+vz6gS1b3g5G0j4qzswthz1+a3B4JqnZEYwDPKPd/hZy/0pDYDwkg21D04lWNB84foFjxXxKBoNOlgFb7NBPme1qxkE20L8lOjbUrDRhQiGZH2XaDvgWcGveGd7Lqu9Mbk8QDFAROx94uy6lgkY4E9J61GSoTW7ylL73Zj8ZaZF4TJwlC4K6tXMNeWpiRUdJUwgQMaTWHGmgfM9+MVJmE29zszeNqNlv5RMUxYUOv5oonOfNFM54ef6v/Kmz/2/2nb+3rrFX4hJaRq2HhZ808E/ESMG+o4pL5Uf6D6vMmQzQ3dHZVeYf68CAeGXqjEJ4/alP1roeveA37+a/esMvdxj3toX28Rhd41F594Um7oyillCwNtl6hjvtxQJj0kjNHRdIBroYmJxl9z//uKS76GiUqqrMupN/S08hqNDhcftfM5XG5mgytA68Dt4Zck6i0HwdQ2G7qRb+O2z+zVTXzLaWX4FswhHqaTkCGHSfQ3biKNOQ==', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('assign.sch', '/home/user/Desktop/assign.sch')]


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
