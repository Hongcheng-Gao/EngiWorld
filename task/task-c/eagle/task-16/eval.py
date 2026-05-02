from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqVV21v4kYQ/u5fMd2TKlsiToD0ekKiUu5CK9S7FCW56qQo2lvwAFaM7e6uuaCI/96ZXRtMoKcekrOw88yL55mZ3QghRmuVVcoWGub0WGWezrpvIfzj8ximmM+WK6WfBmC+qTLDNWZQ5JCk8zlqzG2qsrNEp2vUUKa5ieIg+GzUAgcB0Kfc2CWhkRzE5QbuPr//NL67G/91I6/Ht0Fw+BtWlbEwK3Kr0hy+sgvpTcfZVH+FkIL7qnLzrdkwBdglBhpdKDOEhS6qPJFWV3Z5DmZWaDTwLaUYKgsEUas0X3CIH5Y4ezI+xm4M15ixGzXNEOYp/cHn1FgTO3kvhonShiwpA18+ffS7/RjuNqtpkcGStlWWwTuXALieXJxf39Az6dJKz6RHKz2TPq19r30ZMw5UngBhYVrYJdlZ4z7JQ9EVHvsLY7s1tnsa26uxbxnbq7G909h+jf2Vsf0a2z+NvSSsECKY62IFUs4rW2mUEtJVWWhLunlhlU2L3ARBvWc2pvn6vMpitBoxHmW4omK5p++cxdG9t1gqu8zSaWNuQj+DgAzELIgpm6hteNEBY3XIwpBCIHqkjGJitsjWGEaE5TqsFzgHMStWqyIXUeSdmNkSV6rx4Zi/RVNltgNc+P47wBvIi3/UAEaXF70guL+6+1OOr2EIAtUiQ2oIEVyPPo7/Ht1evf84YsGrAhVBMPoyGX24H13LydX49o4wDy7ToSCyRQcEcc1LV0SdnaDrBW7ptQU9L3BLvy3oe4FbLlnw2HI8vmG/L6VvZZ0WQL30Ki4WlbzP8odB73EbBEGCc9enNAgwNNV0lRpDxMok1QMmIIKz31oJ871DOPLmqDlUaRHkgJpge+WQZ4xMk2GdZmYYS8ftkLkmW8SeU0y4NUmZPZ1DiwEnTefEmvWg2DdtGPnQ+KOI2EZV7CeH2AFInzAnNNuuCbHbx8zgIUrHqHXB7zcXL634ti6yOQ8kTvULRbEVh5pI3ZSD9i+q45kbSrEqS8yTsFWo4U6NJhgORbIfV9KHLjo7SKmMQcqsrnC/ic8lzixttwLcS9XMViob+iyyCy9qKLD4zGn0Yo2KBizthDRxi4Tm6VBUdn72jqrRJcIMhcYyUzMUnnqrN/uM6aJgW6P7mHuTuCYDIZuLdhCaGrJ4IhC/wsEu2ee+81nE5xmWFkZuoarjuYJHjm6KHI8t/66IxhOmiUG7KTHEKJaSEyHldgAvWBP3AxSV7sSQykiyfsyOj+QEP17RHUSjqz9ozrh6PaJKFE+Ci7d+I67K5jV23NX17RKRGpeJVnoOau8NfCiyjCLwR9h0497CHxNuhybK1v3ajQ42G6cWdSgIIVqtw6qkUMYLtKHgXyJqN5yTU0DcHodBNe4eGPLINnx4dLrKkuYJz/chHMy6mEZONTXkiR9Wjp9wQ61cJ+AHKGMvmC6WVrrBzrYar8cEtkI6waKhkwaT8CDS6IjEGvU6cPgZTik23cgMJGUHkryzcyj9vexo0u9Tm5QyW2ecUs5vUj56dnZHvYiYmsRR6xh3JXXQPUl+YCL/DxP5d0y45gubWIav4o/cXSRs/ByJ98X7f0jdEUtNnZRbSbblS5Jv5S5g+XLoYNuiuUV1u08PWCazg1cxMi2v97aH6jX5Ttlnwiv5126BG8L3rRpQfpu5xPkRUq7oqiylGDTdnmEe8gVK6cU6gp+G0NvXQEnDlgir3PX8+1dzGub+MCZTxiY0VvbZ5z06dWzYq1vMX6CGrdtDHcBD99FDvGcPjE21on8oNmHdoTtzF25a1Ri+uvMrduMLX0fdKPgXsCDFOg==', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('diff_driver.lbr', '/home/user/Desktop/diff_driver.lbr')]


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
