from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


TOOLS = Path(r"D:\orcad\tools\bin")
DBDOCTOR = TOOLS / "dbdoctor.exe"
DBSTAT = TOOLS / "dbstat.exe"
PLCTXT = TOOLS / "plctxt.exe"
A2DXF = TOOLS / "a2dxf.exe"
DXF2A = TOOLS / "dxf2a.exe"
CREATE_DEVICES = TOOLS / "create_devices.exe"
CREATE_SYM = TOOLS / "create_sym.exe"
ALLEGRO_UPREV = TOOLS / "allegro_uprev.exe"
DATE_RE = re.compile(r"[A-Z][a-z]{2} [A-Z][a-z]{2}\s+\d{1,2} \d\d:\d\d:\d\d \d{4}")
PATH_RE = re.compile(r"[A-Za-z]:[/\\][^<>'\"\r\n\t*]+")
DBSTAT_META_RE = re.compile(r'USER="(?P<user>[^"]*)".*VERSION_ID=(?P<version_id>\d+)')
DEVICES_MAP_RE = re.compile(r"^'(?P<logical>.+)' '(?P<filename>.+)';$")


def run_tool(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout_s: int = 180,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
    )
    if check and proc.returncode != 0:
        msg = (
            f"command failed: {' '.join(args)}\n"
            f"exit={proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
        raise RuntimeError(msg)
    return proc


def export_place_text(board: Path, out_txt: Path, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return run_tool([str(PLCTXT), str(board), str(board), str(out_txt)], cwd=cwd)


def import_place_text(
    input_board: Path,
    output_board: Path,
    place_txt: Path,
    *,
    move_existing: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [str(PLCTXT), "-r"]
    if move_existing:
        args.append("-m")
    args.extend([str(input_board), str(output_board), str(place_txt)])
    return run_tool(args, cwd=cwd)


def parse_place_text(path: Path) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("VERSION") or line.startswith("UUNITS"):
            continue
        parts = [p.strip() for p in raw.split("!")]
        if len(parts) < 6:
            continue
        refdes = parts[0]
        mirror = parts[4].lower()
        out[refdes] = {
            "x_mm": float(parts[1]),
            "y_mm": float(parts[2]),
            "rot_deg": float(parts[3]),
            "mirror": mirror if mirror else "",
            "symbol_name": parts[5],
        }
    return out


def rewrite_place_text(
    template: Path,
    updates: dict[str, dict[str, object]],
    out_path: Path,
) -> None:
    out_lines: list[str] = []
    for raw in template.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("VERSION") or line.startswith("UUNITS"):
            out_lines.append(raw.rstrip())
            continue
        parts = [p.strip() for p in raw.split("!")]
        if len(parts) < 6:
            out_lines.append(raw.rstrip())
            continue
        refdes = parts[0]
        if refdes not in updates:
            out_lines.append(raw.rstrip())
            continue
        update = updates[refdes]
        symbol_name = parts[5]
        embedded_layer = parts[6] if len(parts) > 6 else ""
        out_lines.append(
            f"{refdes:<20} ! {float(update['x_mm']):10.3f} ! {float(update['y_mm']):10.3f} ! "
            f"{float(update['rot_deg']):8.3f} ! {str(update.get('mirror', '')):>6} ! "
            f"{symbol_name:<32} ! {embedded_layer}"
        )
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def read_targets_csv(path: Path) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["refdes"]] = {
                "x_mm": float(row["x_mm"]),
                "y_mm": float(row["y_mm"]),
                "rot_deg": float(row["rot_deg"]),
                "mirror": (row.get("mirror") or "").strip().lower(),
            }
    return out


def normalize_text(text: str) -> str:
    text = DATE_RE.sub("<DATE>", text)
    text = PATH_RE.sub(lambda m: Path(m.group(0)).name, text)
    return text.replace("\r\n", "\n").strip()


def run_dbstat(path: Path, *flags: str) -> str:
    proc = run_tool([str(DBSTAT), *flags, str(path)])
    return proc.stdout


def parse_dbstat_meta(text: str) -> dict[str, object]:
    match = DBSTAT_META_RE.search(text)
    if not match:
        raise ValueError(f"unable to parse dbstat metadata from: {text!r}")
    return {
        "user": match.group("user"),
        "version_id": int(match.group("version_id")),
    }


def read_dbstat_meta(path: Path) -> dict[str, object]:
    return parse_dbstat_meta(run_dbstat(path, "-e"))


def run_dbdoctor_islocked(path: Path) -> str:
    proc = run_tool([str(DBDOCTOR), "-islocked", str(path)])
    return proc.stdout


def parse_lock_status(text: str) -> dict[str, str | bool]:
    info: dict[str, str | bool] = {"locked": "Database is locked." in text}
    for raw in text.splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        info[key.strip()] = value.strip()
    return info


def export_dxf(
    map_file: Path,
    out_dxf: Path,
    board: Path,
    *,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [str(A2DXF)]
    if extra_args:
        args.extend(extra_args)
    args.extend([str(map_file), str(out_dxf), str(board)])
    return run_tool(args)


def import_dxf(
    map_file: Path,
    in_dxf: Path,
    out_design: Path,
    *,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [str(DXF2A)]
    if extra_args:
        args.extend(extra_args)
    args.extend([str(map_file), str(in_dxf), str(out_design)])
    return run_tool(args)


def compile_symbol(symbol_kind_flag: str, dra: Path, out_symbol: Path) -> subprocess.CompletedProcess[str]:
    return run_tool([str(CREATE_SYM), symbol_kind_flag, str(dra), str(out_symbol)], cwd=out_symbol.parent)


def dump_devices(board: Path, out_dir: Path) -> subprocess.CompletedProcess[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return run_tool([str(CREATE_DEVICES), "-o", str(out_dir), str(board)], cwd=out_dir)


def parse_devices_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = DEVICES_MAP_RE.match(line)
        if not match:
            raise ValueError(f"unexpected devices.map line: {line}")
        mapping[match.group("logical")] = match.group("filename")
    return mapping


def uprev_tree(target_dir: Path, *, max_depth: int = 1) -> subprocess.CompletedProcess[str]:
    return run_tool([str(ALLEGRO_UPREV), "-b", "-n", str(max_depth), str(target_dir)])
