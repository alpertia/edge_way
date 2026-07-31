"""Saglik motoru davranis testi. Izole /tmp altinda kosar, cihaz verisine dokunmaz.

Repo kokunden: python3 scripts/test_health.py
Tek satir cikti bekleniyor: TEST YESIL
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

SANDBOX = "/tmp/edgeway_healthtest"
shutil.rmtree(SANDBOX, ignore_errors=True)
os.environ["EDGEWAY_DATA_DIR"] = SANDBOX

sys.path.insert(0, os.getcwd())
from edgeway import config  # noqa: E402

config.cameras = lambda: ["cam1", "cam2"]

from edgeway.health import engine  # noqa: E402

engine._disk_pct = lambda: 40.0
engine.cpu_temp = lambda: 55.0
engine._service_states = lambda: {"edgeway-recorder": "active", "edgeway-api": "active"}

now = time.time()
for cam in ("cam1", "cam2"):
    d = config.REC_DIR / cam / "20260730"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "120000.mp4"
    f.write_bytes(b"x")
    os.utime(f, (now, now))

s_ok = engine.snapshot()
assert s_ok["status"] == "OK", f"KIRMIZI: taze kayitta OK degil -> {s_ok['reasons']}"
assert s_ok["hw_id"], "KIRMIZI: hw_id bos"
assert s_ok["rec_age_s"]["cam1"] is not None, "KIRMIZI: rec_age hesaplanmadi"

stale = config.REC_DIR / "cam2" / "20260730" / "120000.mp4"
os.utime(stale, (now - 700, now - 700))
s_crit = engine.snapshot()
assert s_crit["status"] == "CRIT", "KIRMIZI: bayat kayit CRIT degil"
assert any("cam2" in r for r in s_crit["reasons"]), "KIRMIZI: gerekce cam2 demiyor"
assert not any("cam1" in r for r in s_crit["reasons"]), "KIRMIZI: saglam kamera suclanmis"
assert s_crit["rec_age_s"]["cam1"] < 60, "KIRMIZI: saglam kameranin yasi bozulmus"

os.utime(stale, (now - 300, now - 300))
assert engine.snapshot()["status"] == "WARN", "KIRMIZI: ara esik WARN vermiyor"

engine._service_states = lambda: {"edgeway-recorder": "failed"}
assert engine.snapshot()["status"] == "CRIT", "KIRMIZI: dusmus servis CRIT degil"
engine._service_states = lambda: {"edgeway-recorder": "active"}

engine._disk_pct = lambda: 95.0
assert engine.snapshot()["status"] == "CRIT", "KIRMIZI: dolu disk CRIT degil"
engine._disk_pct = lambda: 40.0

os.utime(stale, (now, now))
engine.persist(engine.snapshot())
engine.persist(s_crit)
engine.persist(engine.snapshot())
written = json.loads(engine.HEALTH_FILE.read_text())
assert written["status"] == "OK", "KIRMIZI: health.json son durumu tasimiyor"
assert engine.read_health()["hw_id"] == written["hw_id"], "KIRMIZI: read_health tutarsiz"

h = engine.last24h()
assert h["samples"] == 3, f"KIRMIZI: gecmis sayimi yanlis -> {h}"
assert h["crit"] == 1, "KIRMIZI: CRIT sayimi yanlis"
assert len(h["gaps"]) == 1, "KIRMIZI: sessiz bosluk yakalanmadi"

with open(engine.HISTORY_FILE, "a") as fh:
    fh.write(json.dumps({"ts": int(now) - 90000, "status": "OK",
                         "rec_age_s": {}, "disk_used_pct": 10}) + "\n")
engine.persist(engine.snapshot())
kept = [json.loads(x) for x in open(engine.HISTORY_FILE)]
assert all(r["ts"] > int(now) - 86400 for r in kept), "KIRMIZI: 24s budama calismadi"
assert len(kept) == 4, f"KIRMIZI: budama fazla satir sildi -> {len(kept)}"

shutil.rmtree(SANDBOX, ignore_errors=True)
print("TEST YESIL")
