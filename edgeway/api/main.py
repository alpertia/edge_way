"""EdgeWay API — kayit listeleme, geri gosterim, canli yayin bilgisi, cihaz durumu.
Calistir: uvicorn edgeway.api.main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from edgeway import config

app = FastAPI(title="EdgeWay Pro2", version="0.2.0")

from edgeway.provision.routes import router as setup_router  # noqa: E402
app.include_router(setup_router)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def auth(authorization: str | None = Header(default=None)) -> None:
    if not config.API_TOKEN:
        return  # dev modu
    if authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/health")
def health() -> dict:
    disk = shutil.disk_usage(config.DATA_DIR) if config.DATA_DIR.exists() else None
    temp = _cpu_temp()
    return {
        "status": "ok",
        "site": config.SITE_ID,
        "device": config.DEVICE_ID,
        "ts": int(time.time()),
        "temp_c": temp,
        "disk_used_pct": round(disk.used / disk.total * 100, 1) if disk else None,
        "cameras": list(config.cameras()),
    }


@app.get("/api/cameras", dependencies=[Depends(auth)])
def api_cameras() -> dict:
    cams = {}
    for name in config.cameras():
        cams[name] = {
            "live_path": config.live_paths().get(name, name),
            "recordings": f"/api/recordings/{name}",
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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


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
