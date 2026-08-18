#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
import time


LICENSE_PATHS = (
    r"C:\Program Files\ANSYS Inc\Shared Files\licensing\license_files\ansyslmd.lic",
    r"C:\Program Files\ANSYS Inc\Shared Files\Licensing\license_files\ansyslmd.lic",
    r"C:\Program Files\ANSYS Inc\Shared Files\licensing\ansyslmd.lic",
    r"C:\Program Files\ANSYS Inc\Shared Files\Licensing\ansyslmd.lic",
)
LMGRD = r"C:\Program Files\ANSYS Inc\Shared Files\Licensing\winx64\lmgrd.exe"
LICENSE_LOG = r"C:\Program Files\ANSYS Inc\Shared Files\Licensing\license.log"
LMUTIL_PATHS = (
    r"C:\Program Files\ANSYS Inc\v261\licensingclient\winx64\lmutil.exe",
    r"C:\Program Files\ANSYS Inc\Shared Files\fnp\winx64\lmutil.exe",
)


def run(command, timeout=30):
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return completed.returncode, completed.stdout, completed.stderr
    except Exception as exc:
        return -1, "", str(exc)


def get_mac():
    command = (
        "(Get-NetAdapter | Where-Object {$_.HardwareInterface} | "
        "Select-Object -First 1).MacAddress"
    )
    returncode, stdout, _ = run(
        ["powershell", "-NoProfile", "-Command", command]
    )
    if returncode == 0:
        value = stdout.strip().replace("-", "").replace(":", "").lower()
        if len(value) == 12:
            return value
    return None


def find_existing(paths):
    return next((path for path in paths if os.path.exists(path)), None)


def license_ready():
    lmutil = find_existing(LMUTIL_PATHS)
    if not lmutil:
        return False
    returncode, stdout, _ = run(
        [lmutil, "lmstat", "-c", "1055@localhost", "-f", "ansys"],
        timeout=10,
    )
    upper = stdout.upper()
    return (
        returncode == 0
        and "LICENSE SERVER UP" in upper
        and "USERS OF ANSYS:" in upper
    )


def stop_process(name):
    subprocess.run(
        ["taskkill", "/F", "/IM", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    print("=" * 50)
    print("ANSYS License startup check")
    print("=" * 50)

    license_path = find_existing(LICENSE_PATHS)
    if not license_path:
        print("[ERROR] ANSYS license file was not found")
        return 1

    mac = get_mac()
    if not mac:
        print("[ERROR] Physical network adapter MAC was not found")
        return 1

    with open(license_path, "r", encoding="utf-8", errors="ignore") as stream:
        content = stream.read()
    match = re.search(
        r"^(SERVER\s+\S+\s+)(\S+)(\s+\d+)",
        content,
        flags=re.MULTILINE,
    )
    if not match:
        print("[ERROR] SERVER line was not found in the license file")
        return 1

    old_mac = match.group(2).replace("-", "").replace(":", "").lower()
    if old_mac != mac:
        updated = content[: match.start(2)] + mac + content[match.end(2) :]
        shutil.copy2(license_path, license_path + ".bak")
        temporary = license_path + ".tmp"
        with open(temporary, "w", encoding="utf-8", newline="") as stream:
            stream.write(updated)
        os.replace(temporary, license_path)
        for process_name in ("lmgrd.exe", "ansysli_server.exe", "ansyslmd.exe"):
            stop_process(process_name)
        time.sleep(2)

    if license_ready():
        print("[SUCCESS] License Server is ready")
        return 0

    if not os.path.exists(LMGRD):
        print("[ERROR] lmgrd.exe was not found")
        return 1
    for process_name in ("lmgrd.exe", "ansysli_server.exe", "ansyslmd.exe"):
        stop_process(process_name)
    time.sleep(2)
    subprocess.Popen(
        [LMGRD, "-c", license_path, "-l", LICENSE_LOG],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    for _ in range(40):
        if license_ready():
            print("[SUCCESS] License Server is ready")
            return 0
        time.sleep(1.5)
    print("[ERROR] License Server did not become ready")
    return 1


if __name__ == "__main__":
    sys.exit(main())
