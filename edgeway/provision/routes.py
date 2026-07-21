"""Kurulum sihirbazi (/setup) — QR akisinin web tarafi.
Kutu provision edilmemisse acik; edilmisse API token ister.
Env yazimi root gerektirdigi icin tek-amacli sudo helper kullanilir:
  /usr/local/sbin/edgeway-apply-env  (sudoers.d ile sadece bu komut, sifresiz)
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from edgeway import config

router = APIRouter()
WEB_DIR = Path(__file__).resolve().parents[2] / "web"
APPLY_CMD = config.env("EDGEWAY_APPLY_CMD", "sudo /usr/local/sbin/edgeway-apply-env")
MASK = re.compile(r"//[^/@\s:]+:[^@\s]+@")


def provisioned() -> bool:
    return bool(config.cameras())


def guard(authorization: str | None) -> None:
    if not provisioned():
        return  # ilk kurulum: acik
    if not config.API_TOKEN or authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(status_code=401, detail="kurulum kilitli (token gerekli)")


class DVRReq(BaseModel):
    ip: str
    port: int = 554
    user: str
    password: str
    channel: int = 1
    stream: str = "main"
    path_template: str = "/h264/ch{ch}/{stream}/av_stream"


class ApplyReq(BaseModel):
    site_id: str
    device_id: str
    dvr: DVRReq
    channels: list[int]
    retention_days: int = 90
    max_storage_gb: float = 0
    api_token: str = ""
    alert_phone: str = ""
    alert_email: str = ""


def rtsp_url(d: DVRReq, ch: int, stream: str) -> str:
    path = d.path_template.format(ch=ch, stream=stream)
    return f"rtsp://{d.user}:{d.password}@{d.ip}:{d.port}{path}"


def probe(url: str, timeout: int = 8) -> dict:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-rtsp_transport", "tcp", "-i", url,
             "-show_entries", "stream=codec_name,width,height", "-of", "csv=p=0"],
            capture_output=True, text=True, timeout=timeout,
        )
        if out.returncode == 0 and out.stdout.strip():
            first = out.stdout.strip().splitlines()[0].split(",")
            return {"ok": True, "codec": first[0],
                    "resolution": "x".join(first[1:3]) if len(first) >= 3 else ""}
        return {"ok": False, "error": MASK.sub("//***:***@", out.stderr.strip()[-160:])}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "zaman asimi"}


@router.get("/setup", response_class=HTMLResponse)
def setup_page(authorization: str | None = Header(default=None)) -> str:
    guard(authorization)
    return (WEB_DIR / "setup.html").read_text(encoding="utf-8")


@router.post("/api/setup/test")
def setup_test(req: DVRReq, authorization: str | None = Header(default=None)) -> dict:
    guard(authorization)
    return probe(rtsp_url(req, req.channel, req.stream))


@router.post("/api/setup/discover")
def setup_discover(req: DVRReq, max_channels: int = 16,
                   authorization: str | None = Header(default=None)) -> dict:
    guard(authorization)
    def check(ch: int) -> dict | None:
        r = probe(rtsp_url(req, ch, "sub"), timeout=6)
        return {"channel": ch, **r} if r["ok"] else None
    with ThreadPoolExecutor(max_workers=4) as ex:
        found = [r for r in ex.map(check, range(1, max_channels + 1)) if r]
    return {"channels": found}


@router.post("/api/setup/apply")
def setup_apply(req: ApplyReq, authorization: str | None = Header(default=None)) -> dict:
    guard(authorization)
    if not req.channels:
        raise HTTPException(status_code=422, detail="en az bir kanal sec")
    cams = ",".join(
        f"cam{ch}={rtsp_url(req.dvr, ch, 'main')}" for ch in sorted(set(req.channels))
    )
    lines = [
        f"EDGEWAY_SITE_ID={req.site_id}",
        f"EDGEWAY_DEVICE_ID={req.device_id}",
        "EDGEWAY_DATA_DIR=/var/lib/edgeway",
        "EDGEWAY_SEGMENT_SECONDS=60",
        f"EDGEWAY_RETENTION_DAYS={req.retention_days}",
        "EDGEWAY_DISK_MAX_PERCENT=85",
        f"EDGEWAY_MAX_STORAGE_GB={req.max_storage_gb}",
        f"EDGEWAY_CAMERAS={cams}",
        "EDGEWAY_MEDIAMTX_HLS=http://127.0.0.1:8888",
        "EDGEWAY_API_PORT=8080",
        f"EDGEWAY_API_TOKEN={req.api_token}",
        'EDGEWAY_FFMPEG_EXTRA="-tag:v hvc1"',
        f"EDGEWAY_ALERT_PHONE={req.alert_phone}",
        f"EDGEWAY_ALERT_EMAIL={req.alert_email}",
        "EDGEWAY_HEARTBEAT_SECONDS=15",
        "EDGEWAY_TEMP_WARN=70",
        "EDGEWAY_TEMP_CRIT=78",
        "EDGEWAY_TEMP_SHUTDOWN=82",
    ]
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".env") as f:
        f.write("\n".join(lines) + "\n")
        tmp = f.name
    r = subprocess.run([*APPLY_CMD.split(), tmp], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise HTTPException(status_code=500,
                            detail=MASK.sub("//***:***@", (r.stderr or r.stdout)[-200:]))
    return {"ok": True, "cameras": len(req.channels)}
