from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqlV+tu2zYU/q+nOOP+SFiixm43uEYdIG3UIliaZkk6FCgKlpaObcK6laSSGEGAPcSecE+yQ1KyrdgYEMxAYos81+9cxRhLbkXeCFMpmNGfEXp5OHgF4YfPZzDFMl0UQi3H8Mf7i8MR1CJdijmCLCHOpyqKg+CzpoNxAPSpV2ZRlYAkMK5XcP357cez6+uzTxf89OwqCPrPUDTaQFqVRpC07z9m5ciK/A4hWfFdlPoOlT/QFZgFgsIZKjIIg7mqmjLjRjVm8QJ0WinUcCdJeWOIrBSFLOfWtncLTJfaGzeI4RRzeYtKTHOEmaR/eC+10bG7H8ZwKZQmSULDl4/n/vRlDOdyqoRadaZq4hKpyVcwgDctHsee+JUV4QFaiA3dCN7oIjsm8LJW16+WMAMy1KpT6PzTRpHZGtiA0TO5OF8AGzEISZQAjSbyzL9ttKRCKWlFGMhREJxVifDmTio8hk9XZF6Vr+ZVeUznkIsVKhgOnAz6hOYyFymplflSpwqxjOCfv/6GWlW36DSuL4BwzSWJlhoyJe7KOGCMBTNVFcD5rDGNQs5BFnWlDIiyrIwwsip1ELRneqW7n/dFHqMhsXGSY4GluaHfFvPkxkushVnkctqJu6THICABsb2IKQCoTHh0YPEK7WVIJlAwOY9iyoMqv8UwIlrKA9N+wQtgaVUUVcmiyCvR6QIL0elweXKFusnNAdh68L8Bfoay+iHGkLw6GgbBzcn17/zsFCbAUMxzpDphwWlyfvZncnXy9jyxF10esyD5cpm8u0lO+eXJKb84+Zhc0/2DtVpGrtSkLSMlyjmGgwN4HT0GQZDhzNUPFSSGupkWUmtCkmdSja3HERweb1noU5voSLTDos+yhYgjVES2YQ5trXOZTVq/LKRYOzAn1kySRXA5xsxWDjFbTS9gy2V3K2cEk/FEsa+pMBp3iQaCkOxY2aaw2ZqA+IlmD+e2aqJYn2OusU+lYlSqsv7N2MOWfY/OspntFxbtB7LikfU5kdKX4uAdVXHqekYs6hrLLNzKjHDNZut2wrJNN+HedHawJqmF1kjIqgY3h3hfY2roeMvAzS01i0bkE4+iVeGvuhAYvLcw+muFgvofnYTUEKuM+saENWZ2OGIH4IDQE6awtgXOfOiNWm0QU1VlZSU3sS0G33hCKy5ak1CZ8mpJRNaF3inJt4nuUcT7FGsDifuirLOFjDuKLqgv7Up+LyiMe0RTBM2qxhCjmHMLBOePY3jANnDPCFHtGjoXmpP03eh4S/bExzO6OZGcfKDCdvm6EypWLZlN3tYjm5WdG+vYtfntgKD2aZHYgqeXe+0w0QRBTukUWp5YGlQha69YK/AZEOR+enEaSLwdSJxs4J3EHVByLMPOkggmExjsAWiwg0WPrZ+59XJOLnWXX4++WUDWzjrU1glCg3LtP/G17tMpue7YSBbBaIva8njur9+enxhOew8VlPOF4aSK20G9HxhrngNltAeU0V5QHMsTQKh4/ey3AyGeowmZfWZ+LmjbqRwQ5HD/esv1x+f73GrlNBT5gLc7Bh/turplIHWJnTm2x3dNYxSzcA8tLHE1kaWJdtBpedbKPGkuimlG28eYUDChjjwIUmdyLk0Y+Yi/fv0EUrus8JTavG03R13VPcmWTeFZmNOFzN1QIKr+MCFOdxkbMbcEIbMrFbVW1i5UFAlBA8UTufi47Yq51GDDAevLe2LgL1RT/ydhna7hgG8WtN0Ibqk73l/CrLc0WgeBQGkd3F4Yu00x2m2A1Kk3ih49xyFxoN/sKHqsH6ZNwwsI5K67O9Q4L2i75rzFjq5d9dDeJ9T8NoKfJjDcwFormx2scS8f//3iQXHzKw2J0iaj5ryZcvaMZrcJh21j9XvfZGsHaw34OvjmSbxmTxjrpqDXo1XY9uW1uCPX81sa+37iGml85LN3EAX/AjCvFAI=', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt')]


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
