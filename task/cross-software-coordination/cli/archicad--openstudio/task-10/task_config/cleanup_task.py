import datetime, glob, json, os, shutil, stat, subprocess, time

desktop = r"C:\Users\user\Desktop"
documents = r"C:\Users\user\Documents"
paths = [r"C:\EW10", r"C:\EW10-MATRIX", r"C:\EW10-R2-MATRIX", r"C:\EW10-RERUN", r"C:\ew10_diag"]
for pattern in (r"C:\ew10-debug-*", r"C:\ew10-eplus-*", r"C:\ew10-openstudio-*", r"C:\ew10-ft-*", r"C:\ew10-ac-rerun-*"):
    paths.extend(glob.glob(pattern))
paths.extend(os.path.join(desktop, name) for name in (
    "init.ifc", "stage1.ifc", "stage1.ifc.log", "handoff.json", "native_stage_log.json", "archicad_process_journal.json",
    "result.osm", "in.idf", "workflow.osw", "weather.epw", "flow_report.json",
    "model_summary.csv", "openstudio_simulation_transaction.json",
    "openstudio_postprocess_transaction.json", "run", "eval.py", "multi_metrics.json",
))
paths.extend(os.path.join(documents, name) for name in (
    "ew10-archicad.ps1", "ew10-build.rb", "ew10-post.rb", "ew10-post.py",
    "ew10-run-task.ps1", "ew10-equivalent.rb", "ew10-equivalent-post.rb",
    "ew10-run-equivalent.py", "ew10-openstudio_equivalent.rb",
    "ew10-openstudio_equivalent_post.rb", "ew10-build-negatives.py", "ew10-cleanup.py",
    "ew10-run-matrix.py", "ew10-matrix.stdout.txt", "ew10-matrix.stderr.txt", "ew10-matrix.pid",
    "ew10-ac.stdout.txt", "ew10-ac.stderr.txt", "ew10-eval.stdout.txt", "ew10-eval.stderr.txt", "ew10-eval.pid",
    "ew10-altmeta-eval.stdout.txt", "ew10-altmeta-eval.stderr.txt", "ew10-altmeta-eval.pid",
    "ew10-formal.stdout.txt", "ew10-formal.stderr.txt", "ew10-formal.pid",
    "ew10-altmeta.stdout.txt", "ew10-altmeta.stderr.txt", "ew10-altmeta.pid",
    "ew10-equivalent.stdout.txt", "ew10-equivalent.stderr.txt", "ew10-equivalent.pid",
    "ew10-formal-current.zip", "ew10-r2-formal-default.zip", "ew10-r2-matrix.py",
    "ew10-r2.pid", "ew10-r2.stderr.txt", "ew10-r2.stdout.txt",
    "ew10-r2eval.pid", "ew10-r2eval.stderr.txt", "ew10-r2eval.stdout.txt",
))
removed = []
failures = []

def remove_readonly(function, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    function(path)

for path in paths:
    try:
        if os.path.isdir(path):
            subprocess.run(["attrib", "-R", path, "/S", "/D"], capture_output=True, text=True)
            shutil.rmtree(path, onerror=remove_readonly)
            removed.append(path)
        elif os.path.exists(path):
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)
            removed.append(path)
    except Exception as exc:
        failures.append({"path": path, "error": f"{type(exc).__name__}:{exc}"})
for executable in ("IFCCommandServerApp.exe", "Archicad.exe", "openstudio.exe", "energyplus.exe"):
    subprocess.run(["taskkill", "/F", "/IM", executable], capture_output=True, text=True)
print(json.dumps({"cleanup_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "removed_count": len(removed), "failures": failures}, indent=2))
if failures: raise SystemExit(1)
