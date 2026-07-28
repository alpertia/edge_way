"""Olay klibi kesici: ring tampondaki segmentlerden [t-pre, t+post] tam kare klip.
Yeniden kodlama yok (-c copy) — keyframe hizasina yaslanir, RPi CPU'su yorulmaz."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

from edgeway import config


def _day_segments(cam: str, day: str) -> list[Path]:
    d = config.REC_DIR / cam / day
    return sorted(d.glob("*.mp4")) if d.exists() else []


def _t(name: str) -> int:
    return int(name[:2]) * 3600 + int(name[2:4]) * 60 + int(name[4:6])


def _covered(cam: str, day: str, need_end: int) -> bool:
    segs = _day_segments(cam, day)
    return bool(segs) and _t(segs[-1].stem) > need_end


def cut_clip(cam: str, event_dt: datetime, pre: int | None = None,
             post: int | None = None, tag: str = "evt", wait: bool = True) -> Path | None:
    pre = config.CLIP_PRE_S if pre is None else pre
    post = config.CLIP_POST_S if post is None else post
    start_dt = event_dt - timedelta(seconds=pre)
    end_dt = event_dt + timedelta(seconds=post)
    if start_dt.date() != end_dt.date():  # MVP: gun sinirinda klip gunun icine kirpilir
        start_dt = datetime.combine(end_dt.date(), datetime.min.time())
    day = end_dt.strftime("%Y%m%d")
    need_end = _t(end_dt.strftime("%H%M%S"))
    deadline = time.time() + post + 95
    while wait and not _covered(cam, day, need_end) and time.time() < deadline:
        time.sleep(5)
    start_t = _t(start_dt.strftime("%H%M%S"))
    use = [f for f in _day_segments(cam, day)
           if _t(f.stem) + 61 > start_t and _t(f.stem) < need_end]
    if not use:
        print(f"[clipper] {cam} {event_dt}: tamponda segment yok (ring disina dusmus olabilir)",
              file=sys.stderr)
        return None
    off = max(0, start_t - _t(use[0].stem))
    out_dir = config.CLIPS_DIR / cam / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{start_dt.strftime('%H%M%S')}_{tag}.mp4"
    last_cut = max(1, need_end - _t(use[-1].stem))
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as lf:
        for i, f in enumerate(use):
            lf.write(f"file '{f}'\n")
            if i == 0 and off > 0.5:
                lf.write(f"inpoint {off}\n")
            if i == len(use) - 1 and last_cut < 61:
                lf.write(f"outpoint {last_cut}\n")
        lst = lf.name
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c", "copy", "-movflags", "+faststart", str(out)],
        capture_output=True, text=True)
    Path(lst).unlink(missing_ok=True)
    if r.returncode != 0 or not out.exists() or out.stat().st_size < 1000:
        print(f"[clipper] {cam} kesim hatasi: {(r.stderr or '')[-160:]}", file=sys.stderr)
        return None
    print(f"[clipper] klip hazir: {out}", file=sys.stderr)
    return out
