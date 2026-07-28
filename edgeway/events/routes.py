"""CamMind/Orin webhook girisi: POST /api/events -> klip kesimi planla."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from edgeway import config
from edgeway.events.clipper import cut_clip

router = APIRouter()


class EventReq(BaseModel):
    cam: str
    ts: float | str | None = None     # epoch sn, ISO-8601 ya da bos (=simdi)
    type: str = "event"
    pre_s: int | None = None
    post_s: int | None = None


def _parse_ts(ts) -> datetime:
    if ts is None:
        return datetime.now()
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts))
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone().replace(tzinfo=None)


@router.post("/api/events")
def post_event(req: EventReq, authorization: str | None = Header(default=None)) -> dict:
    if config.API_TOKEN and authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(status_code=401, detail="token")
    if req.cam not in config.cameras():
        raise HTTPException(status_code=404, detail="bilinmeyen kamera")
    dt = _parse_ts(req.ts)
    config.EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.EVENTS_DIR / (dt.strftime("%Y%m%d") + ".jsonl"), "a") as f:
        f.write(json.dumps({"cam": req.cam, "ts": dt.isoformat(), "type": req.type,
                            "received": time.time()}) + "\n")
    threading.Thread(target=cut_clip, args=(req.cam, dt),
                     kwargs={"pre": req.pre_s, "post": req.post_s, "tag": req.type},
                     daemon=True).start()
    post = req.post_s if req.post_s is not None else config.CLIP_POST_S
    return {"ok": True, "cam": req.cam, "ts": dt.isoformat(), "clip_eta_s": post + 75}
