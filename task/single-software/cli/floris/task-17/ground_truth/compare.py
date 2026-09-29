from pathlib import Path

if __name__ == "__main__":
    btot, bdown = [float(x) for x in Path("baseline.csv").read_text(encoding="utf-8").strip().split(",")]
    ytot, ydown = [float(x) for x in Path("yaw.csv").read_text(encoding="utf-8").strip().split(",")]
    gtot = (ytot - btot) / max(abs(btot), 1e-9) * 100.0
    gdown = (ydown - bdown) / max(abs(bdown), 1e-9) * 100.0
    lines = [
        f"baseline,{btot:.6f},{bdown:.6f}",
        f"yaw,{ytot:.6f},{ydown:.6f}",
        f"Gain_Total_Percent,{gtot:.6f}",
        f"Gain_Downstream_Percent,{gdown:.6f}",
    ]
    Path("comparison_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
