"""EdgeWay kayitci: her kamera icin RTSP -> 60sn mp4 segment (transcode yok, -c copy).
Dizin: REC_DIR/<cam>/<YYYYMMDD>/<HHMMSS>.mp4
Retention (segment bazli, en eski once):
  1) RETENTION_DAYS'ten eski gun klasorleri silinir
  2) disk > DISK_MAX_PERCENT veya toplam kayit > MAX_STORAGE_GB ise
     en eski segmentler tek tek silinir (son 5 segment asla silinmez)
"""
from __future__ import annotations

import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from edgeway import config

RUN = True
KEEP_LAST = 5  # aktif yazilan + son segmentler dokunulmaz


def ffmpeg_cmd(cam: str, url: str) -> list[str]:
    out = config.REC_DIR / cam / "%Y%m%d" / "%H%M%S.mp4"
    return [
        "ffmpeg", "-nostdin", "-loglevel", "warning",
        "-rtsp_transport", "tcp", "-i", url,
        "-c", "copy", "-map", "0:v:0", "-an",
        *(config.FFMPEG_EXTRA.split() if config.FFMPEG_EXTRA else []),
        "-f", "segment", "-segment_time", str(config.SEGMENT_SECONDS),
        "-segment_atclocktime", "1", "-reset_timestamps", "1",
        "-strftime", "1", str(out),
    ]


def record_loop(cam: str, url: str) -> None:
    backoff = 2
    while RUN:
        (config.REC_DIR / cam / datetime.now().strftime("%Y%m%d")).mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        proc = subprocess.Popen(ffmpeg_cmd(cam, url))
        while RUN and proc.poll() is None:
            time.sleep(1)
            (config.REC_DIR / cam / datetime.now().strftime("%Y%m%d")).mkdir(parents=True, exist_ok=True)
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
            break
        ran = time.time() - t0
        backoff = 2 if ran > 60 else min(backoff * 2, 60)
        print(f"[recorder] {cam} ffmpeg cikti (kod={proc.returncode}), {backoff}sn sonra tekrar", file=sys.stderr)
        time.sleep(backoff)


# ---------- retention ----------

def _segments_oldest_first() -> list[Path]:
    if not config.REC_DIR.exists():
        return []
    return sorted(config.REC_DIR.rglob("*.mp4"), key=lambda f: f.stat().st_mtime)


def _disk_pct() -> float:
    d = shutil.disk_usage(config.REC_DIR)
    return d.used / d.total * 100


def _total_bytes() -> int:
    return sum(f.stat().st_size for f in config.REC_DIR.rglob("*.mp4"))


def _delete_segment(f: Path) -> None:
    f.with_suffix(f.suffix + ".up").unlink(missing_ok=True)
    f.unlink(missing_ok=True)


def enforce_retention() -> None:
    if not config.REC_DIR.exists():
        return
    # 1) yas siniri: eski gun klasorleri komple
    cutoff = (datetime.now() - timedelta(days=config.RETENTION_DAYS)).strftime("%Y%m%d")
    for cam_dir in [p for p in config.REC_DIR.iterdir() if p.is_dir()]:
        for day_dir in [p for p in cam_dir.iterdir() if p.is_dir()]:
            if day_dir.name < cutoff:
                print(f"[retention] gun siliniyor: {day_dir}", file=sys.stderr)
                shutil.rmtree(day_dir, ignore_errors=True)
    # 2) kapasite siniri: segment bazli, en eski once
    max_bytes = config.MAX_STORAGE_GB * 1_000_000_000 if config.MAX_STORAGE_GB else 0

    def over_limit() -> bool:
        if _disk_pct() > config.DISK_MAX_PERCENT:
            return True
        return bool(max_bytes) and _total_bytes() > max_bytes

    if over_limit():
        segs = _segments_oldest_first()
        deletable = segs[:-KEEP_LAST] if len(segs) > KEEP_LAST else []
        deleted = 0
        for f in deletable:
            if not over_limit():
                break
            _delete_segment(f)
            deleted += 1
        if deleted:
            print(f"[retention] kapasite: {deleted} eski segment silindi", file=sys.stderr)
        if over_limit():
            print("[retention] UYARI: limit hala asili, silinecek eski segment kalmadi", file=sys.stderr)
    # 3) bos gun klasorlerini topla
    for cam_dir in [p for p in config.REC_DIR.iterdir() if p.is_dir()]:
        for day_dir in [p for p in cam_dir.iterdir() if p.is_dir()]:
            if not any(day_dir.iterdir()):
                day_dir.rmdir()


def retention_loop() -> None:
    while RUN:
        try:
            enforce_retention()
        except Exception as e:  # retention asla kaydi durdurmasin
            print(f"[retention] hata: {type(e).__name__}: {e}", file=sys.stderr)
        for _ in range(300):
            if not RUN:
                break
            time.sleep(1)


def main() -> None:
    def stop(*_a):  # noqa: ANN002
        global RUN
        RUN = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    cams = config.cameras()
    if not cams:
        print("[recorder] EDGEWAY_CAMERAS bos — cikiliyor", file=sys.stderr)
        sys.exit(1)
    config.REC_DIR.mkdir(parents=True, exist_ok=True)

    threads = [threading.Thread(target=record_loop, args=(c, u), daemon=True) for c, u in cams.items()]
    threads.append(threading.Thread(target=retention_loop, daemon=True))
    for t in threads:
        t.start()
    while RUN:
        time.sleep(1)


if __name__ == "__main__":
    main()
