from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNqdV21v2zYQ/q5fceM+VAIS1sq6rTXqAmmjFcGSNGjSoUBRMLR9toXobSSdxgjy33dHyrYceQMyA4kl3gvvnueORwshsjtdLLWrDczoz2l7ezh4DfHHL6cwxmqyKLW5HUI6OGzyCj58urhIB2BX5bgugBZkMTaJjKIvVs9xGAF9mpVb1BUg+ZXNCq6+vD8/vbo6/XShTk4/R9HuO5RL62BSV06Ttxt6qNIBO72BmMK50ZX9gSYs2BrcAsHgDA1FhtHc1MtqqpxZusVLsJPaoIUfOW2/dKRW6TKv5hzdhwVObm0IL5VwgkV+h0aPC4RZTv/wPrfOSi8/knCpjSVP2sLX87Ow+ouEs3xstFmtg7VkpSeuWEEKbwMg74LuKwlXASCKACG3cBNwuwnyXzfyhe54GcBbgvgdYIElVutwfqNwCBn2RBEZ9BBYZygzCyIV9E4ozBf0PBAQk0MNFl0SrH+XkFGmK2DyeLdpbnDi8roaiUZbISMhRDQzdQlKzZZuaVApyMumNg50VdVOs7KNonbNruz68b4sJDqDKLMQ8TU9M2jZdfDYaLco8vHa3SW9RhE5kCyQhCAaFw8OOJuYhTGFQGwolUgisi7uME5Il4h07Re8BDGpy7KuRJKETexkgaVe7+GJ/ox2WbgD4MoOzwA/Q1X/rYeQvRocRdH18dWf6vQERiBQzwukihfRSXZ2+lf2+fj9WcaCbSmKKPt6mX24zk7U5emFujg+z65I44HjzhPfNjn3gtHVHOP0ANI0eYyiaIoz3wXUXRjb5bjMrSUwFXEw5KQTOHzXCTKUJ+mRbw/HrkkHFK9oSG1rHHPjqnw6alNjVLHxeI44TvJFiHnDKVc/GfNOL6GTtZfmM0LKBSUZ+iJOQmj80QTm2lRsm1NsFMiedPZYdrcmjc06FhZ3tYxEY2rObyYeOvE9+shm3PMM9wNF8Sh2LZEqmIgIiRo58X0vddNgNY07xRFvzLixRmK6PRFUCF0cbFSoUSwSsmaJ20W8b6iRaLkT4FZKLb3UxSigyFsE0ZoCh/cMYxAb1HSG0UpMh1o9pcYeiaWbHb4WB+CBsCNhsCn0BEWg3pnVFjFT1+wru5bcD+FkiNldslGhTlX1LSlxCjur5J9rPaCI9xNsHGT+i6qOexl7G13UFfY9/6GJxj2uiUG3ajDGRCrFQCj1OIQHbIl7BkWNP5SVtoq899kJkezhJxj6sz47/ki97eu1R5WobwUXb5sRV+U6jQ13bX17IOhUZyQ68OzUXhgIlhAoqJpiNpG5QxOLIBGtu2cAUIT5o+gYV+3QUBSBah32ECmwitswEhiNIN0DTtrDoWu1W7S0yq0fZN8G3xmKdZoerk1l0KrnOqjLObpY8LtIWhtGj3uZLZ7YPgOQsHmoqtyqMGP7OGyjoUrvKW3rpCdqEVnb76LR8A2gZZeTDOTSKjH7r1l++/4/c+xy7rBSvPt+xlkS6B7s43uwl3Bv1MtPhUsHTbpmh0MeeA2fwB4DynVX3Mn68dlNvt5V0bxXqWovN2ofr50I6fjrTeg92Vu6IuA03qMLt7ga5ZVL+uwHm81mQbXQ5XhKF60hwUD8B8Zlbqf5PHdxEth+8+YJppvLVx/UIcTt+0aJoCSghUhkUdOYjZ8AH7DVRaEID/I3rusi3u6Q0PVtyuJ46gufb3vegZ+dWz3JFxSkSf3s88hvTYGojTOOpM9TG+IePl6QKBTRk2vpi/4k3QS8C+n21I2IgvWI8RkrVdI1XSkxXB/c4Wyj3Mz8LoGfRnC0Pb4bw0yKpf8d89+/YWguh3sVubJuShNiO2p5jS4QLj5q8Qz3z1HnItgG8C39HlTCzkFR2mVJP7hWazo27gZ+8LQ6/EPHt7gchEpLk+gfRK8spw==', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
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
    print("True" if _run() else "False")
