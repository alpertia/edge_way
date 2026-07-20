"""EdgeWay yukleyici: bitmis segmentleri S3'e gonderir (SSE-S3/KMS sunucu tarafi sifreleme).
Basari isareti: <dosya>.up sidecar. Internet yoksa sessizce bekler, donunce kaldigi yerden devam.
Lifecycle (S3 -> Glacier IR -> Deep Archive) bucket policy'de: infra/s3_lifecycle.json
Not: sidecar MVP cozumu; sqlite indekse gecis TODO(docs/ARCHITECTURE.md#uploader).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from edgeway import config

MIN_AGE_SECONDS = 90  # ffmpeg segmenti kapatmis olsun


def pending_segments() -> list[Path]:
    if not config.REC_DIR.exists():
        return []
    now = time.time()
    out = []
    for f in config.REC_DIR.rglob("*.mp4"):
        if f.with_suffix(f.suffix + ".up").exists():
            continue
        if now - f.stat().st_mtime < MIN_AGE_SECONDS:
            continue
        out.append(f)
    return sorted(out)


def s3_key(f: Path) -> str:
    rel = f.relative_to(config.REC_DIR)  # cam/YYYYMMDD/HHMMSS.mp4
    return f"{config.S3_PREFIX}/{rel.as_posix()}"


def run_once() -> int:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    if not config.S3_BUCKET:
        print("[uploader] EDGEWAY_S3_BUCKET bos — cikiliyor", file=sys.stderr)
        return 1
    s3 = boto3.client("s3", region_name=config.AWS_REGION)
    ok = fail = 0
    for f in pending_segments():
        try:
            s3.upload_file(str(f), config.S3_BUCKET, s3_key(f),
                           ExtraArgs={"ServerSideEncryption": "AES256",
                                      "StorageClass": "STANDARD"})
            f.with_suffix(f.suffix + ".up").touch()
            ok += 1
        except (BotoCoreError, ClientError, OSError) as e:
            fail += 1
            print(f"[uploader] hata {f.name}: {type(e).__name__}", file=sys.stderr)
            break  # baglanti sorunuysa listeyi ogutme; sonraki turda dene
    if ok or fail:
        print(f"[uploader] yuklendi={ok} hata={fail}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(run_once())
