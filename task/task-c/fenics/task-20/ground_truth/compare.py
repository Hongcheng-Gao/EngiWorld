from pathlib import Path
import json


ROOT = Path(__file__).resolve().parent


def load(job):
    xdmf = ROOT / (job + ".xdmf")
    if not xdmf.is_file() or xdmf.stat().st_size == 0:
        raise RuntimeError("Missing XDMF output: " + str(xdmf))
    return json.loads((ROOT / (job + "_metrics.json")).read_text(encoding="utf-8"))


def main():
    job_a = load("job_a")
    job_b = load("job_b")
    mises_ratio = job_b["max_mises_mpa"] / job_a["max_mises_mpa"]
    displacement_ratio = job_b["tip_uy_mm"] / job_a["tip_uy_mm"]
    rows = [
        "job_a,{:.12g},{:.12g}".format(job_a["max_mises_mpa"], job_a["tip_uy_mm"]),
        "job_b,{:.12g},{:.12g}".format(job_b["max_mises_mpa"], job_b["tip_uy_mm"]),
        "Ratio_Mises,{:.12g}".format(mises_ratio),
        "Ratio_Displacement,{:.12g}".format(displacement_ratio),
    ]
    (ROOT / "comparison_report.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
