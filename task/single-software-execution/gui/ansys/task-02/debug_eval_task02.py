from pathlib import Path
import traceback

DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_plate.db"
RESULT_FILE = DESKTOP / "apdl_plate.rst"
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_plate"
MAPDL_PORT = 50102


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def allsel(mapdl) -> None:
    mapdl.run("ALLSEL,ALL")


def node_at(mapdl, x: float, y: float, tol: float = 1e-3) -> int:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    mapdl.nsel("R", "LOC", "Y", y - tol, y + tol)
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    allsel(mapdl)
    if node < 1:
        raise RuntimeError("Node not found.")
    return node


def sort_max(mapdl, item: str, comp: str = "") -> float:
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def reaction_fy_on_x(mapdl, x: float, tol: float = 1e-3) -> float:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    cnt = int(mapdl.get_value("NODE", 0, "COUNT"))
    print('cnt@x',x,cnt)
    if cnt < 1:
        raise RuntimeError("No support nodes selected.")
    mapdl.fsum()
    fy = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
    allsel(mapdl)
    return fy


def _coord_span(arr, axis: int):
    values = [float(v[axis]) for v in arr]
    return min(values), max(values)


def _within(value: float, target: float, tol: float) -> bool:
    return abs(value - target) <= tol


def _check_bounds_from_instruction(mapdl) -> bool:
    nodes = mapdl.mesh.nodes
    if nodes is None or len(nodes) < 2:
        print('bounds no nodes')
        return False
    xmin, xmax = _coord_span(nodes, 0)
    ymin, ymax = _coord_span(nodes, 1)
    zmin, zmax = _coord_span(nodes, 2)
    ok = _within(xmin, 0.0, 1e-2) and _within(xmax, 50.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 1.0, 1e-1)
    print('bounds', xmin,xmax,ymin,ymax,zmin,zmax,'->',ok)
    return ok


def evaluate():
    if any(not is_nonempty_file(p) for p in [DB_FILE, RESULT_FILE]):
        print('missing files')
        return False

    from ansys.mapdl.core import launch_mapdl
    mapdl = launch_mapdl(exec_file=EXEC_FILE, jobname=JOBNAME, run_location=str(DESKTOP), nproc=1, port=MAPDL_PORT, override=True)
    try:
        mapdl.resume(DB_FILE.stem, "db")
        if not _check_bounds_from_instruction(mapdl):
            print('FAIL: bounds')
            return False
        mapdl.post1()
        mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip('.'))
        try:
            mapdl.set('LAST')
        except Exception:
            mapdl.set(1,1)

        center = node_at(mapdl, x=0.0, y=1.0)
        pred = {
            'center_top_uy_mm': float(mapdl.get_value('NODE', center, 'U', 'Y')),
            'max_seqv_mpa': sort_max(mapdl, 'S', 'EQV'),
            'clamped_reaction_fy_n': reaction_fy_on_x(mapdl, x=50.0),
        }
        print('pred', pred)

        for key, val in pred.items():
            x=float(val)
            lk=key.lower()
            if "temp" in lk and not (-1000.0 <= x <= 5000.0):
                print('FAIL temp',key,x); return False
            if "freq" in lk and not (x > 0.0):
                print('FAIL freq',key,x); return False
            if "reaction" in lk and abs(x) < 1e-9:
                print('FAIL reaction',key,x); return False
            if ("uy" in lk or "uz" in lk or "ux" in lk or "rot" in lk) and not (-1e6 <= x <= 1e6):
                print('FAIL disp',key,x); return False
            if ("von_mises" in lk or "seqv" in lk or "stress" in lk) and abs(x) < 1e-9:
                print('FAIL stress',key,x); return False
            if "final_time" in lk and not (x > 0.0):
                print('FAIL time',key,x); return False
        print('PASS')
        return True
    except Exception as e:
        print('EXC',repr(e))
        traceback.print_exc()
        return False
    finally:
        try: mapdl.exit()
        except Exception: pass

print('True' if evaluate() else 'False')
