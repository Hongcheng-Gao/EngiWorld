from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('C:\\Users\\Administrator\\Desktop')
BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('materials.json', 'C:\\Users\\Administrator\\Desktop/materials.json'), ('plan.dxf', 'C:\\Users\\Administrator\\Desktop/plan.dxf'), ('site.json', 'C:\\Users\\Administrator\\Desktop/site.json'), ('windows.csv', 'C:\\Users\\Administrator\\Desktop/windows.csv')]


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


def _install_ifcopenshell_fallback() -> None:

    try:

        __import__("ifcopenshell")

        return

    except ImportError:

        pass

    import re

    import sys

    import types

    def _normalize_type_name(name: str) -> str:

        known = {

            "IFCPROJECT": "IfcProject",

            "IFCSITE": "IfcSite",

            "IFCBUILDING": "IfcBuilding",

            "IFCBUILDINGSTOREY": "IfcBuildingStorey",

            "IFCWALL": "IfcWall",

            "IFCDOOR": "IfcDoor",

            "IFCWINDOW": "IfcWindow",

            "IFCSLAB": "IfcSlab",

            "IFCRELAGGREGATES": "IfcRelAggregates",

            "IFCRELCONTAINEDINSPATIALSTRUCTURE": "IfcRelContainedInSpatialStructure",

        }

        return known.get(name.upper(), name)

    class _IfcEntity:

        def __init__(self, eid: str, etype: str, args_text: str):

            self._id = eid

            self._type = _normalize_type_name(etype)

            self._args_text = args_text

            self.Name = None

            self.IsDecomposedBy = []

            self.ContainsElements = []

            self.ContainedInStructure = []

        def is_a(self, type_name=None):

            if type_name is None:

                return self._type

            return self._type.upper() == str(type_name).upper()

    class _IfcModel:

        def __init__(self, schema: str, entities_by_id: dict[str, _IfcEntity]):

            self.schema = schema

            self._entities_by_id = entities_by_id

        def by_type(self, type_name: str):

            want = str(type_name).upper()

            return [ent for ent in self._entities_by_id.values() if ent._type.upper() == want]

    def _split_top_level_args(text: str) -> list[str]:

        parts: list[str] = []

        buf: list[str] = []

        depth = 0

        in_string = False

        i = 0

        while i < len(text):

            ch = text[i]

            if ch == "'":

                buf.append(ch)

                if in_string and i + 1 < len(text) and text[i + 1] == "'":

                    buf.append(text[i + 1])

                    i += 1

                else:

                    in_string = not in_string

            elif not in_string and ch == "(":

                depth += 1

                buf.append(ch)

            elif not in_string and ch == ")":

                depth -= 1

                buf.append(ch)

            elif not in_string and ch == "," and depth == 0:

                parts.append("".join(buf).strip())

                buf = []

            else:

                buf.append(ch)

            i += 1

        tail = "".join(buf).strip()

        if tail:

            parts.append(tail)

        return parts

    def _parse_name(parts: list[str]):

        if len(parts) <= 2:

            return None

        value = parts[2]

        if len(value) >= 2 and value[0] == "'" and value[-1] == "'":

            return value[1:-1].replace("''", "'")

        return None

    def _parse_refs(text: str) -> list[str]:

        return re.findall(r"#\d+", text or "")

    def _open_ifc(path):

        raw = Path(path).read_text(encoding="utf-8", errors="ignore")

        schema_match = re.search(r"FILE_SCHEMA\(\('([^']+)'\)\)", raw, re.IGNORECASE)

        schema = schema_match.group(1) if schema_match else ""

        data_match = re.search(r"DATA;(.*)ENDSEC;", raw, re.IGNORECASE | re.DOTALL)

        data = data_match.group(1) if data_match else raw

        entities_by_id: dict[str, _IfcEntity] = {}

        for match in re.finditer(r"(#\d+)\s*=\s*([A-Z0-9_]+)\((.*?)\);", data, re.IGNORECASE | re.DOTALL):

            eid, etype, args_text = match.groups()

            entities_by_id[eid] = _IfcEntity(eid, etype, args_text)

        for ent in entities_by_id.values():

            ent.Name = _parse_name(_split_top_level_args(ent._args_text))

        for ent in entities_by_id.values():

            parts = _split_top_level_args(ent._args_text)

            etype = ent._type.upper()

            if etype == "IFCRELAGGREGATES" and len(parts) >= 2:

                parent = entities_by_id.get(parts[-2].strip())

                children = [entities_by_id[ref] for ref in _parse_refs(parts[-1]) if ref in entities_by_id]

                ent.RelatedObjects = children

                if parent is not None:

                    parent.IsDecomposedBy.append(ent)

            elif etype == "IFCRELCONTAINEDINSPATIALSTRUCTURE" and len(parts) >= 2:

                children = [entities_by_id[ref] for ref in _parse_refs(parts[-2]) if ref in entities_by_id]

                structure = entities_by_id.get(parts[-1].strip())

                ent.RelatedElements = children

                ent.RelatingStructure = structure

                if structure is not None:

                    structure.ContainsElements.append(ent)

                for child in children:

                    child.ContainedInStructure.append(ent)

        return _IfcModel(schema, entities_by_id)

    module = types.ModuleType("ifcopenshell")

    module.open = _open_ifc

    sys.modules["ifcopenshell"] = module


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

        _install_ifcopenshell_fallback()
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
