"""EdgeWay bant kurucu.

Buluttaki segmentlerden dongu icin tek bir dosya uretir. Kaynak S3'tir, cunku
yerel disk kapasite temizligiyle eski saatleri atiyor.

    python -m edgeway.tape_build --cams cam1,cam19 --date 20260830 --start 1925 --minutes 60

Ciktilar: /var/lib/edgeway/tape/<cam>.mp4
Indirilen ham segmentler: /var/lib/edgeway/tape/src/<cam>/  (istenirse silinebilir)

Segmentlerin zaman damgalari bozuk gelebiliyor (kaynaktaki non-monotonic DTS),
o yuzden birlestirmede damgalar yeniden uretiliyor.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from edgeway import config

TAPE_DIR = Path(os.environ.get("EDGEWAY_TAPE_DIR", str(config.DATA_DIR / "tape")))


def s3():
    import boto3
    return boto3.client("s3", region_name=getattr(config, "AWS_REGION", None))


def fetch(cam: str, date: str, start: str, minutes: int) -> list[Path]:
    client = s3()
    prefix = "%s/%s/%s/" % (getattr(config, "S3_PREFIX", "").rstrip("/"), cam, date)
    begin = int(start) * 100
    end = begin + minutes * 100
    out_dir = TAPE_DIR / "src" / cam
    out_dir.mkdir(parents=True, exist_ok=True)

    found: list[Path] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=config.S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []) or []:
            name = obj["Key"].rsplit("/", 1)[-1]
            if not name.endswith(".mp4"):
                continue
            stem = name[:-4]
            if not stem.isdigit() or len(stem) != 6:
                continue
            if not (begin <= int(stem) < end):
                continue
            dest = out_dir / name
            if not dest.exists() or dest.stat().st_size != obj["Size"]:
                client.download_file(config.S3_BUCKET, obj["Key"], str(dest))
            found.append(dest)
    found.sort()
    return found


def concat(cam: str, parts: list[Path]) -> Path:
    TAPE_DIR.mkdir(parents=True, exist_ok=True)
    listing = TAPE_DIR / ("%s.txt" % cam)
    listing.write_text(
        "".join("file '%s'\n" % p.as_posix() for p in parts), encoding="utf-8"
    )
    out = TAPE_DIR / ("%s.mp4" % cam)
    cmd = [
        "ffmpeg", "-y", "-nostdin", "-loglevel", "warning",
        "-fflags", "+genpts",
        "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy", "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-800:], file=sys.stderr)
        raise SystemExit("ffmpeg birlestirme basarisiz: %s" % cam)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="edgeway.tape_build")
    ap.add_argument("--cams", default="cam1,cam19")
    ap.add_argument("--date", required=True, help="YYYYAAGG, ornek 20260830")
    ap.add_argument("--start", required=True, help="SSDD, ornek 1925")
    ap.add_argument("--minutes", type=int, default=60)
    args = ap.parse_args(argv)

    for cam in [c.strip() for c in args.cams.split(",") if c.strip()]:
        parts = fetch(cam, args.date, args.start, args.minutes)
        if not parts:
            print("%s: bu araliktan segment bulunamadi" % cam, file=sys.stderr)
            continue
        out = concat(cam, parts)
        mb = out.stat().st_size / (1024 * 1024)
        print("%s: %d segment -> %s (%.1f MB)" % (cam, len(parts), out, mb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
