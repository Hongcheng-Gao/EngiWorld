"""Evaluator for kicad-1 (LIB02 -- Symbol-footprint pin consistency audit)."""
from __future__ import annotations
import csv
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from schema import CheckResult, EvalResult

TASK_ID = "kicad-1"
HERE = os.path.dirname(__file__)
INIT = os.path.join(HERE, "init_file")
FP_DIR = os.path.join(INIT, "opamps.pretty")
EXPECTED_MISMATCHES = os.path.join(HERE, "ground_truth", "expected_mismatches.csv")

# Correct SOT-23-5 pin mapping: pin_name -> footprint_pad_number
CORRECT_MAP = {
    "IN-": "1",
    "IN+": "2",
    "V-":  "3",
    "OUT": "4",
    "V+":  "5",
}


def parse_symbol_pins(sym_text: str, sym_name: str) -> list[tuple[str, str]]:
    """Return [(pin_number, pin_name)] for a symbol."""
    sym_start = sym_text.find(f'  (symbol "{sym_name}"\n')
    if sym_start == -1:
        sym_start = sym_text.find(f'  (symbol "{sym_name}" ')
    if sym_start == -1:
        return []

    depth = 0
    end = sym_start
    for i in range(sym_start, len(sym_text)):
        if sym_text[i] == '(':
            depth += 1
        elif sym_text[i] == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    sym_block = sym_text[sym_start:end]

    names = re.findall(r'\(name "([^"]+)"\s*\(effects', sym_block)
    numbers = re.findall(r'\(number "([^"]+)"\s*\(effects', sym_block)
    if names and numbers and len(names) == len(numbers):
        return list(zip(numbers, names))
    return []


def get_all_sym_names(sym_text: str) -> list[str]:
    names = re.findall(r'  \(symbol "([^"]+)"\n', sym_text)
    return [n for n in names if not re.match(r'.+_\d+_\d+$', n)]


def read_expected_mismatches() -> list[dict]:
    with open(EXPECTED_MISMATCHES) as f:
        return list(csv.DictReader(f))


def evaluate(audit_csv_path: str) -> EvalResult:
    r = EvalResult(task_id=TASK_ID, step_file=audit_csv_path)
    if not os.path.exists(audit_csv_path):
        r.error = f"audit.csv not found at {audit_csv_path}"
        return r

    output_dir = os.path.dirname(audit_csv_path)
    sym_path = os.path.join(output_dir, "opamps.kicad_sym")

    # ── Check 1: audit.csv can be parsed ──────────────────────────────────────
    try:
        with open(audit_csv_path) as f:
            audit_rows = list(csv.DictReader(f))
    except Exception as e:
        r.error = f"cannot parse audit.csv: {e}"
        return r

    r.checks.append(CheckResult(
        name="audit_csv_parseable",
        passed=True,
        expected="parseable CSV",
        actual=f"{len(audit_rows)} rows",
    ))

    # ── Check 2: audit.csv has required columns ───────────────────────────────
    required_cols = {"symbol_name", "pin_name", "symbol_pin_number", "footprint_pad_number"}
    if audit_rows:
        actual_cols = set(audit_rows[0].keys())
    else:
        actual_cols = set()
    has_cols = required_cols.issubset(actual_cols)
    r.checks.append(CheckResult(
        name="audit_csv_has_required_columns",
        passed=has_cols,
        expected=sorted(required_cols),
        actual=sorted(actual_cols),
    ))
    if not has_cols:
        return r

    # ── Check 3: audit lists all expected mismatch symbols ────────────────────
    expected = read_expected_mismatches()
    expected_sym_set = {row["symbol_name"] for row in expected}
    audit_sym_set = {row["symbol_name"] for row in audit_rows}
    missing_syms = expected_sym_set - audit_sym_set
    r.checks.append(CheckResult(
        name="audit_identifies_all_mismatch_symbols",
        passed=(len(missing_syms) == 0),
        expected=sorted(expected_sym_set),
        actual=sorted(audit_sym_set & expected_sym_set),
        note=f"missing from audit: {sorted(missing_syms)}",
    ))

    # ── Check 4: audit has no false positives (lists non-mismatch symbols) ────
    correct_syms = set(re.findall(r'  \(symbol "([^"]+)"\n',
                                   open(os.path.join(INIT, "opamps.kicad_sym")).read()))
    correct_syms = {n for n in correct_syms if not re.match(r'.+_\d+_\d+$', n)}
    mismatch_syms = expected_sym_set
    correct_only = correct_syms - mismatch_syms

    false_pos = [row["symbol_name"] for row in audit_rows
                 if row["symbol_name"] in correct_only]
    r.checks.append(CheckResult(
        name="audit_no_false_positives",
        passed=(len(false_pos) == 0),
        expected=0,
        actual=len(false_pos),
        note=f"false positives: {false_pos[:5]}",
    ))

    # ── Check 5: total mismatch count in audit ────────────────────────────────
    r.checks.append(CheckResult(
        name="audit_mismatch_row_count",
        passed=(len(audit_rows) == len(expected)),
        expected=len(expected),
        actual=len(audit_rows),
    ))

    # ── Check 6: corrected .kicad_sym exists ─────────────────────────────────
    r.checks.append(CheckResult(
        name="corrected_sym_file_exists",
        passed=os.path.exists(sym_path),
        expected="opamps.kicad_sym present",
        actual="present" if os.path.exists(sym_path) else "missing",
    ))
    if not os.path.exists(sym_path):
        return r

    try:
        with open(sym_path) as f:
            sym_text = f.read()
    except Exception as e:
        r.error = f"cannot read corrected sym file: {e}"
        return r

    # ── Check 7: symbol count unchanged ──────────────────────────────────────
    sym_names = get_all_sym_names(sym_text)
    r.checks.append(CheckResult(
        name="symbol_count_30",
        passed=(len(sym_names) == 30),
        expected=30,
        actual=len(sym_names),
    ))

    # ── Check 8: previously-mismatch symbols now have correct pin numbers ─────
    fixed_ok = 0
    fix_errors = []
    for sym_name in expected_sym_set:
        pins = parse_symbol_pins(sym_text, sym_name)
        for pnum, pname in pins:
            expected_num = CORRECT_MAP.get(pname)
            if expected_num and pnum != expected_num:
                fix_errors.append(f"{sym_name}.{pname}: still {pnum}")
            elif expected_num and pnum == expected_num:
                fixed_ok += 1

    r.checks.append(CheckResult(
        name="mismatch_symbols_fixed",
        passed=(len(fix_errors) == 0),
        expected="all mismatch pins corrected",
        actual=fix_errors[:5] if fix_errors else "all fixed",
    ))

    # ── Check 9: correct symbols not modified ─────────────────────────────────
    unchanged_ok = 0
    unchanged_errors = []
    for sym_name in list(correct_syms - expected_sym_set)[:10]:  # sample 10
        pins = parse_symbol_pins(sym_text, sym_name)
        for pnum, pname in pins:
            expected_num = CORRECT_MAP.get(pname)
            if expected_num and pnum != expected_num:
                unchanged_errors.append(f"{sym_name}.{pname}: wrongly changed to {pnum}")
            else:
                unchanged_ok += 1
    r.checks.append(CheckResult(
        name="correct_symbols_unchanged",
        passed=(len(unchanged_errors) == 0),
        expected="correct symbols not modified",
        actual=unchanged_errors[:3] if unchanged_errors else f"checked {unchanged_ok} pins ok",
    ))

    return r


def eval_outputs(output_dir: str = ".") -> dict:
    path = os.path.join(output_dir, "audit.csv")
    r = evaluate(path)
    return {
        "task_id": r.task_id, "score": r.score, "passed": r.passed,
        "total": r.total, "error": r.error,
        "checks": [
            {"name": c.name, "passed": c.passed, "expected": c.expected,
             "actual": c.actual, "tolerance": c.tolerance, "note": c.note}
            for c in r.checks
        ],
        "summary": r.summary(),
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "audit.csv"
    print(evaluate(path).summary())

