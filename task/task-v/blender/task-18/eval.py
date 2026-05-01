from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import shutil
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender5.1\blender.exe"

BUNDLE = {'eval_inner.py': 'eNqVWW1z2zYS/s5fscd+MJVIqGwnaU9XdermnGtmkrTjOO20aQaGJdBiTJE8ALKj0zhzn+4H3Nwv7C+5XbzwRaKcVDO2JGDfn8ViuYrj+PRG5CthSgUp/hmhr+H05fgYRiN49eIEvs9lMYfkF5Ffw0P4RdzIAYuin6XK0kxqMAthQKilMCsl4eIsu7oA+SHTRg/hsjQLuCDOk5nJyuICBIq6IBn1AjJVSmpZmKHlZqLIUBhu8rkwghW54EaJ2bW+gFlZGJEVGhWImcnXYG5LcJtDKAsJ2qisgpVGu9pq+zZrE4bogoRbXPAUuhKoQlyWKwOpEkukPxoz9mgMtxn6kxVpvpLFTHqSMXs8tH4JTw7HY+f5siQF2vqI9maoAWlKZJ3ARVVqyS7RLv324KwszcE7lpcz6zhbX0AWLDhkYxe1NsMPUsyRQZXGRUqucqk8W1EWo39JVSJIb7S4kpMI8HVJKEqFoF5iuK5UuUKZo1G1NouyAIkpwKo1QY4EFvBvKmEWX5rySwzGLQq3q9/GcRylqlwC5+mKEOccsmVVKsyBovDm6CgKa+qqEkrL8P29LovwGUFehM+lDp/0WjsFBP4sF5rg8nv10hAw9fJ5FEXPzk5envLzH19A85ramNnXF2BKjIwgtNDNNshGKPMlOWoxi56/evbizemrp21hU8R2/PgTgup0iM5+/PGc/8qfHY/5+cnZP07Pt22RHyo5M3IOhDdbw22p8vkI021mEyOdYuLQERQR3P/6AvKskEKhfewIjcGTKWaq1BqejH3KdqwJHpFDh70OeYu8FdEPpyd/52co4OXzV9AXjWVWYH5qoETcScPaGVN+2hM80zqjzKxPYVxeaqluBGZcjBB/V8Me2f/wdCFn12dSr3LjcrtAhycEh/1WUc7MJ3gEy9wuLPWV2+2R9XpWKvlUqLmTNCPReoLh1QYdtlmWzGUqUBdP8QyXaj2lzUFk6XELxHyeaJmnQ2vH0OsfktohPHjAr28HkzoMRMicFiaqCvMvabmT7EgYeEXfVaqspDLrRm2ec0dotbd0KIkHs7D+Jy19A1ek8jyZMcdok22GGdw2a69CgyjnXFPA9mikVM9SJ6wxD2SuJeVO1BLF59nM7BGzia2SeOIktfQOIXYyw16jZbiTabHzB0k3M+ZSZNOwhxigSAyzXcD3u/vytS9ad3eNV8pW2G2n6KRqzKW38SiGB/DV1++i+wROOhYshbpG3vink9evY4ptDZ0Navzs5PmLuMNh1YXUSmOAtxsScvcO6jB8c/zkjr6Qv/Eg6uUMxu7ZJsH+BMLmgKw72Iv8ARl5cAdxf2zTOLHYopubbbwn7DC9G3y+jT6B4t+LmL0vsyKx9JjREeHD06yYc1u1OYaeC3v/J02DMQS3xClMHkK88M6c1DRTWBSoIwqFHy7azcntAi9ouGBOhg31BV1yiKtmdG8GyI0i3oZ10kkI1IG7RjGrZSsfUDbGSRuvpLOH8adt2wGgndTx2AM/M9YWmE7b7k120PDBM2qICqLWCoka2v8hkGqFtR5bhsQ2BZw6BR8uf1NfVmt3LmZYWtHiuswmvrygsWRlqRkxs0ynWS53xQURjIpsTDTc9ZbxEJ4JzC7sBOKiBNed0L2zaWS0k9u7QrKi+4Seq5WV6eRNt8VZXqPWjXXoKSsrzW6X+CYLvsT+1PpC/4ht2nLKcskPM1kZOLVvCAcI7Gf3uktCO97SAqQC9/CO28g/4WQQ5Xy0grAUeqf0DL+hw+QPtdnyg2F2zW1/AccMsDuvO33mMgRXHI/t1cvL99jgaHYlTRIjtbcNqXhJdYzIt/MT15hZVzY/45Ozlyfnb85OY/i99ioQkYY295aLwbAay26COxu2FlMyMjx+YDS37NupWWlMlk436J8wRiVIP4QDWjtwB2QQ4PD57bROehHycX3E4ByfYtzR1MEYF96F0Nx2dxia5nEmpgJRx9wztuhvpKMPTzj76Zvo4YOUr4faBXA7frUpBEfQsxPOxsjpJnDcDaGxJSzfyLu/7UaXrg5vxXTzVri6ZTviPhfebQU76bVxcG/0HzNb0V0hxl50VRhKxCMXfzF3Sbv1TBqU4jZmC+Hed3ypwJMRFFonvznGVLO6Mm0TXp+YvtNsZXBvImBRSbD1bm6RQfRp9d14dwSizztoWoIQFNi06HtOhu1dCTbTwGavso6V7+rrHOPXNuAvaMC9SD1hEG5eJVOp6JFLQ5NwDjGC36kaus+OY7rv8u8YN+ycsn0BbWSQgu2gtpS2Ksk9B8X5NNkN6KYR5SKKEWtJt73VniqVWH+mmyYaXQkO2EZCC5Ou/d3c7kHlqz2ohPMeULmRDSr4+U+jUteyz0HlRu6iUiu9H5Wg5z5UgqhWTGvpn4dKiEZXwr2otO3/JCpfMwuBB2ZW3kilwyjrI82yPj4aO2TsGMRdzvg4n7Scs+Tc7sOIBmDjAXwzhXrg4noZRA+ZYR87NVGA7I/62RsYG06uRHEl+dGYPxpvw1hbSwXe6d7BsGX3dNPvTw82tbk9PLjai2aZw6b2p42WvYx6bL3/KvprB7RmyviRBi+PHVy4SmOJvBSmHeyaeLA/rDUNHpc83Y4soUfCR6TLItUZiO1EuZY23eDHCXuU3oGLSIfPRsX7dzhmfpbczHfaM1PW9KEBLGwjj8fOp3ZfepPJW56LtVRsVeHlKRNHM7/aamClm2zLOZ/LSl8pUS049aaBvMtOzRpx+Du/YSaW+ZV3pLrkqiyNI+JucFpPZn3ni/s+G5B6IUMb0U9NI7Qmd4J4f8wBb9Eg455ewz1jNHHlwvD0eFw3HFHPY/cy0zorsP2lx1Zrz8SOAaeblg17W2Eng2y39MHAmn5PI+Nz4XwhrS6rFy3ICqPh4W/ULmD/a6xN+Bha2g8jS0TD8Xz0qxcQRuWQ3NLvDzQ7dHcHXMu1q3QD0IvyVsPKPqrbWSv8xuC1WFa59GKIr1ZxoKGZwMM8U9L+xvDHv//nZ5O2s6SmjUbSBsZ//Oe/R14QldhQYQ8ZezK21oc5KBKjLSs04BLP8yHzuU5B5tYvvq6PtQ9+68cAF0mKMO4YJIU28aJvAutz1V7mdXHvqBvBzrjaHvvu2Li5vWspjR0D+HYK7UmxO6ilWTjqoJ0KoJcRfWbadnPNi9wpQiFOfD3dtJ2bPLT1qKdkC4VHDjY7rt+BrV1d5/ueULxPvrUqr+8GPUQBErKrCddeq8IsfdOOJSr3MfM3EukKxbRzouxIhioLL1emWhndGqMM698cpm6Kg8lusDqm2ZVd8DeSl9c712FhWFuP0eQyMwnp9tyVwuNrF5gfgQ4GrY349OeTF/zs9PWbF+eTGB7aH4HYfLWstGOqFQyCChqiJF46QnZDM6+1ZvQx1Ml4NLLPtbTWVERPTG9v6R/ejHP5ISHiAWo+nLjhK/VY/UyBonIL9scrdqKuVkt8KP+JvqlkLvUMb1T7OBt+PJX0k+kRC1Wf0psLz0bqbUCxHCv5zxUWlvmUhjCD4CDNhytmlRGXTsgWt+ui3SBD227aZaOFkeB2nse5HaBwO4DiPHbuuUBG/wf0ZRqf'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\answer.blend']
INIT_MAP = [('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend')]


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


def _call_inner(root: Path):
    module = _load_module(root)
    func = getattr(module, CALL_FUNC)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    return func(*args)


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def _run_via_blender(root: Path) -> bool:
    result_path = root / "_blender_result.json"
    runner_path = root / "_blender_runner.py"
    added_paths = _bundle_python_paths(root)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    runner_code = f"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path({str(root)!r})
RESULT_PATH = Path({str(result_path)!r})
CALL_FUNC = {CALL_FUNC!r}
CALL_ARGS = {args!r}
ADDED_PATHS = {added_paths!r}


def _is_pass(result):
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


spec = importlib.util.spec_from_file_location("eval_inner", ROOT / "eval_inner.py")
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load eval_inner.py")
module = importlib.util.module_from_spec(spec)
sys.modules["eval_inner"] = module
for path in reversed(ADDED_PATHS):
    sys.path.insert(0, path)
try:
    spec.loader.exec_module(module)
    func = getattr(module, CALL_FUNC)
    value = func(*CALL_ARGS)
    RESULT_PATH.write_text(json.dumps({{"pass": _is_pass(value)}}), encoding="utf-8")
finally:
    for path in ADDED_PATHS:
        try:
            sys.path.remove(path)
        except ValueError:
            pass
"""
    runner_path.write_text(runner_code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [BLENDER_PATH, "--background", "--factory-startup", "--python", str(runner_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except Exception:
        return False
    if result_path.exists():
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            return bool(payload.get("pass"))
        except Exception:
            return False
    return proc.returncode == 0


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        if _have_bpy():
            return _is_pass(_call_inner(root))
        return _run_via_blender(root)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("true" if _run() else "false")
