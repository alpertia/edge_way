"""mediamtx.yml uretici — tum Mind'lar ve EdgeWay icin ortak.
Version-aware: v1.11 (rpi pilot) ve v1.18 (orin) arasindaki alan farklarini yonetir.
Kullanim:
    from edgeway.mediamtx_common.generator import generate
    yml = generate(cameras={"cam1": "rtsp://user:MASKED@192.168.0.4:554/h264/ch1/main/av_stream"},
                   hls_variant="fmp4", version="1.18")
"""
from __future__ import annotations

HEADER_COMMON = """logLevel: info
api: yes
apiAddress: 127.0.0.1:9997
rtsp: yes
rtspAddress: :8554
hls: yes
hlsAddress: :8888
hlsVariant: {hls_variant}
hlsSegmentCount: 7
hlsSegmentDuration: 1s
webrtc: {webrtc}
"""

PATH_TMPL = """  {name}:
    source: {source}
    sourceProtocol: tcp
    sourceOnDemand: {on_demand}
"""


def generate(cameras: dict[str, str], hls_variant: str = "fmp4",
             version: str = "1.18", webrtc: bool = False,
             on_demand: bool = False) -> str:
    """cameras: {path_adi: rtsp_url}. URL'lerde sifre MASKED birakip deploy'da env'den doldur."""
    major_minor = tuple(int(x) for x in version.split(".")[:2])
    if major_minor < (1, 15) and hls_variant == "lowLatency":
        hls_variant = "fmp4"  # eski surumde LL-HLS sorunlu
    out = HEADER_COMMON.format(hls_variant=hls_variant, webrtc="yes" if webrtc else "no")
    out += "paths:\n"
    for name, src in cameras.items():
        out += PATH_TMPL.format(name=name, source=src,
                                on_demand="yes" if on_demand else "no")
    return out


def relay_from_broker(broker_host: str, paths: list[str], port: int = 8554) -> dict[str, str]:
    """Site ici broker'dan (Orin gibi) relay ceken cihaz icin kaynak haritasi."""
    return {p: f"rtsp://{broker_host}:{port}/{p}" for p in paths}


if __name__ == "__main__":
    import sys
    cams = relay_from_broker("100.80.20.60", ["cam1"])
    sys.stdout.write(generate(cams, version="1.11"))
