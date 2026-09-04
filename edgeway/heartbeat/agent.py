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


SPOOL = config.DATA_DIR / "heartbeat_spool.jsonl"
SPOOL_MAX = int(config.env("EDGEWAY_HEARTBEAT_SPOOL_MAX", "2880"))
SPOOL_BATCH = 60


def _spool_append(payload: dict) -> None:
    """SPOOL-v1: gonderilemeyen nabiz kaybolmaz, siraya yazilir.

    3 Eylul dersi: cihaz saglikliydi ama nabiz buluta ulasamadi ve bekci
    20 saat DOWN gosterdi. Teslimat arizasi ile cihaz arizasi ayni sonuca
    cikmamali; birikmis nabizlar sonradan gidince gecmis duzeltilir.
    """
    try:
        SPOOL.parent.mkdir(parents=True, exist_ok=True)
        with SPOOL.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        lines = SPOOL.read_text(encoding="utf-8").splitlines()
        if len(lines) > SPOOL_MAX:
            SPOOL.write_text("\n".join(lines[-SPOOL_MAX:]) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"[heartbeat] spool yazilamadi: {type(e).__name__}", file=sys.stderr)


def _spool_drain() -> int:
    """Birikmis nabizlari EN ESKIDEN baslayarak gonderir, turda en fazla
    SPOOL_BATCH tane — dongu uzun surmesin."""
    if not SPOOL.exists():
        return 0
    try:
        lines = [l for l in SPOOL.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return 0
    sent = 0
    for line in lines[:SPOOL_BATCH]:
        try:
            item = json.loads(line)
        except ValueError:
            sent += 1
            continue
        if not push(item):
            break
        sent += 1
    try:
        rest = lines[sent:]
        if rest:
            SPOOL.write_text("\n".join(rest) + "\n", encoding="utf-8")
        else:
            SPOOL.unlink(missing_ok=True)
    except OSError:
        pass
    if sent:
        print(f"[heartbeat] {sent} birikmis nabiz gonderildi, {len(lines) - sent} kaldi",
              file=sys.stderr)
    return sent


def deliver(payload: dict) -> None:
    """Once tampon, sonra guncel nabiz. Basarisizsa guncel de tampona yazilir."""
    _spool_drain()
    if not push(payload):
        _spool_append(payload)


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
            deliver(m)
        except Exception as e:
            # §5: nabiz kesilebilir, DONGU KIRILMAZ. Cihaz kaydetmeye devam eder.
            print(f"[heartbeat] dongu hatasi: {type(e).__name__}", file=sys.stderr)
        time.sleep(config.HEARTBEAT_SECONDS)


if __name__ == "__main__":
    main()
