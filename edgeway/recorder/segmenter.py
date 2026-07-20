"""EdgeWay kayitci: her kamera icin RTSP -> 60sn mp4 segment (transcode yok, -c copy).
Dizin: REC_DIR/<cam>/<YYYYMMDD>/<HHMMSS>.mp4
ffmpeg dusesse backoff ile yeniden baslatir. SIGTERM ile temiz kapanir.
"""
from __future__ import annotations

import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

from edgeway import config

RUN = True


def ffmpeg_cmd(cam: str, url: str) -> list[str]:
    out = config.REC_DIR / cam / "%Y%m%d" / "%H%M%S.mp4"
    return [
        "ffmpeg", "-nostdin", "-loglevel", "warning",
        "-rtsp_transport", "tcp", "-i", url,
        "-c", "copy", "-map", "0",
        "-f", "segment", "-segment_time", str(config.SEGMENT_SECONDS),
        "-segment_atclocktime", "1", "-reset_timestamps", "1",
        "-strftime", "1", str(out),
    ]


def record_loop(cam: str, url: str) -> None:
    backoff = 2
    while RUN:
        # strftime dizinleri ffmpeg acmaz; gunluk dizini garanti et
        (config.REC_DIR / cam / datetime.now().strftime("%Y%m%d")).mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        proc = subprocess.Popen(ffmpeg_cmd(cam, url))
        while RUN and proc.poll() is None:
            time.sleep(1)
            # gun donumu: yeni gun dizinini onceden ac
            (config.REC_DIR / cam / datetime.now().strftime("%Y%m%d")).mkdir(parents=True, exist_ok=True)
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
            break
        ran = time.time() - t0
        backoff = 2 if ran > 60 else min(backoff * 2, 60)
        print(f"[recorder] {cam} ffmpeg cikti (kod={proc.returncode}), {backoff}sn sonra tekrar", file=sys.stderr)
        time.sleep(backoff)


def retention_loop() -> None:
    while RUN:
        cutoff = datetime.now() - timedelta(days=config.RETENTION_DAYS)
        for cam_dir in config.REC_DIR.iterdir() if config.REC_DIR.exists() else []:
            for day_dir in sorted(p for p in cam_dir.iterdir() if p.is_dir()):
                too_old = day_dir.name < cutoff.strftime("%Y%m%d")
                disk = shutil.disk_usage(config.REC_DIR)
                disk_full = disk.used / disk.total * 100 > config.DISK_MAX_PERCENT
                if too_old or disk_full:
                    print(f"[retention] siliniyor: {day_dir} (old={too_old} full={disk_full})", file=sys.stderr)
                    shutil.rmtree(day_dir, ignore_errors=True)
                if not disk_full and not too_old:
                    break  # gunler sirali; ilk taze gunde dur
        for _ in range(600):
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
