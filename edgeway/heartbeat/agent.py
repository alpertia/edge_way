"""EdgeWay nabiz: 15sn'de bir CPU/RAM/disk/sicaklik/kamera durumunu buluta POST eder.
Termal esikler: WARN log, CRIT log+flag, SHUTDOWN kontrollu kapanma (veri korumasi).
Basarisiz push loglanir ama dongu olmez — cihaz bagimsiz calisir.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

from edgeway import config


def cpu_temp() -> float | None:
    try:
        out = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True,
                             text=True, timeout=2).stdout
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        try:
            return int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000
        except Exception:
            return None


def metrics() -> dict:
    load1 = os.getloadavg()[0]
    disk = shutil.disk_usage(config.DATA_DIR) if config.DATA_DIR.exists() else None
    mem_free = mem_total = 0
    for line in open("/proc/meminfo"):
        if line.startswith("MemTotal"):
            mem_total = int(line.split()[1])
        elif line.startswith("MemAvailable"):
            mem_free = int(line.split()[1])
    return {
        "site_id": config.SITE_ID,
        "device_id": config.DEVICE_ID,
        "ts": int(time.time()),
        "temp_c": cpu_temp(),
        "load1": round(load1, 2),
        "mem_used_pct": round((1 - mem_free / mem_total) * 100, 1) if mem_total else None,
        "disk_used_pct": round(disk.used / disk.total * 100, 1) if disk else None,
        "cameras": list(config.cameras()),
    }


def push(payload: dict) -> bool:
    if not config.CLOUD_URL:
        return False
    req = urllib.request.Request(
        config.CLOUD_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {config.CLOUD_TOKEN}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"[heartbeat] push hatasi: {type(e).__name__}", file=sys.stderr)
        return False


def thermal_action(temp: float | None) -> None:
    if temp is None:
        return
    if temp >= config.TEMP_SHUTDOWN:
        print(f"[heartbeat] KRITIK {temp}C >= {config.TEMP_SHUTDOWN} — kontrollu kapanma", file=sys.stderr)
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
    elif temp >= config.TEMP_CRIT:
        print(f"[heartbeat] CRIT sicaklik {temp}C", file=sys.stderr)
    elif temp >= config.TEMP_WARN:
        print(f"[heartbeat] WARN sicaklik {temp}C", file=sys.stderr)


def main() -> None:
    while True:
        m = metrics()
        thermal_action(m["temp_c"])
        push(m)
        time.sleep(config.HEARTBEAT_SECONDS)


if __name__ == "__main__":
    main()
