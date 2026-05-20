from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqtV21v2zYQ/q5fcWM/RFpj1c5LhxhxgNTphmxoGzTrp8QTaOkca6EojaTTGEX/+46krJfYQZFhBhKZ1L0+9/B4Zoy9f+BixU2pYEF/huv7wegEwt++XMIcZbosuLofw/T8A+BjVSoD5QIur6aDi8Hh8dvzKGaMBQtVFpAki5VZKUwSyAsnyaUsDTd5KXUQ1HsKN9/0WnvFipulyOcbrStaBgG9je2LOJcalQmH+6CNCu3LkDzlgvxEsUJdigcMI5JVKE39gDfA0rIoSsmiyDvR6RILvvExXWJ6/xn1Sph9sAj47wCvQJb/8DG8PxoeBMGf59d/JJcXMAGG/E4gIcOCIMhwAehhw1Cv5kWuNSWZZLka2ygjGJx1rI4DoA/JkR0Xf1+lk4UTVCTWKoe2IkmeTepYLAxYOQAmFhCyRSk6xZTLLM8opkTyAjWZuWHzkqsszquU7QPjUn9F5VYzp2G4ukNDgh9LiW7HcsBqQy6f2vNp2E9FGjadN0602c4XUMX4mGujw6iV7jmqettzhfw+qHVrmVy7aFp9FaNSpUVlwTIU+QMqPhdIhTIU7kpmNtZvFM93CImimBrMgCxYon57ksP3iLV2kdgqQXnwjFq3Lg0+2mB9RFQeniV2qy4QPqZYGXjvHlRE4Bp68aaWXTrmVYUyCztcC20QE2YN2hSoJhXXGrPJr1xo3O9h89xnk2JrxoVLtnhqVlw4VmAURc8kKnLpuGGVYl2J3LidOjdJnMSiMmvLHiEdH+hBCHs9qpOQMbnIqzCaeYuv/HGC0diqD5x68CMkmug8JI1f1qJQYzMvSxE276P2fYsENyCQa+PKbgPtWKlRESi3jGwOziaBA3t6uTIavuZmCRymA9tFqKH4s5ErbWnRmLkZziwgLWZIVQTGXpq8d5pYp8k0qV1uA+H8x17YyoZsynbC4QNtauEQoWZ+R63UZ7Y33dtGyGndjA+Hs93oHI4hLaXh1goHdgXw+6d3EMcxowAVJWJQOVdOa8l1UiV/l7bpcbkOFcYFN+kyVOyvq1v9mnRv50RaIaMOydoKvRTDxt82bs2rH1Jnr01q7xkesfKe2aK3+fmiu4Yu79hu7I7G0HN0OPqFDqC212Faqsx3IFonfq23Tl/LMfLdxZIseRRn/wUx0t64fObgdaPaSbazCYxsPgMvtPvk7bDyFKLjMSBPlw4aL2kxBrNEKHKZF6uC6CdWhQSNptYEYDZ/eA3h6WR0NEiXnK4vNFG9c+B3FC4y1HYzU7kQZCdDWvA0Ra3dytkruCDAC7o9CP1Zcx36AnQzGHevPJueJfEpHB73L73G3qYYQt6M3w5nUU/KnqlcrnrXqL3aqMgauXJVvrjVP99mr+n/OT18vV/i6wWs6DAi+YpCJN7sNjtCG2Tjdic1kK7qdYcbrqAXp64IZ+enHv+zbcaEm0PWc+EPWrOkTjV7hkpviUoyq3sdOzk5YXS9c5qYlL8B6RQmdKDmgsv7Xj8fjGabu+1/aew2Ct/WbRDbED6JZOKD3YmlFX3a0mlU2iOFHb28Z7gPUjsNBJRi4uYiGtmt8yQpqLsnCRsHHXLbSZwGoYcIfprQFdkmoXJpQrbS/A7HUK3NkkYhOxbH1Rquv7z7cHl9ffnpY3Jx+ZkY6wdWMqVNRvNcewbsHg2NJjyoueon8Ulnwq4DuBnVdPaevWCsVwX9RFmH9cDTmBv6TulliH1oUxzFQ1/LURT8C8we5Qs=', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.brd', '/home/user/Desktop/board.brd')]


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
