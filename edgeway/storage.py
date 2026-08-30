"""EdgeWay saklama ve maliyet motoru.

Tek ayar kaynagi config/env'dir; bu modul kendi ayar dosyasini TUTMAZ.
Okudugu degerler:

    EDGEWAY_RETENTION        1h 12h 24h 3d 7d 14d 1m 3m 6m 1y 2y
                             bos ise EDGEWAY_RETENTION_DAYS kullanilir
    EDGEWAY_PINNED_PREFIXES  virgullu S3 prefix listesi, varsayilan "pinned/"
    EDGEWAY_UPLOAD_MODE      continuous | events | both  (config.UPLOAD_MODE)

Uc is yapar:

    sweep      Saklama suresini uygular.
    lifecycle  Sureye karsilik gelen S3 yasam dongusu kuralini uretir.
    stats      Panelin okuyacagi JSON'u uretir.

Iki emniyet kurali, ikisi de bilerek:

  1. Buluta yukleme aciksa YALNIZCA ".up" sidecar'i olan, yani buluta
     cikmis segmentler silinir. Yuklenmemis kayda dokunulmaz.
  2. clips/ klasorune hic dokunulmaz. Klip saklamasi
     recorder/segmenter.py icindeki enforce_clips_retention'a aittir;
     ikinci bir motor kurmak celiskiye yol acar.

Silme varsayilan olarak kuru calisir; gercekten silmek icin --apply.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edgeway import config

RETENTION_SECONDS = {
    "1h": 3600,
    "12h": 12 * 3600,
    "24h": 24 * 3600,
    "3d": 3 * 86400,
    "7d": 7 * 86400,
    "14d": 14 * 86400,
    "1m": 30 * 86400,
    "3m": 90 * 86400,
    "6m": 180 * 86400,
    "1y": 365 * 86400,
    "2y": 730 * 86400,
}

PRICE_USD_PER_GB_MONTH = {
    "STANDARD": float(config.env("EDGEWAY_PRICE_STANDARD", "0.0245")),
    "GLACIER_IR": float(config.env("EDGEWAY_PRICE_GLACIER_IR", "0.006")),
    "DEEP_ARCHIVE": float(config.env("EDGEWAY_PRICE_DEEP_ARCHIVE", "0.0018")),
}
PRICE_USD_PER_1000_PUT = float(config.env("EDGEWAY_PRICE_PUT_1000", "0.005"))

GIB = 1024 ** 3
STATS_FILE = config.DATA_DIR / "storage_stats.json"


class StorageError(RuntimeError):
    pass


def retention_key() -> str:
    key = config.env("EDGEWAY_RETENTION", "").strip()
    if key:
        if key not in RETENTION_SECONDS:
            raise StorageError(
                "gecersiz EDGEWAY_RETENTION %r, gecerli degerler: %s"
                % (key, ", ".join(RETENTION_SECONDS))
            )
        return key
    return "%dd" % config.RETENTION_DAYS


def retention_secs() -> int:
    key = retention_key()
    if key in RETENTION_SECONDS:
        return RETENTION_SECONDS[key]
    return int(key.rstrip("d")) * 86400


def retention_days() -> float:
    return retention_secs() / 86400.0


def pinned_prefixes() -> tuple[str, ...]:
    raw = config.env("EDGEWAY_PINNED_PREFIXES", "pinned/")
    return tuple(p.strip() for p in raw.split(",") if p.strip())


def cloud_enabled() -> bool:
    return bool(getattr(config, "S3_BUCKET", "")) and config.UPLOAD_MODE != "off"


def s3_prefix() -> str:
    return getattr(config, "S3_PREFIX", "").rstrip("/") + "/"


def s3_client():
    try:
        import boto3
    except ImportError as exc:
        raise StorageError("boto3 kurulu degil: %s" % exc) from exc
    return boto3.client("s3")


def iter_objects(client, bucket: str, prefix: str):
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []) or []:
            yield obj


def transitions_for(days: float) -> list[dict]:
    """Katman gecisleri.

    Minimum ucretlendirme sureleri yuzunden kisa saklamada katman ZARARLIDIR:
    Glacier IR en az 90, Deep Archive en az 180 gun faturalanir. Esikler bu
    yuzden bilerek yuksek tutulmustur.
    """
    if days < 120:
        return []
    if days < 360:
        return [{"Days": 30, "StorageClass": "GLACIER_IR"}]
    return [
        {"Days": 30, "StorageClass": "GLACIER_IR"},
        {"Days": 180, "StorageClass": "DEEP_ARCHIVE"},
    ]


def tier_for_age(age_days: float, transitions: list[dict]) -> str:
    """Nesnenin bugun hangi katmanda oldugunu yasindan hesaplar.

    Gecisler yasa bagli ve deterministik oldugu icin AWS'ye sormaya gerek yok;
    panel bu hesapla anlik ve bedava calisir.
    """
    tier = "STANDARD"
    for t in sorted(transitions, key=lambda x: x["Days"]):
        if age_days >= t["Days"]:
            tier = t["StorageClass"]
    return tier


def sweep_recordings(seconds: int, apply: bool) -> tuple[int, int, int]:
    root = config.REC_DIR
    if not root.exists():
        print("yerel kayit: klasor yok (%s)" % root, file=sys.stderr)
        return (0, 0, 0)

    require_uploaded = cloud_enabled()
    threshold = time.time() - seconds
    count = 0
    total = 0
    skipped = 0

    for f in root.rglob("*.mp4"):
        try:
            st = f.stat()
        except FileNotFoundError:
            continue
        if st.st_mtime >= threshold:
            continue
        marker = f.with_suffix(f.suffix + ".up")
        if require_uploaded and not marker.exists():
            skipped += 1
            continue
        count += 1
        total += st.st_size
        if apply:
            try:
                f.unlink()
                marker.unlink(missing_ok=True)
            except OSError as exc:
                print("silinemedi %s: %s" % (f, exc), file=sys.stderr)
    return (count, total, skipped)


def cmd_sweep(apply: bool) -> int:
    seconds = retention_secs()
    verb = "silindi" if apply else "silinecek"

    count, total, skipped = sweep_recordings(seconds, apply)
    print("yerel kayit: %d dosya, %.2f GiB %s" % (count, total / GIB, verb))
    if skipped:
        print("yerel kayit: %d dosya buluta cikmadigi icin korundu" % skipped)
    print("olay klipleri: dokunulmadi, enforce_clips_retention yonetiyor")

    if seconds >= 86400:
        print("bulut: saklama 1 gun veya daha uzun, temizligi S3 yasam dongusu yapar")
        return 0
    if not cloud_enabled():
        print("bulut: yukleme kapali, bulut temizligi atlandi")
        return 0

    client = s3_client()
    bucket = config.S3_BUCKET
    prefix = s3_prefix()
    pinned = pinned_prefixes()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    batch: list[dict] = []
    cloud_n = 0
    cloud_bytes = 0

    def flush(items: list[dict]) -> None:
        if not items or not apply:
            return
        resp = client.delete_objects(Bucket=bucket, Delete={"Objects": items, "Quiet": True})
        for err in resp.get("Errors", []) or []:
            print("bulut silinemedi %s: %s" % (err.get("Key"), err.get("Message")), file=sys.stderr)

    for obj in iter_objects(client, bucket, prefix):
        key = obj["Key"]
        if key.startswith(pinned):
            continue
        if obj["LastModified"] >= cutoff:
            continue
        cloud_n += 1
        cloud_bytes += obj["Size"]
        batch.append({"Key": key})
        if len(batch) == 1000:
            flush(batch)
            batch = []
    flush(batch)
    print("bulut: %d nesne, %.2f GiB %s" % (cloud_n, cloud_bytes / GIB, verb))

    if not apply:
        print("kuru calisma. gercekten silmek icin --apply ekleyin")
    return 0


def lifecycle_config() -> dict:
    days = retention_days()
    site_prefix = s3_prefix().split("/")[0] + "/"
    abort = {
        "ID": "edgeway-abort-mpu",
        "Filter": {"Prefix": ""},
        "Status": "Enabled",
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
    }
    if days < 1:
        return {"Rules": [abort]}
    rule = {
        "ID": "edgeway-retention",
        "Filter": {"Prefix": site_prefix},
        "Status": "Enabled",
        "Expiration": {"Days": int(round(days))},
    }
    transitions = transitions_for(days)
    if transitions:
        rule["Transitions"] = transitions
    return {"Rules": [rule, abort]}


def cmd_lifecycle(apply: bool, write: str) -> int:
    cfg = lifecycle_config()
    out = json.dumps(cfg, ensure_ascii=False, indent=2)
    print(out)
    if write:
        Path(write).write_text(out + "\n", encoding="utf-8")
        print("yazildi: %s" % write, file=sys.stderr)
    if not apply:
        print("kuru calisma. uygulamak icin --apply ekleyin", file=sys.stderr)
        return 0
    client = s3_client()
    client.put_bucket_lifecycle_configuration(
        Bucket=config.S3_BUCKET, LifecycleConfiguration=cfg
    )
    print("kural uygulandi: %s" % config.S3_BUCKET, file=sys.stderr)
    return 0


def stats() -> dict:
    now = datetime.now(timezone.utc)
    transitions = transitions_for(retention_days())

    cameras: dict[str, dict] = {}
    tiers: dict[str, dict] = {}
    total_objects = 0
    total_bytes = 0
    oldest = None
    newest = None

    cloud_error = ""
    if cloud_enabled():
        try:
            client = s3_client()
        except StorageError as exc:
            client = None
            cloud_error = str(exc)
    else:
        client = None

    if client is not None:
        prefix = s3_prefix()
        for obj in iter_objects(client, config.S3_BUCKET, prefix):
            size = obj["Size"]
            modified = obj["LastModified"]
            age_days = (now - modified).total_seconds() / 86400.0
            tier = tier_for_age(age_days, transitions)

            rest = obj["Key"][len(prefix):] if obj["Key"].startswith(prefix) else obj["Key"]
            cam = rest.split("/")[0] or "bilinmiyor"

            c = cameras.setdefault(cam, {"objects": 0, "bytes": 0})
            c["objects"] += 1
            c["bytes"] += size

            t = tiers.setdefault(tier, {"objects": 0, "bytes": 0})
            t["objects"] += 1
            t["bytes"] += size

            total_objects += 1
            total_bytes += size
            oldest = modified if oldest is None or modified < oldest else oldest
            newest = modified if newest is None or modified > newest else newest

    storage_usd = 0.0
    for tier, agg in tiers.items():
        gib = agg["bytes"] / GIB
        agg["gib"] = round(gib, 3)
        agg["usd_per_month"] = round(gib * PRICE_USD_PER_GB_MONTH.get(tier, 0.0), 4)
        storage_usd += gib * PRICE_USD_PER_GB_MONTH.get(tier, 0.0)

    span_days = 1.0
    if oldest and newest and newest > oldest:
        span_days = max((newest - oldest).total_seconds() / 86400.0, 1.0)
    request_usd = (total_objects / span_days) * 30.0 / 1000.0 * PRICE_USD_PER_1000_PUT

    for agg in cameras.values():
        agg["gib"] = round(agg["bytes"] / GIB, 3)
        agg["gb_per_day"] = round(agg["bytes"] / GIB / span_days, 2)
        agg["usd_per_month"] = round(
            storage_usd * (agg["bytes"] / total_bytes) if total_bytes else 0.0, 4
        )

    local = {}
    if config.REC_DIR.exists():
        pending = 0
        local_bytes = 0
        local_files = 0
        for f in config.REC_DIR.rglob("*.mp4"):
            try:
                local_bytes += f.stat().st_size
            except FileNotFoundError:
                continue
            local_files += 1
            if not f.with_suffix(f.suffix + ".up").exists():
                pending += 1
        usage = shutil.disk_usage(config.DATA_DIR)
        local = {
            "segments": local_files,
            "bytes": local_bytes,
            "gib": round(local_bytes / GIB, 3),
            "pending_upload": pending,
            "disk_total_bytes": usage.total,
            "disk_used_bytes": usage.used,
            "disk_used_pct": round(usage.used / usage.total * 100.0, 1),
            "rewind_seconds": int(local_files * config.SEGMENT_SECONDS
                                  / max(len(config.cameras()), 1)),
        }

    payload = {
        "generated_at": now.isoformat(),
        "site": config.SITE_ID,
        "device": config.DEVICE_ID,
        "retention": retention_key(),
        "upload_mode": config.UPLOAD_MODE,
        "segment_seconds": config.SEGMENT_SECONDS,
        "cloud": {
            "enabled": cloud_enabled(),
            "error": cloud_error,
            "bucket": getattr(config, "S3_BUCKET", ""),
            "objects": total_objects,
            "bytes": total_bytes,
            "gib": round(total_bytes / GIB, 3),
            "oldest": oldest.isoformat() if oldest else None,
            "newest": newest.isoformat() if newest else None,
        },
        "tiers": tiers,
        "cameras": cameras,
        "cost": {
            "storage_usd_per_month": round(storage_usd, 4),
            "request_usd_per_month": round(request_usd, 4),
            "total_usd_per_month": round(storage_usd + request_usd, 4),
        },
        "local": local,
    }

    try:
        STATS_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        print("istatistik dosyasi yazilamadi: %s" % exc, file=sys.stderr)
    return payload


def cmd_stats(quiet: bool) -> int:
    payload = stats()
    if not quiet:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edgeway.storage")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sweep = sub.add_parser("sweep", help="saklama suresini uygula")
    p_sweep.add_argument("--apply", action="store_true")

    p_life = sub.add_parser("lifecycle", help="S3 yasam dongusu kurali")
    p_life.add_argument("--apply", action="store_true")
    p_life.add_argument("--write", default="", help="kurali bu dosyaya da yaz")

    p_stats = sub.add_parser("stats", help="panel icin JSON uret")
    p_stats.add_argument("--quiet", action="store_true", help="sadece dosyaya yaz")

    args = parser.parse_args(argv)
    try:
        if args.command == "sweep":
            return cmd_sweep(args.apply)
        if args.command == "lifecycle":
            return cmd_lifecycle(args.apply, args.write)
        return cmd_stats(args.quiet)
    except StorageError as exc:
        print("hata: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
