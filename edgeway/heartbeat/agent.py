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
from edgeway.health import engine as health_engine  # CONTRACT-v1


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
    """CONTRACT-v1 §3 tam govde — motorun ciktisi OLDUGU GIBI gonderilir.

    Eski hali sozlesme semasini degil kendi semasini uretiyordu: hw_id ve
    status yoktu, alici 400 donuyordu. Ayrica kendi cpu_temp/meminfo/
    disk_usage hesabini yapiyordu — §2'nin yasakladigi ikinci hesap noktasi.

    Buraya ALAN EKLENMEZ. Yeni alan gerekiyorsa engine.snapshot() icine
    eklenir; portal, /api/health ve bulut ayni anda gorur.
    """
    snap = health_engine.snapshot()
    snap["product"] = "edgeway"
    snap["cameras"] = list(config.cameras())
    return snap


def _snap_rec_ages() -> dict:
    """rec_age motordan okunur, BURADA HESAPLANMAZ (CONTRACT-v1 §2).

    Eski _rec_ages() kaldirildi: kendi taramasini yapiyordu, olcek
    sinirlamasi yoktu ve engine ile ayrisma riski tasiyordu.
    Motor erisilemezse dongu KIRILMAZ — bos sozluk doner.
    """
    try:
        return health_engine.snapshot().get("rec_age_s", {})
    except Exception as e:
        print(f"[heartbeat] snapshot hatasi: {type(e).__name__}", file=sys.stderr)
        return {}


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
    except urllib.error.HTTPError as e:
        # Durum kodu OLMADAN teshis edilemiyordu (22 Agu: 400 mu 401 mi 404 mu
        # belli degildi, tek satir "HTTPError" yaziyordu).
        body = ""
        try:
            body = e.read().decode()[:200]
        except Exception:
            pass
        print(f"[heartbeat] push hatasi: HTTP {e.code} {body}", file=sys.stderr)
        return False
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
        try:
            m = metrics()
            thermal_action(m.get("temp_c"))
            push(m)
        except Exception as e:
            # §5: nabiz kesilebilir, DONGU KIRILMAZ. Cihaz kaydetmeye devam eder.
            print(f"[heartbeat] dongu hatasi: {type(e).__name__}", file=sys.stderr)
        time.sleep(config.HEARTBEAT_SECONDS)


if __name__ == "__main__":
    main()
