from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'eval_inner.py': 'eNqlGWtv28jxO3/FgPlg0qEUSb74XCEOLs0lQIvcNYhzBXKuQNDkUmJMkcwuZVvW6b93Zh/kkpTiFBVgS9ydnfdjZ+i67ru7KN9Edckhxb86Erfhn2cXIY+SLMpDsV2vWc23YZqX94yPHeftisW3AupVVEMEaY5fSSZu4T4SIOJNXtUsgfusXsH5KC3zBBQmMJjmwMs6qrNi6dQrBmsmVnCzhfMJJGzJGRMQ8XJTJEC7XyB6yARsM5YnuAFVmRU1xHm5SWAd1fEK0RCgU/JsmRVIhihnBdRlznhUxCyACHGdE49IM67hyyhhFWdCZGVBtBjQEytqlO0PES3Z3HEAP9W2XpUFMFTPuNrCaFTefIVXVVSvXtTli3JTV5t6jGuvHdd1nZSXawjDdFNvOAtDyNZVyVFBRSGFRVKOY9b4soq4YOb5qygL8xtlWpnfpVBY4zLPWSxxGLRvUUE142o/ieooziMhWLPfLAWQkuocx7n6+O4tXMJOyuaKzU1dlnlYRGvmzkF93PfSxr+iNd1AwXGWhmkUszAmihry59kkkD+ewdk5ZEXB0G94Bs9h+jdAxeAjR7sIKFMC+LaJEqSMv57D+cVPLeI7xuse4qlBPIWYkYh4ZjY5PTvXbBtvjIplzkJ0GDx5PhlPgt4+mr8RC7cnLzXAOivCKqvxZFWvDAQCmH32UKGqWUJAwuyfB84eNfhLo1VH/gcZCZ+Y2OT1XB4nbc5B1Fw5EJkkmcMNKlourMVS7R7AdRWXnL2NeKIwxTLI5pCj16LupBG9hKUR0iKDYLhuL2nTV86KWxAliSdYngaSj0DTD4hsAKen4e29r5DThwDHiso4qipWJJ4ljjfA4GtCv1S8rNBu25ZsnocKUFK3aHCGwVBI+T2Lni8jEo958VgdlJknRk+y2TpKsMaIwsRECjtCcTqeQJYqZC17wHLByNiOhSpMsrg+gmbnSiLoBhKTRTcAV+E0ey2VoMFiPq6SB0F38Vi5yK49bnSAKFHNcgG/9wMs1ueQtvb7ViqO1mS8L1SeFZggLuHaHblwCj9fLJzvIZx3OFhH/BbPuh/fXF25pNvGdFKp7vs3//jgdk5Icsa1UhfgekdI9gto1PDqbLanB5LX9Z2DJw2zR7YJsY5A2J0QdydHLX9CTJ7s0SCHlZu6njQuZcm+wefjabr3f5xJ7UHufwp3/BVrlifh0aUdMlAo83+IxcOjeqKNpHOytJGyzTIvb5ADypPWarzhaGFKC7+XBbOXwiVWzorspFOFkvRuHdHiznKRkBUCC5Vn+UdRFnkZYwXVyAJ5LujibqDJBTQfWJ+Jka7DtEzuXF1k3KvNzWcqOlMXnV0KhavXC3ygEqMfjjm+W5X5VvIgZNDVnt8NEqM+YxTNgd8BalVxgNkD6pNg8jKDSaiQ1kJ2OQrAirhMsMpdups6HV3QCuclF5dutiwoa2CaE5Cu5p0o49E9xZm9bLwJ6eLuGOtDVnldrlHZeI1QUIiEvhEuQgUSa577zPXnA73FZYEXng3rbNTlLXmSwlDlWd2jVEdL3Cao68miz4PcRO2U7pAa2Zg0B9rfJYrpfOHTwZypBR9eY2GXwZg23rCjXWM8//l0PwzPA86kCtT/7EU/5Ek/7E3HPerpoDQflluavTug2YcAtgE80i0gL6Naa3bhB/bzrPd8thhyamcTI5ansftD8CZFHBT5mqxmY/QX5Fe4qMW+1rY5wEgf4glmOhpaHtDQQNE/6oSHLTJMbxR8wxQ3EMfyK5QpaZxGMfYdodIDQh1Xv7yP92pC/3pQ34JsgpT8h/leZskDYsCGyqtvdTZwX7g+Rr5/8AByLM+8gsn8aIBprAP3oO4A/2j7u8iRbfKv4wRa8Y3fSH+kwwf41oZvD6H5sRd5wpIqk7SO2TFkYLHg+/+/S7S3TZ1zKCvpn3tzY5A9Mwu3XkUNrW5+dNaPUd/UOI7jUnjyh2y5C+G1kIqUMJACo+O7kG3WqWwmvRgvOg9oR4HfjxJmJPQSbT02V5ymFZNl0ZPaGrKOrfN7dFcWxSsgEPYAd9SzYoNQMOzNsfvRy3UJ2JKp2QHe6LI1dupjieOTZE3APVZfOYuoqe+HKOYlNlZ4CwTlLYagas5k9MgNVePl4UvZHpgguiNnRECrMbhDkNYWd7ZADdANUz2bzMZuVqTWtZHQ3g/QylvZDM94/A6jD0ZwT0F4ejpDtdLaVK1N7bWZWpvJtX6pRmyvJCNDR9fsJbNDsSI3X8GUjaazwzFyw1l06/SPvFYK7B4xOiUI24mUB37jtSchGpeRowDZeSt3aX1EzjvaEY66p34ZYTePfgDRuiyWlqHhjXGajGZGElo14Kh45Jj8aEt7ctxBk6xCjbPKtMViBkkUIBuBfjF92fOgzE7AZNgsgKaEkY1ZsVkzjq7SEUerbUt5aITu1tPz4NqWiZD4voTP3Folel+J3gwJ4t/j7AmSmmxGBefrD94WlU8+oJ89zIznPeLT4+yoz5GeMA/IL2rzt7S4xTPoUudDso1w7yMsyM6Tzqbgu3jIEEeuEM/gN8aXTNlKGxRZI0PLlFPWK3QAT42aRmU6uinvc0g2WAtjVKJQWNaEI+naupJBnNlRHOXIbbIdCEPgawJXeAYm8SoV82sr5isV3msd3lKxkwup2MnFUI0t6Y6THFUjXWj0mV6fL1k02uwWKLXXFKRNEdJs1MMuNrS62DjipKpmnuXpOY6mWooxAY/ZAwaz6B82CGSpdGlTwWF3JXWKpcEtSvjX3/8JGK47c9qeHmhmCYvzHXSkJ8JGqC67mPTwjgtpc6tXb5g17TrFvwK8bov3okcWSy2VCL2PpHW/gzcRDMVpr1VJ3V2zvwfdI3kI65nRJEzNHEKrlGDnR+XHXeSSYKij6/Nmj4EDgrpWDdaCeKOR8XUXZjFgVzd+Jzs6fEJPJ4v9icXuyU7iObHxEIhvVF00l1ktea91KOQEurOv72d+TxxroBy0aI0gvZHzUJSdPrLXFaCVQYvQxYBCGEu0LFjD8qDl3GbBgjjIgjyyB3XyIAstBs2CxIL3LHLX3r3LVmdgLDqcog9U2Xv9o8YbmIZ6GGjOPpRCFf7zCWIecf3+Q41HKNbwx3z8Mt0DtmO5kcvGaEu1jh7UsF7eXB+86EZ4W1/mVC9UyT5U1XboOK007cg/sDC+NmbpvhUYyoNH4K8vfxHzzen5+CcSgaqXFqGDxZZB3xTs+81TzBoPIo+nA37rQ91XFIvD+UOe2SvKAx/qYLAZtXOHTvNsjV0hLegMXXHqFyWzesysS63acN/9+82H8NO7qz8+fJ67WMno5dY42awroQ6Zibvvm2sfFZFQvU5r6wG6m2bykhrvAKpS1HhHSbOlXNDcaIYPFKOWkCaj0njEl8IMPWlUYN7Fjd/wJd6civojPXEvYSLmWUWOe2nekDL4c3R2AZ/U68wr7bCgXpqNdSaoyIZERmLzXPnaEA3J2bdNxlEcKjydslqNbdY0t+sIGzTNJ22YQmOg1ISAbNPKTlv0QlJqFmtDKFNtGMoRQxgSyjDUkwaF3/kvsA2eMw=='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['C:\\Users\\user\\Desktop\\output.obj']
INIT_MAP = [('scene.obj', 'C:\\Users\\user\\Desktop\\scene.obj')]


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


def _materialize_desktop_view(root: Path) -> Path:
    stage = root / "_desktop_view"
    stage.mkdir(parents=True, exist_ok=True)
    if DESKTOP.exists():
        for item in DESKTOP.iterdir():
            if item.name in {"eval.py", "_runtime"}:
                continue
            dst = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            elif item.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        if src.exists():
            dst = stage / "initial_files" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return stage


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


def _resolve_arg(spec: str, desktop_view: Path):
    if spec == "__DESKTOP_DIR__":
        return str(desktop_view)
    desktop_prefix = str(DESKTOP)
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("\\/")
        return str(desktop_view / Path(rel)) if rel else str(desktop_view)
    return spec



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
        return False

    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        desktop_view = _materialize_desktop_view(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg, desktop_view) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
