"""EdgeWay yerel saglik motoru — tek hesap noktasi.

Portal (/api/health) ve bulut nabzi ayni ciktidan beslenir.
Internet gerekmez; gecmis cihazda durur, "sessiz bosluk oldu mu" offline cevaplanir.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from edgeway import config

HEALTH_FILE = config.DATA_DIR / "health.json"
HISTORY_FILE = config.DATA_DIR / "health_history.jsonl"
HISTORY_SECONDS = 24 * 3600
REC_AGE_WARN_S = 180
REC_AGE_CRIT_S = 600
DISK_WARN_PCT = 85.0
DISK_CRIT_PCT = 93.0
TEMP_WARN_C = 75.0
TEMP_CRIT_C = 82.0
WATCHED_UNITS = ("edgeway-recorder", "edgeway-api", "mediamtx")
RANK = {"OK": 0, "WARN": 1, "CRIT": 2}
GRACE_S = 150          # acilistan sonra ilk segment icin tolerans
START_TS = time.time()  # modul import ani = servis acilis ani


def hw_id() -> str:
    """Donanim kimligi — QR/urun kodu eslestirmesinin capasi, degismez."""
    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.lower().startswith("serial"):
                    return line.split(":")[1].strip()
    except Exception:
        pass
    return "unknown"


def cpu_temp() -> float | None:
    try:
        out = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True,
                             text=True, timeout=2).stdout
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as fh:
                return int(fh.read()) / 1000
        except Exception:
            return None


def _disk_pct() -> float | None:
    try:
        d = shutil.disk_usage(config.DATA_DIR)
        return round(d.used / d.total * 100, 1)
    except Exception:
        return None


def _mem_pct() -> float | None:
    try:
        total = avail = 0
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal"):
                    total = int(line.split()[1])
                elif line.startswith("MemAvailable"):
                    avail = int(line.split()[1])
        return round((1 - avail / total) * 100, 1) if total else None
    except Exception:
        return None


def _newest_mtime(base: Path) -> float:
    """Yalnizca en yeni iki gun klasorunu tarar; maliyet arsiv buyudukce sabit kalir."""
    if not base.exists():
        return 0.0
    try:
        days = sorted((p for p in base.iterdir() if p.is_dir()),
                      key=lambda p: p.name, reverse=True)
    except Exception:
        return 0.0
    for day in days[:2]:
        newest = 0.0
        try:
            files = day.glob("*.mp4")
        except Exception:
            continue
        for f in files:
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if m > newest:
                newest = m
        if newest:
            return newest
    return 0.0


def _service_states() -> dict:
    out = {}
    for unit in WATCHED_UNITS:
        try:
            r = subprocess.run(["systemctl", "is-active", unit],
                               capture_output=True, text=True, timeout=5)
            out[unit] = r.stdout.strip() or "unknown"
        except Exception:
            out[unit] = "unknown"
    return out


def _uptime_s() -> int | None:
    """UPTIME-v1: cihazin kesintisiz calisma suresi.

    3 Eylul dersi: nabiz buluta ulasmadi, bekci 20 saat DOWN gosterdi, oysa
    cihaz sagliktiydi. Teslimat arizasi ile cihaz arizasini ayirmak icin
    bekcinin uptime'a bakmasi yeterli: nabiz gelmeyen aralikta uptime artmaya
    devam etmisse cihaz ayaktaydi.
    """
    try:
        with open("/proc/uptime") as fh:
            return int(float(fh.read().split()[0]))
    except (OSError, ValueError, IndexError):
        return None


def _boot_id() -> str:
    """Her acilista degisir. Degismediyse cihaz yeniden baslamamistir."""
    try:
        return open("/proc/sys/kernel/random/boot_id").read().strip()[:8]
    except OSError:
        return ""


DVR_HOST = os.environ.get("EDGEWAY_DVR_HOST", "192.168.0.4")
DVR_PORT = int(os.environ.get("EDGEWAY_DVR_PORT", "554"))
MEDIAMTX_API = os.environ.get("EDGEWAY_MEDIAMTX_API", "http://127.0.0.1:9997")

_PREV_BYTES: dict = {}


def _cam_adi(ad: str) -> bool:
    return ad.startswith("cam") and ad[3:].isdigit()


def _mediamtx_paths() -> list:
    import urllib.request
    url = MEDIAMTX_API + "/v3/paths/list?itemsPerPage=1000"
    with urllib.request.urlopen(url, timeout=3) as r:
        return json.load(r).get("items", [])


def _dvr_sessions(host: str):
    try:
        r = subprocess.run(["ss", "-tn", "state", "established", "dst", host],
                           capture_output=True, text=True, timeout=5)
        return len([s for s in r.stdout.splitlines()[1:] if s.strip()])
    except Exception:
        return None


def _dvr_reachable(host: str, port: int) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _dvr_block() -> dict:
    """DVR-v1: DVR'a bagli tek cihaz RPi oldugundan DVR telemetrisi buradan cikar.

    paths_ready icin MediaMTX'in `ready` alanina guvenilmez (21 Agu dersi:
    ready kaynak varligi degildir). Olcut bytesReceived'in iki ornek arasinda
    artmasi. Ilk cagrida onceki ornek yoktur, o turda ready + bytesReceived>0
    kullanilir.
    """
    simdi = time.time()
    blok = {
        "src": "rpi-mediamtx",
        "paths_total": None,
        "paths_ready": None,
        "dvr_sessions": _dvr_sessions(DVR_HOST),
        "down_cams": [],
        "dvr_reachable": _dvr_reachable(DVR_HOST, DVR_PORT),
    }
    try:
        items = _mediamtx_paths()
    except Exception:
        return blok

    cams = [p for p in items if _cam_adi(p.get("name", ""))]
    blok["paths_total"] = len(cams)

    akan, duran = [], []
    for p in cams:
        ad = p["name"]
        rb = p.get("bytesReceived")
        onceki = _PREV_BYTES.get(ad)
        _PREV_BYTES[ad] = (simdi, rb)
        akiyor = False
        if p.get("source"):
            if onceki and rb is not None and onceki[1] is not None:
                akiyor = rb > onceki[1]
            else:
                akiyor = bool(p.get("ready")) and bool(rb)
        (akan if akiyor else duran).append(ad)

    blok["paths_ready"] = len(akan)
    blok["down_cams"] = sorted(duran, key=lambda s: int(s[3:]))
    return blok


def snapshot() -> dict:
    """Anlik saglik tablosu. Durum: OK / WARN / CRIT, her biri gerekceli."""
    now = time.time()
    rec_age = {}
    for cam in config.cameras():
        m = _newest_mtime(config.REC_DIR / cam)
        rec_age[cam] = int(now - m) if m else None

    state = {"status": "OK"}
    reasons = []

    def bump(level: str, reason: str) -> None:
        reasons.append(f"{level}: {reason}")
        if RANK[level] > RANK[state["status"]]:
            state["status"] = level

    for cam, age in sorted(rec_age.items()):
        if age is None:
            if now - START_TS < GRACE_S:
                bump("WARN", f"{cam} ilk segment bekleniyor")
            else:
                bump("CRIT", f"{cam} hic kayit yok")
        elif age > REC_AGE_CRIT_S:
            bump("CRIT", f"{cam} kayit {age}sn once")
        elif age > REC_AGE_WARN_S:
            bump("WARN", f"{cam} kayit {age}sn once")

    disk = _disk_pct()
    if disk is not None:
        if disk >= DISK_CRIT_PCT:
            bump("CRIT", f"disk yuzde {disk}")
        elif disk >= DISK_WARN_PCT:
            bump("WARN", f"disk yuzde {disk}")

    temp = cpu_temp()
    if temp is not None:
        if temp >= TEMP_CRIT_C:
            bump("CRIT", f"sicaklik {temp}C")
        elif temp >= TEMP_WARN_C:
            bump("WARN", f"sicaklik {temp}C")

    services = _service_states()

    kayit_acik = bool(config.cameras())
    if not kayit_acik and "edgeway-recorder" in services:
        services["edgeway-recorder"] = "disabled"

    for unit, st in services.items():
        if st in ("active", "unknown", "disabled"):
            continue
        bump("CRIT", f"{unit} {st}")

    dvr = _dvr_block()

    roles = []
    if (dvr.get("paths_total") or 0) > 0:
        roles.append("dvr_source")
    if kayit_acik:
        roles.append("recorder")

    return {
        "hw_id": hw_id(),
        "site_id": config.SITE_ID,
        "device_id": config.DEVICE_ID,
        "ts": int(now),
        "uptime_s": _uptime_s(),
        "boot_id": _boot_id(),
        "status": state["status"],
        "reasons": reasons,
        "rec_age_s": rec_age,
        "disk_used_pct": disk,
        "mem_used_pct": _mem_pct(),
        "temp_c": temp,
        "load1": round(os.getloadavg()[0], 2),
        "services": services,
        "roles": roles,
        "dvr": dvr,
    }


def _prune_history(now_ts: int) -> None:
    if not HISTORY_FILE.exists():
        return
    cutoff = now_ts - HISTORY_SECONDS
    total = 0
    kept = []
    with open(HISTORY_FILE) as fh:
        for line in fh:
            total += 1
            try:
                if json.loads(line).get("ts", 0) >= cutoff:
                    kept.append(line)
            except Exception:
                continue
    if len(kept) != total:
        tmp = Path(str(HISTORY_FILE) + ".tmp")
        tmp.write_text("".join(kept))
        os.replace(tmp, HISTORY_FILE)


def persist(snap: dict) -> None:
    """health.json atomik yazilir, gecmise tek satir eklenir, 24s disi budanir."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(HEALTH_FILE) + ".tmp")
    tmp.write_text(json.dumps(snap))
    os.replace(tmp, HEALTH_FILE)
    line = json.dumps({"ts": snap["ts"], "status": snap["status"],
                       "rec_age_s": snap["rec_age_s"],
                       "disk_used_pct": snap["disk_used_pct"]})
    with open(HISTORY_FILE, "a") as fh:
        fh.write(line + "\n")
    _prune_history(snap["ts"])


def read_health() -> dict:
    """Son yazilan tablo; yoksa taze hesaplar. Portal ucu bunu okur."""
    try:
        return json.loads(HEALTH_FILE.read_text())
    except Exception:
        return snapshot()


def last24h() -> dict:
    """Gecmis ozeti: ornek sayilari ve kesintisiz CRIT bloklari (sessiz bosluklar)."""
    if not HISTORY_FILE.exists():
        return {"samples": 0, "ok": 0, "warn": 0, "crit": 0, "gaps": []}
    counts = {"OK": 0, "WARN": 0, "CRIT": 0}
    gaps = []
    open_gap = None
    prev_ts = None
    with open(HISTORY_FILE) as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            st = rec.get("status", "OK")
            counts[st] = counts.get(st, 0) + 1
            ts = rec.get("ts", 0)
            if st == "CRIT":
                if open_gap is None:
                    open_gap = ts
            elif open_gap is not None:
                gaps.append({"from": open_gap, "to": prev_ts or ts})
                open_gap = None
            prev_ts = ts
    if open_gap is not None:
        gaps.append({"from": open_gap, "to": prev_ts})
    return {"samples": sum(counts.values()), "ok": counts.get("OK", 0),
            "warn": counts.get("WARN", 0), "crit": counts.get("CRIT", 0),
            "gaps": gaps}
