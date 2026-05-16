from __future__ import annotations

import re
from pathlib import Path

FLOAT_RE = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_measurements(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, value in re.findall(rf"^\s*([A-Za-z0-9_()]+)\s*=\s*({FLOAT_RE})\b", text, re.M):
        out[name] = float(value)
    return out


def parse_task02_loopgain(text: str) -> dict[str, float]:
    fc_m = re.search(rf"f_c\s*=\s*({FLOAT_RE})\s*MHz", text)
    pm_m = re.search(rf"PHASE MARGIN\s*=\s*({FLOAT_RE})\s*deg", text)
    if not fc_m or not pm_m:
        raise ValueError("failed to parse crossover or phase margin")
    return {
        "f_c_Hz": float(fc_m.group(1)) * 1e6,
        "phase_margin_deg": float(pm_m.group(1)),
    }


def parse_task06_dsp(text: str) -> dict[str, float]:
    patterns = {
        "input_1kHz_V": r"1 kHz\s*:\s*(" + FLOAT_RE + r")\s*V\s*\(0 dB reference\)",
        "input_5kHz_V": r"5 kHz\s*:\s*(" + FLOAT_RE + r")\s*V\s*\(-6\.02 dB reference\)",
        "recon_1kHz_V": r"1 kHz\s*:\s*(" + FLOAT_RE + r")\s*V\s*\(-0\.16 dB vs input\)",
        "recon_5kHz_V": r"5 kHz\s*:\s*(" + FLOAT_RE + r")\s*V\s*\(-20\.69 dB vs input\)",
        "atten_5kHz_dB": r"Attenuation of 5 kHz tone:\s*(" + FLOAT_RE + r")\s*dB",
        "atten_1kHz_dB": r"Attenuation of 1 kHz tone:\s*(" + FLOAT_RE + r")\s*dB",
    }
    out: dict[str, float] = {}
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if not m:
            raise ValueError(f"failed to parse {key}")
        out[key] = float(m.group(1))
    return out


def parse_task07_samples(text: str) -> dict[str, object]:
    meas = parse_measurements(text)
    name_map = [
        ("exp_rise", 1e-3, "V_AT_1MS", "VO_1MS"),
        ("constant_3V", 3e-3, "V_AT_3MS", "VO_3MS"),
        ("sine_on_DC", 6e-3, "V_AT_6MS", "VO_6MS"),
        ("pulse_train", 8e-3, "V_AT_8MS", "VO_8MS"),
    ]
    segments = []
    for name, t_sample_s, vin_key, vout_key in name_map:
        if vin_key not in meas or vout_key not in meas:
            raise ValueError(f"missing measurement pair for {name}")
        segments.append(
            {
                "name": name,
                "t_sample_s": t_sample_s,
                "V_in": meas[vin_key],
                "V_out": meas[vout_key],
            }
        )
    return {
        "segments": segments,
        "tau_ms": 0.5,
        "R_ohms": 500.0,
        "C_F": 1e-6,
    }


def parse_task09_family(text: str) -> list[tuple[float, float, float]]:
    rows: list[tuple[float, float, float]] = []
    for t_c, vbb, ic in re.findall(
        rf"^\s*({FLOAT_RE})\s+({FLOAT_RE})\s+({FLOAT_RE})\s*$", text, re.M
    ):
        rows.append((float(t_c), float(vbb), float(ic)))
    if len(rows) < 20:
        raise ValueError("failed to parse nested sweep table")
    return rows


def parse_task11_metrics(text: str) -> dict[str, float]:
    meas = parse_measurements(text)
    return {
        "f0": meas["F0"],
        "Q": meas["Q_VAL"],
        "BW_3dB": meas["BW_3DB"],
    }


def parse_task12_first_gain(text: str) -> dict[str, float]:
    steps = []
    for rf, av in re.findall(rf"RF_VAL\s*=\s*({FLOAT_RE}).*?AV\s*=\s*({FLOAT_RE})", text, re.S):
        steps.append((float(rf), float(av)))
    if not steps:
        raise ValueError("failed to parse RF/AV sweep")
    for rf, av in steps:
        if av >= 20.0:
            return {"Rf_found": rf, "Av_dB": av, "Rg": 1000.0}
    raise ValueError("no step reaches 20 dB")


def parse_task13_mc_summary(text: str) -> dict[str, float]:
    runs = re.search(r"NUMBER OF RUNS\s*:\s*(\d+)", text)
    passing = re.search(r"PASSING RUNS\s*:\s*(\d+)", text)
    yield_m = re.search(rf"YIELD\s*:\s*({FLOAT_RE})", text)
    if not runs or not passing or not yield_m:
        raise ValueError("failed to parse monte carlo summary")
    return {
        "runs": int(runs.group(1)),
        "passing": int(passing.group(1)),
        "yield": float(yield_m.group(1)),
    }


def parse_task14_wcase(text: str) -> dict[str, object]:
    nominal = re.search(rf"BW_3DB\s*=\s*({FLOAT_RE})\s*Hz", text)
    low = re.search(rf"LOW\s+\(MIN BW_3DB\)\s*=\s*({FLOAT_RE})\s*Hz", text)
    high = re.search(rf"HIGH\s+\(MAX BW_3DB\)\s*=\s*({FLOAT_RE})\s*Hz", text)
    tops = re.findall(r"^\s*\d+\.\s+([A-Za-z0-9_]+)\s+\(", text, re.M)
    if not nominal or not low or not high or not tops:
        raise ValueError("failed to parse worst-case summary")
    return {
        "BW_nominal": float(nominal.group(1)),
        "BW_min": float(low.group(1)),
        "BW_max": float(high.group(1)),
        "top_sensitivity": tops,
    }


def parse_task15_temp_vout(text: str) -> list[tuple[int, float]]:
    matches = re.findall(
        rf"TEMPERATURE =\s*({FLOAT_RE})\s*DEG C.*?\(OUT\)\s*({FLOAT_RE})",
        text,
        re.S,
    )
    if not matches:
        raise ValueError("failed to parse temperature sweep")
    return [(int(round(float(t_c))), float(vout)) for t_c, vout in matches]


def parse_task16_fourier(text: str) -> dict[str, object]:
    rows = []
    for n, freq, comp in re.findall(
        rf"^\s*(\d+)\s+({FLOAT_RE})\s+({FLOAT_RE})\s+{FLOAT_RE}\s+{FLOAT_RE}\s+{FLOAT_RE}\s*$",
        text,
        re.M,
    ):
        rows.append((int(n), float(freq), float(comp)))
    thd_m = re.search(rf"TOTAL HARMONIC DISTORTION\s*=\s*({FLOAT_RE})\s*PERCENT", text)
    if len(rows) < 5 or not thd_m:
        raise ValueError("failed to parse fourier output")
    harmonic_rows = [{"n": n, "V": comp} for n, _, comp in rows if 2 <= n <= 5]
    return {
        "THD_percent": float(thd_m.group(1)),
        "fundamental_V": next(comp for n, _, comp in rows if n == 1),
        "harmonics": harmonic_rows,
    }


def parse_task17_optimizer(text: str) -> dict[str, object]:
    status = re.search(r"Status:\s*([A-Z]+)", text)
    iterations = re.search(r"Iterations:\s*(\d+)", text)
    final_v = re.search(rf"Final V_AT_1MS\s*=\s*({FLOAT_RE})\s*V", text)
    r_fb = re.search(rf"R_FB\s*=\s*({FLOAT_RE})", text)
    r_gain = re.search(rf"R_GAIN\s*=\s*({FLOAT_RE})", text)
    if not status or not iterations or not final_v or not r_fb or not r_gain:
        raise ValueError("failed to parse optimizer result")
    return {
        "R_FB": float(r_fb.group(1)),
        "R_GAIN": float(r_gain.group(1)),
        "V_OUT_at_1ms": float(final_v.group(1)),
        "converged": status.group(1).upper() == "CONVERGED",
        "iterations": int(iterations.group(1)),
    }


def parse_task18_sensitivity(text: str) -> list[tuple[str, float, float]]:
    rows = re.findall(
        rf"^\s*([A-Za-z0-9_]+)\s+{FLOAT_RE}\s+({FLOAT_RE})\s+({FLOAT_RE})\s*$",
        text,
        re.M,
    )
    out = [(name, float(sens), float(rel)) for name, sens, rel in rows]
    if len(out) < 6:
        raise ValueError("failed to parse sensitivity table")
    return out


def parse_task19_logic(text: str) -> dict[str, object]:
    meas = parse_measurements(text)
    q_state = re.search(r"Q\s*=\s*(HI|LO)", text)
    qbar_state = re.search(r"QBAR\s*=\s*(HI|LO)", text)
    if "Q_AT_1MS" not in meas or "QBAR_AT_1MS" not in meas or not q_state or not qbar_state:
        raise ValueError("failed to parse mixed-signal states")
    return {
        "t": 1e-3,
        "Q": q_state.group(1),
        "QBAR": qbar_state.group(1),
        "V_Q": meas["Q_AT_1MS"],
        "V_QBAR": meas["QBAR_AT_1MS"],
    }


def parse_task20_diode(text: str) -> dict[str, float]:
    meas = parse_measurements(text)
    diode_v = re.search(rf"V\(D1\)\s*=\s*({FLOAT_RE})\s*V", text)
    if "I_AT_50U" not in meas or "V_AT_50U" not in meas or not diode_v:
        raise ValueError("failed to parse diode operating point")
    return {
        "V_IN_at_50us": meas["V_AT_50U"],
        "V_diode_at_50us": float(diode_v.group(1)),
        "I_diode_at_50us": meas["I_AT_50U"],
    }


def rel_ok(got: float, want: float, rel_tol: float, abs_tol: float = 0.0) -> bool:
    return abs(got - want) <= max(abs(want) * rel_tol, abs_tol)
