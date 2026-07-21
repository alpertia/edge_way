"""EdgeWay merkezi config. Kaynak sirasi: env > /etc/edgeway/edgeway.env > defaults.
Secret'lar asla koda gomulmez; .env.example sablonuna bak.
"""
import os
from pathlib import Path

ENV_FILE = Path(os.environ.get("EDGEWAY_ENV", "/etc/edgeway/edgeway.env"))


def _load_env_file() -> None:
    try:
        _text = ENV_FILE.read_text()
    except OSError:
        return
    for line in _text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_env_file()


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# --- kimlik ---
SITE_ID = env("EDGEWAY_SITE_ID", "site-dev")
DEVICE_ID = env("EDGEWAY_DEVICE_ID", "edgeway-dev")

# --- yollar ---
DATA_DIR = Path(env("EDGEWAY_DATA_DIR", "/var/lib/edgeway"))
REC_DIR = DATA_DIR / "recordings"
QUEUE_DIR = DATA_DIR / "upload_queue"

# --- kayit ---
SEGMENT_SECONDS = int(env("EDGEWAY_SEGMENT_SECONDS", "60"))
RETENTION_DAYS = int(env("EDGEWAY_RETENTION_DAYS", "90"))
DISK_MAX_PERCENT = int(env("EDGEWAY_DISK_MAX_PERCENT", "85"))

# --- kameralar: "cam1=rtsp://...,cam2=rtsp://..." ---
def cameras() -> dict[str, str]:
    raw = env("EDGEWAY_CAMERAS", "")
    out: dict[str, str] = {}
    for part in raw.split(","):
        if "=" in part:
            name, url = part.split("=", 1)
            out[name.strip()] = url.strip()
    return out


# --- mediamtx ---
MEDIAMTX_API = env("EDGEWAY_MEDIAMTX_API", "http://127.0.0.1:9997")
MEDIAMTX_HLS = env("EDGEWAY_MEDIAMTX_HLS", "http://127.0.0.1:8888")

# --- api ---
API_HOST = env("EDGEWAY_API_HOST", "0.0.0.0")
API_PORT = int(env("EDGEWAY_API_PORT", "8080"))
API_TOKEN = env("EDGEWAY_API_TOKEN", "")  # bos = auth kapali (sadece dev)

# --- aws ---
S3_BUCKET = env("EDGEWAY_S3_BUCKET", "")
S3_PREFIX = env("EDGEWAY_S3_PREFIX", f"{SITE_ID}/{DEVICE_ID}")
AWS_REGION = env("AWS_DEFAULT_REGION", "eu-central-1")

# --- bulut (heartbeat hedefi) ---
CLOUD_URL = env("EDGEWAY_CLOUD_URL", "")
CLOUD_TOKEN = env("EDGEWAY_CLOUD_TOKEN", "")
HEARTBEAT_SECONDS = int(env("EDGEWAY_HEARTBEAT_SECONDS", "15"))

# --- termal esikler (watchdog) ---
TEMP_WARN = float(env("EDGEWAY_TEMP_WARN", "70"))
TEMP_CRIT = float(env("EDGEWAY_TEMP_CRIT", "78"))
TEMP_SHUTDOWN = float(env("EDGEWAY_TEMP_SHUTDOWN", "82"))

FFMPEG_EXTRA = env("EDGEWAY_FFMPEG_EXTRA", "")

FFMPEG_EXTRA = env("EDGEWAY_FFMPEG_EXTRA", "")

MAX_STORAGE_GB = float(env("EDGEWAY_MAX_STORAGE_GB", "0"))  # 0 = kapali
