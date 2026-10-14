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
{webrtc_extra}"""

PATH_TMPL = """  {name}:
    source: {source}
    sourceOnDemand: {on_demand}
{extra}"""


def generate(cameras: dict[str, str], hls_variant: str = "fmp4",
             version: str = "1.18", webrtc: bool = False,
             on_demand=False, on_demand_timeout: str = "") -> str:
    """cameras: {path_adi: rtsp_url}. URL'lerde sifre MASKED birakip deploy'da env'den doldur."""
    major_minor = tuple(int(x) for x in version.split(".")[:2])
    if major_minor < (1, 15) and hls_variant == "lowLatency":
        hls_variant = "fmp4"  # eski surumde LL-HLS sorunlu
    out = HEADER_COMMON.format(
        hls_variant=hls_variant,
        webrtc="yes" if webrtc else "no",
        webrtc_extra="webrtcAddress: :8889\n" if webrtc else "")
    out += "paths:\n"
    if isinstance(on_demand, bool):
        wanted = set(cameras) if on_demand else set()
    else:
        wanted = set(on_demand)
    for name, src in cameras.items():
        od = name in wanted
        extra = ""
        if od and on_demand_timeout:
            extra = "    sourceOnDemandStartTimeout: " + on_demand_timeout + "\n"
        out += PATH_TMPL.format(name=name, source=src,
                                on_demand="yes" if od else "no", extra=extra)
    return out


def relay_from_broker(broker_host: str, paths: list[str], port: int = 8554) -> dict[str, str]:
    """Site ici broker'dan (Orin gibi) relay ceken cihaz icin kaynak haritasi."""
    return {p: f"rtsp://{broker_host}:{port}/{p}" for p in paths}


def dvr_channels(host: str, user: str, password: str, names: list[str],
                 port: int = 554, suffix: str = "01") -> dict[str, str]:
    """camN -> rtsp://user:pass@host:port/Streaming/Channels/N01 (Hikvision ana akis)."""
    from urllib.parse import quote
    u = quote(user, safe="")
    p = quote(password, safe="")
    out = {}
    for name in names:
        n = name.replace("cam", "", 1)
        out[name] = (f"rtsp://{u}:{p}@{host}:{port}"
                     f"/Streaming/Channels/{n}{suffix}")
    return out


import sys


def expand_cams(spec: str) -> list[str]:
    """1-25 veya 1-12,15,17-25 bicimini cam adlarina cevirir."""
    nums: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            nums.extend(range(int(a), int(b) + 1))
        else:
            nums.append(int(part))
    names: list[str] = []
    for n in nums:
        name = "cam" + str(n)
        if name not in names:
            names.append(name)
    return names


def cli(argv: list[str]) -> int:
    import argparse
    import os
    ap = argparse.ArgumentParser(description="mediamtx.yml uretici")
    ap.add_argument("--broker", help="relay kaynagi, ornek 192.168.0.200")
    ap.add_argument("--dvr", help="DVR host, ornek 192.168.0.4")
    ap.add_argument("--dvr-user", default="admin")
    ap.add_argument("--dvr-suffix", default="01")
    ap.add_argument("--port", type=int, default=0,
                    help="bos birakilirsa broker 8554, dvr 554")
    ap.add_argument("--cams", default="1-25")
    ap.add_argument("--version", default="1.11")
    ap.add_argument("--hls-variant", default="fmp4")
    ap.add_argument("--webrtc", action="store_true")
    ap.add_argument("--always-on", default="",
                    help="sourceOnDemand no olacak yollar, virgulle")
    ap.add_argument("--on-demand-timeout", default="",
                    help="ornek 10s, sadece on-demand yollara yazilir")
    ap.add_argument("--out", default="-")
    a = ap.parse_args(argv)

    if bool(a.broker) == bool(a.dvr):
        sys.stderr.write("DURDU: --broker veya --dvr, ikisinden biri\n")
        return 2

    names = expand_cams(a.cams)
    if not names:
        sys.stderr.write("DURDU: kamera listesi bos\n")
        return 2
    always = {x.strip() for x in a.always_on.split(",") if x.strip()}
    bilinmeyen = always - set(names)
    if bilinmeyen:
        sys.stderr.write("DURDU: always-on listede yok: "
                         + ",".join(sorted(bilinmeyen)) + "\n")
        return 2

    if a.broker:
        cams = relay_from_broker(a.broker, names, port=a.port or 8554)
    else:
        pwd = os.environ.get("EDGEWAY_DVR_PASS", "")
        if not pwd:
            sys.stderr.write("DURDU: EDGEWAY_DVR_PASS bos\n")
            return 2
        cams = dvr_channels(a.dvr, a.dvr_user, pwd, names,
                            port=a.port or 554, suffix=a.dvr_suffix)

    on_demand = {n for n in names if n not in always}
    yml = generate(cams, hls_variant=a.hls_variant, version=a.version,
                   webrtc=a.webrtc, on_demand=on_demand,
                   on_demand_timeout=a.on_demand_timeout)
    if a.out == "-":
        sys.stdout.write(yml)
    else:
        fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(yml)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli(sys.argv[1:]))
