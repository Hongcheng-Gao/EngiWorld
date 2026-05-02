from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqVV+9u2zYQ/66nuHFfJCzRYjftBqEOkKVaESxNjcQFOhSFQsu0LViiNJJKYnQB9hB7wj3J7kjakmOvWAVEkqnj7/7/jmGMpfe8bLmpFczxz3C9Oj55CeHbD5cwFTJfVlytElCthPT87VUKvEXZujVCQS1heFzyNb5Oa65mURwEF0uRrzQ0QiFcJWYkZJYCdDutCmNw4S6eqtkdhKLAdQV3UyX4CgHdMsnmXNayyHkZzERZ3AvFp6UAyStxBGjjHZf6QahOfoH2yFlmVGuWMOdlOeX5KkqCAGAQA/pXzLLHqoTu+uevv+3OeYHADVdaaHhAewDFYmGUEHFaikpIM6F3BBrGINyKzloMC5cL9MUCaTQMcjTBAJcza6eGeg6v/YYz4NpqK2RhrEoCfBGDLhaSlzt4Xwd0G85o+ynag5FZZ24tW3KdPRRKWADB86VHR6VWt00QoBScjWAAr0n2jJLDA/jaldcN5hJclsMBxX/wChPNGAvmqq4gy+ataZXIMiiqplZks6wNN0UtdRD4Nb3Wm9eDIaYQpROH2HCzLIvpBm6MP4MAAWL6EBdSC2XCkyPQRoX0MUQTMKhZFsVK6Lq8F2GEsgqh/QN+BJbXVVVLFkVOic6XouIbHbZqb4RuS3ME1BHuHeB7kPUfPIH09GQYBJPz29+yyzcwAib4ohTYKSy4eD8epzfZ1fnv6c0tfvrCBuwI2OAVewqC9OM4vZikb7L0Kn2XXk+cwNhKjIf2/sLeT+39pb2/svef7P1nRNmC3F6+vT6/chj4blHwOfTPF/55Spqxd+aAgcHG6HVRiH2Y2JBGcHxmX+BPuK6lSGwdEAdQvVHZhKzfmoTdNR6Lkm3dNGgPwmKQaed2uZhDE4vHQhsd9qTpUgIrRkIT9H6QDd5q4SjJGlsVWmMlZbNCJZRxa3aXIYdL2kfWmWdbehXhdKFYtzkktsuK2cjnlUpKNLaYRlRciIXlYjcarhbC4O6DEXXg6LAXK3QvpFZvLJSqSfuc7XBajYRA5EXx/oJIT8iLj43IiSj70ae+66IfseBZKJU3U617SuuaLE4nsWW40BkXxXijTz4kdGFLZvUKZSeqFTurlV5Qtdcrp1E85qIxkNpHQeyhQexptKncw/4Vqe4Q+JxZ88BGKIEv4snpUnFuZ0nMkYHkLOz1aLiFoYobsS3Fs6OuKrnWYjZy6rvlTXRHTqvNwsd3V72NPDctL0feQLcebTNMGXOYyX/k4Hu4qMsSlWwHhmVxT/axi+PmC3ayKCkjISNXWGQ7UFjapmjGBQ7akHl5Fj25endYuPuTthv0M3knwKLPPfHMzRHUqPcU2v0e9Sn41vDvD8b9PISdy1iSz1kxOpAgjcQsZuHXZH2qvORGQ7STs2/wY28eH3BjN5Y9Vzw3/x9P9kV3Henr6JzxxTUW6tiPdj+b7di3xwVXXLhGpwLKtCsXPBHh+eBe2AOC7rf589wnOxEhXu+XSvcRv5xsfxHIgwWJiRxRW8hIE3vG+tg94YPDs8cJrD3cyfCBe3emaLJ3JpHwAx5bumw4Fz+RXZ/RGNmfOhJew2AXYi8CHRl9S50fOnDt18iuskPUczYa7CSPXnzL7tWEd3W3DDrGCdDhzJYKHsCwHlmWVbyQWcaSDWWVQoZ0fEL6v4/guxEMe7NbFRLz0Wq+EAk0a7NEUqf5GzdruP3wy7vL29vL99fZm8sbPAC4yYhQ2syQrruCoDUc9SYc+qZzx6dRb5R7Az4NPjsRp9kJxrqt8P+Mdeh7dgt3QvZvZPIaQ4UuDuITZEicGIMo+BfsK9oo', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('breakout.brd', '/home/user/Desktop/breakout.brd')]


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
