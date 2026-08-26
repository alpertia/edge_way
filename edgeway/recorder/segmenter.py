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
from edgeway.health import engine as health_engine

RUN = True
KEEP_LAST = 5
MASK = __import__("re").compile(r"//[^/@\s:]+:[^@\s]+@")


# LOG-THROTTLE-v1: ayni mesaj penceresi (saniye) ve ozet esigi
_THROTTLE_S = 60
_seen = {}


def _shape(msg: str) -> str:
    """Mesajin degisken kisimlarini soyar; ayni kalip tek anahtara duser.
    'DTS; previous: 123, current: 456' ile 'previous: 789, current: 12'
    ayni satir sayilir."""
    out = []
    for ch in msg:
        out.append("N" if ch.isdigit() else ch)
    s = "".join(out)
    while "NN" in s:
        s = s.replace("NN", "N")
    return s


def _pipe_masked(cam, pipe):
    """LOG-THROTTLE-v1 — tekrar eden ffmpeg satirlarini bastirir.

    Ilk ornek YAZILIR. Ayni kalip 60sn icinde tekrarlarsa sessiz sayilir;
    pencere dolunca "xN kez" ozetiyle bir kez daha yazilir.
    Boylece bilgi kaybolmaz ama journald bogulmaz.
    """
    for line in pipe:
        msg = MASK.sub('//***:***@', line.rstrip())
        key = (cam, _shape(msg))
        now = time.time()
        first, count = _seen.get(key, (0.0, 0))
        if now - first >= _THROTTLE_S:
            if count > 1:
                print(f"[ffmpeg:{cam}] onceki satir x{count} kez ({_THROTTLE_S}sn)", file=sys.stderr)
            print(f"[ffmpeg:{cam}] {msg}", file=sys.stderr)
            _seen[key] = (now, 1)
        else:
            _seen[key] = (first, count + 1)
        if len(_seen) > 500:
            _seen.clear()


def ffmpeg_cmd(cam: str, url: str) -> list[str]:
    out = config.REC_DIR / cam / "%Y%m%d" / "%H%M%S.mp4"
    return [
        "ffmpeg", "-nostdin", "-loglevel", "warning",
        "-rtsp_transport", "tcp", "-i", url,
        "-c", "copy", "-map", "0:v:0", "-an",
        *(config.FFMPEG_EXTRA.split() if config.FFMPEG_EXTRA else []),
        "-f", "segment", "-segment_format_options", "movflags=+faststart",
        "-segment_time", str(config.SEGMENT_SECONDS),
        "-segment_atclocktime", "1", "-reset_timestamps", "1",
        "-strftime", "1", str(out),
    ]


def _newest_age(cam: str) -> float:
    base = config.REC_DIR / cam
    newest = 0.0
    for f in base.rglob("*.mp4"):
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if m > newest:
            newest = m
    # CONTRACT-v1 §3: bos arsivde None. Eskiden 0.0 donuyordu ve
    # 0.0 > 180 asla dogru olmadigi icin stall bekcisi KOR kaliyordu.
    return time.time() - newest if newest else None


def record_loop(cam: str, url: str) -> None:
    backoff = 2
    while RUN:
        (config.REC_DIR / cam / datetime.now().strftime("%Y%m%d")).mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        proc = subprocess.Popen(ffmpeg_cmd(cam, url), stderr=subprocess.PIPE, text=True)
        threading.Thread(target=_pipe_masked, args=(cam, proc.stderr), daemon=True).start()
        last_check = time.time()
        while RUN and proc.poll() is None:
            time.sleep(1)
            (config.REC_DIR / cam / datetime.now().strftime("%Y%m%d")).mkdir(parents=True, exist_ok=True)
            if time.time() - last_check >= 30:
                last_check = time.time()
                _age = _newest_age(cam)
                if time.time() - t0 > 180 and (_age is None or _age > 180):
                    print(f"[recorder] {cam} 180sn segment uretmedi — ffmpeg kesiliyor (stall)", file=sys.stderr)
                    proc.terminate()
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
    pairs = []
    for f in config.REC_DIR.rglob("*.mp4"):
        try:
            pairs.append((f.stat().st_mtime, f))
        except OSError:
            continue
    pairs.sort(key=lambda p: p[0])
    return [f for _, f in pairs]


def _disk_pct() -> float:
    d = shutil.disk_usage(config.REC_DIR)
    return d.used / d.total * 100


def _total_bytes() -> int:
    total = 0
    for f in config.REC_DIR.rglob("*.mp4"):
        try:
            total += f.stat().st_size
        except OSError:
            continue
    return total


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


def _clips_oldest_first() -> list[Path]:
    if not config.CLIPS_DIR.exists():
        return []
    return sorted(config.CLIPS_DIR.rglob("*.mp4"), key=lambda f: f.stat().st_mtime)


def enforce_clips_retention() -> None:
    """Klip tavani: yalnizca buluta cikmis (.up isaretli) klipler, en eski once."""
    max_bytes = int(config.CLIPS_MAX_GB * 1_000_000_000) if config.CLIPS_MAX_GB else 0
    if not max_bytes or not config.CLIPS_DIR.exists():
        return
    clips = _clips_oldest_first()
    total = sum(f.stat().st_size for f in clips)
    if total <= max_bytes:
        return
    deleted = 0
    skipped = 0
    for f in clips:
        if total <= max_bytes:
            break
        up = f.with_suffix(f.suffix + ".up")
        if not up.exists():
            skipped += 1
            continue
        size = f.stat().st_size
        up.unlink(missing_ok=True)
        f.unlink(missing_ok=True)
        total -= size
        deleted += 1
    if deleted:
        print(f"[clips] kapasite: {deleted} eski klip silindi", file=sys.stderr)
    if total > max_bytes:
        print(f"[clips] UYARI: limit asili, buluta cikmamis {skipped} klip korundu", file=sys.stderr)
    for cam_dir in [p for p in config.CLIPS_DIR.iterdir() if p.is_dir()]:
        for day_dir in [p for p in cam_dir.iterdir() if p.is_dir()]:
            if not any(day_dir.iterdir()):
                day_dir.rmdir()


def health_loop() -> None:
    while RUN:
        try:
            health_engine.persist(health_engine.snapshot())
        except Exception as e:
            print(f"[health] hata: {type(e).__name__}: {e}", file=sys.stderr)
        for _ in range(60):
            if not RUN:
                break
            time.sleep(1)


def retention_loop() -> None:
    while RUN:
        try:
            enforce_retention()
        except Exception as e:  # retention asla kaydi durdurmasin
            print(f"[retention] hata: {type(e).__name__}: {e}", file=sys.stderr)
        try:
            enforce_clips_retention()
        except Exception as e:
            print(f"[clips] hata: {type(e).__name__}: {e}", file=sys.stderr)
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
    threads.append(threading.Thread(target=health_loop, daemon=True))
    for t in threads:
        t.start()
    while RUN:
        time.sleep(1)


if __name__ == "__main__":
    main()
