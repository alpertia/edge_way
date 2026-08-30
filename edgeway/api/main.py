"""EdgeWay API — kayit listeleme, geri gosterim, canli yayin bilgisi, cihaz durumu.
Calistir: uvicorn edgeway.api.main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import hashlib  # LOGIN-v1
import hmac  # LOGIN-v1
import os  # LOGIN-v1
import shutil
import subprocess
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request  # LOGIN-v1
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from edgeway import config
from edgeway.health import engine as health_engine  # CONTRACT-v1

app = FastAPI(title="EdgeWay Pro2", version="0.2.0")

from edgeway.provision.routes import router as setup_router  # noqa: E402
app.include_router(setup_router)
from edgeway.events.routes import router as events_router  # noqa: E402
app.include_router(events_router)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def auth(authorization: str | None = Header(default=None)) -> None:
    if not config.API_TOKEN:
        return  # dev modu
    if authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


@app.post("/api/login")
async def api_login(req: Request) -> dict:
    """LOGIN-v1 — kullanici adi + sifre karsiliginda API token.

    Duz sifre cihazda SAKLANMAZ; .env'de yalnizca sha256 ozeti var.
    Yanlis denemede 1sn beklenir (kaba kuvvet yavaslatma).
    Kullanici adi ve sifre hatasi AYNI cevabi alir.
    """
    want_u = os.getenv("EDGEWAY_UI_USER", "")
    want_h = os.getenv("EDGEWAY_UI_PASS_SHA256", "")
    if not want_u or not want_h:
        raise HTTPException(status_code=503, detail="giris yapilandirilmamis")

    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="gecersiz istek")

    u = str(body.get("user", ""))
    p = str(body.get("pass", ""))
    ok_u = hmac.compare_digest(u, want_u)
    ok_p = hmac.compare_digest(hashlib.sha256(p.encode()).hexdigest(), want_h)
    if not (ok_u and ok_p):
        time.sleep(1)
        raise HTTPException(status_code=401, detail="kullanici adi veya sifre hatali")

    return {"token": config.API_TOKEN, "site": config.SITE_ID, "device": config.DEVICE_ID}


@app.get("/health")
def health() -> dict:
    """Sade canlilik ucu. Durum HESAPLANMAZ, motordan okunur (CONTRACT-v1 §2)."""
    snap = health_engine.snapshot()
    return {
        "status": snap["status"],
        "site": snap["site_id"],
        "device": snap["device_id"],
        "ts": snap["ts"],
        "temp_c": snap["temp_c"],
        "disk_used_pct": snap["disk_used_pct"],
        "cameras": list(config.cameras()),
    }


@app.get("/api/health", dependencies=[Depends(auth)])
def api_health() -> dict:
    """Tam saglik tablosu — TEK HESAP NOKTASI (CONTRACT-v1 §2).

    Portal ust seridi ve bulut nabzi ayni ciktiyi okur.
    Burada hicbir esik yeniden degerlendirilmez.
    """
    return health_engine.snapshot()


@app.get("/api/cameras", dependencies=[Depends(auth)])
def api_cameras() -> dict:
    """VIEW-CAMS-v1 — kayitlilar + yalnizca-izlenenler.

    recorded=false olanlarda gecmis YOKTUR; portal takvimi bos gorur,
    yalnizca canli oynatir. Bu kasitli: disk darbogazi yuzunden az
    kamera kaydedilir ama cok kamera izlenebilir.
    """
    lp = config.live_paths()
    rec = config.cameras()
    cams = {}
    for name in rec:
        cams[name] = {
            "live_path": lp.get(name, name),
            "recordings": f"/api/recordings/{name}",
            "recorded": True,
        }
    for name in config.view_cameras():
        if name in cams:
            continue
        cams[name] = {
            "live_path": lp.get(name, name),
            "recordings": None,
            "recorded": False,
        }
    return {"cameras": cams}


@app.get("/api/recordings/{cam}", dependencies=[Depends(auth)])
def api_recordings(cam: str, date: str | None = None) -> dict:
    """Lokal segment listesi. date=YYYYMMDD verilmezse gunler listelenir."""
    base = config.REC_DIR / cam
    if not base.exists():
        return {"cam": cam, "days": [], "segments": []}
    if date is None:
        days = sorted(p.name for p in base.iterdir() if p.is_dir())
        return {"cam": cam, "days": days}
    day_dir = base / date
    segs = []
    if day_dir.exists():
        for f in sorted(day_dir.glob("*.mp4")):
            segs.append({
                "file": f.name,
                "url": f"/media/{cam}/{date}/{f.name}",
                "size": f.stat().st_size,
                "uploaded": f.with_suffix(f.suffix + ".up").exists(),
            })
    return {"cam": cam, "date": date, "segments": segs}


@app.get("/media/{cam}/{date}/{name}", dependencies=[Depends(auth)])
def media(cam: str, date: str, name: str) -> FileResponse:
    f = (config.REC_DIR / cam / date / name).resolve()
    if not str(f).startswith(str(config.REC_DIR.resolve())) or not f.exists():
        raise HTTPException(status_code=404)
    return FileResponse(f, media_type="video/mp4")


@app.get("/api/cloud/{cam}", dependencies=[Depends(auth)])
def api_cloud(cam: str, date: str, expires: int = 3600) -> dict:
    """S3'teki segmentler icin presigned URL listesi (soguk katman geri gosterim)."""
    if not config.S3_BUCKET:
        raise HTTPException(status_code=503, detail="S3 yapilandirilmamis")
    import boto3  # lazy: cihazda boto3 yoksa API yine acilir

    s3 = boto3.client("s3", region_name=config.AWS_REGION)
    prefix = f"{config.S3_PREFIX}/{cam}/{date}/"
    resp = s3.list_objects_v2(Bucket=config.S3_BUCKET, Prefix=prefix, MaxKeys=1000)
    out = []
    for obj in resp.get("Contents", []):
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": config.S3_BUCKET, "Key": obj["Key"]},
            ExpiresIn=expires,
        )
        out.append({"key": obj["Key"], "size": obj["Size"],
                    "storage_class": obj.get("StorageClass", "STANDARD"), "url": url})
    return {"cam": cam, "date": date, "objects": out}


@app.get("/api/cloud/{cam}/days", dependencies=[Depends(auth)])
def api_cloud_days(cam: str) -> dict:
    """S3'teki gun klasorleri (soguk katman takvimi)."""
    if not config.S3_BUCKET:
        raise HTTPException(status_code=503, detail="S3 yapilandirilmamis")
    import boto3

    s3 = boto3.client("s3", region_name=config.AWS_REGION)
    prefix = f"{config.S3_PREFIX}/{cam}/"
    resp = s3.list_objects_v2(Bucket=config.S3_BUCKET, Prefix=prefix, Delimiter="/")
    days = sorted(p["Prefix"][len(prefix):].strip("/") for p in resp.get("CommonPrefixes", []))
    return {"cam": cam, "days": days}


@app.get("/api/storage", dependencies=[Depends(auth)])
def api_storage() -> dict:
    """Kayit penceresi ve bulut senkron durumu — kamera basina."""
    out = {}
    for cam in config.cameras():
        base = config.REC_DIR / cam
        files = sorted(base.rglob("*.mp4")) if base.exists() else []
        total = sum(f.stat().st_size for f in files)
        pending = sum(1 for f in files if not f.with_suffix(f.suffix + ".up").exists())
        first = last = None
        if files:
            first = files[0].parent.name + files[0].stem   # YYYYMMDDHHMMSS
            last = files[-1].parent.name + files[-1].stem
        out[cam] = {"segments": len(files), "bytes": total, "first": first,
                    "last": last, "pending_upload": pending,
                    "cloud": bool(config.S3_BUCKET)}
    return {"cameras": out, "max_gb": config.MAX_STORAGE_GB,
            "retention_days": config.RETENTION_DAYS}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """LANDING-v1: kok artik TANITIM sayfasi."""
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/demo", response_class=HTMLResponse)
def demo() -> str:
    """LANDING-v1: portal. Giris ekrani portalin kendi icinde."""
    return (WEB_DIR / "demo.html").read_text(encoding="utf-8")


if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


def _cpu_temp() -> float | None:
    try:
        out = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True,
                             text=True, timeout=2).stdout
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        z = Path("/sys/class/thermal/thermal_zone0/temp")
        try:
            return int(z.read_text()) / 1000
        except Exception:
            return None


@app.get("/api/storage/cost", dependencies=[Depends(auth)])
def api_storage_cost() -> dict:
    """STORAGE-v1: maliyet ve katman ozeti. Onbellek bayatsa yeniden hesaplar."""
    import json as _json
    import time as _time
    from edgeway import storage
    try:
        payload = _json.loads(storage.STATS_FILE.read_text(encoding="utf-8"))
        payload["cache_age_s"] = int(_time.time() - storage.STATS_FILE.stat().st_mtime)
        if payload["cache_age_s"] < 900:
            return payload
    except (OSError, ValueError):
        pass
    return storage.stats()


@app.get("/storage", response_class=HTMLResponse)
def storage_page() -> str:
    """STORAGE-v1: depolama ve maliyet yonetim sayfasi."""
    return (WEB_DIR / "storage.html").read_text(encoding="utf-8")
