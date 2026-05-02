from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': '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', 'ground_truth/answer.audit.csv': 'eNpNj8sKgzAQRfeCX+IITmKCXUq7KWh1YbMVpRaE+kDton/fTBJtdzmXOTcz62dop1c9NkMHcz/ax2pDw++h7RZ4TtM2L/241XPzcKHvVZliHCVcbyEwwP8gAATme1muOEMo7hUIiA9WAcQgfC+9JDISxufkO1ahtrlDZtpianNMbYzaijLFE9K4oPEdA12my/NzKSOjh1rHX0A+2m0Szk29sMsSap2RnuUSOfvddvBxmuH98x3d51+SiFDL', 'ground_truth/answer.kicad_sym': 'eNrtnF1r40YUhu8L/Q+DrmKKzczoy9q7pUuhsNss3WxujWyPExFZMrLcNr3ob+/MSGK9tAuONwMzhxdCPkbWmffICg/We865eao25XZ1fN6v23pVV+sff2Ds5g/VHau2YZLLWAjJZ3b1QTWqK/u2Y5FSx82j2pfRcGQ4nUW3H9/KPI/Mml49VM2qKffqyG7a3e6oesYXMk1ms/G4+mtTn7Zqteva/epY7VnTTof0met2z57VcVppzUrZbc/XDl17UF3/zKLf1U51qtmoiEWfI3ZT6r1YuuBLxmd6o91ObXotY9c2vVZb/a2YWMjcfpvNZv+Nd1/WJxNrTGgMOP+OiL+0bX/oqqbXUdtDuT8c3wzBV59u72Q8T6dN+CUbsMdqq/5nl3dlXx4flTK7/PMdEb9+Q1d8JcY3VR/rdJiyeaiVfllfdj2by0WasHixFGabZsvs33O7MJ1lYvZd+6RP+rPa9o9WUv98UGyrduWp7mfnL91VdT0eXpebp4euPTXbL68Yf/mGWHEuVt+DrGoOp57VVaPsBbHvIrcizZU527ZWzYOWZi/I2bK5h1n062/z6OI3fjjvtF8r/c8iXnLe7ALp85dr/+lK7fLVtPMF53zKoLhc+/21lz1+NemD5iEBsbxc+u3nuyu1J6982cdbPn/BZb/2jkmvkG5/fI2S9x/idEmIJEM+bkBiY3vNkUFhGBgZtIIioAgoEjpF7t7f608wGSGOTBm5IckY3WuWTBrDoMmkFjwBT8CT0Hny9t0yk5Q+lowJuaHJENxrmIwSw2DJKBYoAUqAktBR8uHnjxnnghBLpozcwGSM7jVNJo1h4GRSC56AJ+BJ+IbJfSwFKcfEJuTKMjHBPfdMrMRQTBMrFigBSoCS0FFiCmlEnBCr4zIZuSvk0tG9r+QyGsMp5TJqwRPwBDyh4JrwlJhrwlOHrglPvXdNtMRwXBMtFigBSoCS4Au6PhVCUirnsvk4KuYysf0u5bIKAynkslpBEVAEFAnfK5EFT0h5JTYhV16JCe65V2IlhuKVWLFACVAClBDwSuKEWMu7SciZU6KD+26UGInB+CRGLFAClAAlJGwSSc0mkS5tEum/TSJDsknwgAsoAUpo9L0npJpLpozc9b0nnjeXTBrD6XtP0FwCnoAnNKZxEestcdla4n9nSUiNJegrAUVAESJeiSgELa/EJOTMK9HBffdKjMRgvBIjFigBSoASCl5JIoh5JYlw6JUkwnuvJBEBeSUJUAKUACUUnm0laSZJPdyyCbl6umWCe/54y0oM5fmWFQuUACVACQHbveDUbPeCu7TdC+6/7V7wkGz3AjMdwRPwhM6MYEluRrB0OiNYBjAjWAY1IxifT8AT8IRGWXCeUysLNhm5KwvW0b0vCzYawykLNmrBE/AEPCExKFhQmxMsXI4JFv5PCRYhDQkGSoASoIREQVdaFLQKukxCzgq6dHDfC7qMxGAKuoxYoAQoAUrCL+haxjGpei6Tj6tyLh3b82ouozCUYi6jFRQBRUARAl5JLDJaVolJyJlTooP7bpQYicH4JEYsUAKUACUEbJKlJDYj2CTkzCbRwX23SYzEYGwSIxYoAUqAEgp97zm1GcG5yxnBuf8zgvOQZgTnKAYGSoASCjZJJmJafe82IVdGiQnuuVNiJYZilVixQAlQApSQGDdPaobKlJHDcfOeT1GZNAY0bh5zVMAT8ISGYZJRM0wyl4ZJ5r9hkoVkmGQwTIASoISIYSI4McNEJ+TOMBHce8NESwzHMNFigRKgBCgJEiX661/eTIJU', 'ground_truth/expected_mismatches.csv': 'eNpNj8sKgzAQRfeCX+IITmKCXUq7KWh1YbMVpRaE+kDton/fTBJtdzmXOTcz62dop1c9NkMHcz/ax2pDw++h7RZ4TtM2L/241XPzcKHvVZliHCVcbyEwwP8gAATme1muOEMo7hUIiA9WAcQgfC+9JDISxufkO1ahtrlDZtpianNMbYzaijLFE9K4oPEdA12my/NzKSOjh1rHX0A+2m0Szk29sMsSap2RnuUSOfvddvBxmuH98x3d51+SiFDL', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('opamps.kicad_sym', '/home/user/Desktop/opamps.kicad_sym'), ('opamps.pretty/AD8599_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/AD8599_SOT23-5.kicad_mod'), ('opamps.pretty/AD8602_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/AD8602_SOT23-5.kicad_mod'), ('opamps.pretty/AD8605_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/AD8605_SOT23-5.kicad_mod'), ('opamps.pretty/AD8610_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/AD8610_SOT23-5.kicad_mod'), ('opamps.pretty/AD8628_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/AD8628_SOT23-5.kicad_mod'), ('opamps.pretty/AD8641_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/AD8641_SOT23-5.kicad_mod'), ('opamps.pretty/AD8672_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/AD8672_SOT23-5.kicad_mod'), ('opamps.pretty/LM2904_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/LM2904_SOT23-5.kicad_mod'), ('opamps.pretty/LM321_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/LM321_SOT23-5.kicad_mod'), ('opamps.pretty/LM358_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/LM358_SOT23-5.kicad_mod'), ('opamps.pretty/LM4562_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/LM4562_SOT23-5.kicad_mod'), ('opamps.pretty/LM6132_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/LM6132_SOT23-5.kicad_mod'), ('opamps.pretty/LM833_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/LM833_SOT23-5.kicad_mod'), ('opamps.pretty/LMV321_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/LMV321_SOT23-5.kicad_mod'), ('opamps.pretty/MCP6001_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/MCP6001_SOT23-5.kicad_mod'), ('opamps.pretty/MCP6002_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/MCP6002_SOT23-5.kicad_mod'), ('opamps.pretty/OPA191_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/OPA191_SOT23-5.kicad_mod'), ('opamps.pretty/OPA211_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/OPA211_SOT23-5.kicad_mod'), ('opamps.pretty/OPA2134_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/OPA2134_SOT23-5.kicad_mod'), ('opamps.pretty/OPA277_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/OPA277_SOT23-5.kicad_mod'), ('opamps.pretty/OPA347_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/OPA347_SOT23-5.kicad_mod'), ('opamps.pretty/OPA627_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/OPA627_SOT23-5.kicad_mod'), ('opamps.pretty/OPA827_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/OPA827_SOT23-5.kicad_mod'), ('opamps.pretty/TLV2316_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/TLV2316_SOT23-5.kicad_mod'), ('opamps.pretty/TLV2401_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/TLV2401_SOT23-5.kicad_mod'), ('opamps.pretty/TLV2462_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/TLV2462_SOT23-5.kicad_mod'), ('opamps.pretty/TLV2771_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/TLV2771_SOT23-5.kicad_mod'), ('opamps.pretty/TLV316_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/TLV316_SOT23-5.kicad_mod'), ('opamps.pretty/TLV9001_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/TLV9001_SOT23-5.kicad_mod'), ('opamps.pretty/TS912_SOT23-5.kicad_mod', '/home/user/Desktop/opamps.pretty/TS912_SOT23-5.kicad_mod')]


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
