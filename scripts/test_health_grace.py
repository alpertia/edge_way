"""Acilis toleransi davranis testi. Izole /tmp altinda kosar.

Repo kokunden: python3 scripts/test_health_grace.py
Beklenen tek satir: TEST YESIL
"""
from __future__ import annotations

import os
import shutil
import sys
import time

SANDBOX = "/tmp/edgeway_gracetest"
shutil.rmtree(SANDBOX, ignore_errors=True)
os.environ["EDGEWAY_DATA_DIR"] = SANDBOX

sys.path.insert(0, os.getcwd())
from edgeway import config  # noqa: E402

config.cameras = lambda: ["cam1", "cam2"]

from edgeway.health import engine  # noqa: E402

engine._disk_pct = lambda: 40.0
engine.cpu_temp = lambda: 55.0
engine._service_states = lambda: {"edgeway-recorder": "active"}

now = time.time()

# cam2 taze kayit yazar, cam1 hic dosya birakmaz (restart aninin birebir taklidi)
d = config.REC_DIR / "cam2" / "20260731"
d.mkdir(parents=True, exist_ok=True)
f = d / "120000.mp4"
f.write_bytes(b"x")
os.utime(f, (now, now))
(config.REC_DIR / "cam1").mkdir(parents=True, exist_ok=True)

# 1) Acilis penceresi icinde: WARN olmali, CRIT degil
engine.START_TS = time.time()
s = engine.snapshot()
assert s["rec_age_s"]["cam1"] is None, "KIRMIZI: cam1 None degil, senaryo kurulmadi"
assert s["status"] == "WARN", f"KIRMIZI: acilis penceresinde WARN degil -> {s['status']} {s['reasons']}"
assert any("ilk segment" in r for r in s["reasons"]), "KIRMIZI: gerekce acilis toleransini soylemiyor"

# 2) Tolerans dolduktan sonra: ayni tablo CRIT olmali
engine.START_TS = time.time() - (engine.GRACE_S + 10)
s2 = engine.snapshot()
assert s2["status"] == "CRIT", "KIRMIZI: tolerans sonrasi CRIT degil — gercek ariza gizlenir"
assert any("hic kayit yok" in r for r in s2["reasons"]), "KIRMIZI: gerekce degismedi"

# 3) Acilis penceresinde bile BAYAT kayit CRIT kalmali (uzun kesinti sonrasi acilis)
engine.START_TS = time.time()
os.utime(f, (now - 700, now - 700))
s3 = engine.snapshot()
assert s3["status"] == "CRIT", "KIRMIZI: bayat kayit tolerans arkasina saklanmis"
assert any("cam2" in r and "sn once" in r for r in s3["reasons"]), "KIRMIZI: bayat gerekcesi yok"

# 4) Her sey saglamsa tolerans hicbir sey bozmaz
os.utime(f, (now, now))
d1 = config.REC_DIR / "cam1" / "20260731"
d1.mkdir(parents=True, exist_ok=True)
f1 = d1 / "120000.mp4"
f1.write_bytes(b"x")
os.utime(f1, (now, now))
assert engine.snapshot()["status"] == "OK", "KIRMIZI: saglam tabloda OK degil"

shutil.rmtree(SANDBOX, ignore_errors=True)
print("TEST YESIL")
