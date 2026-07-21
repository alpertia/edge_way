"""EDGEWAY_CAMERAS'tan mediamtx.yml uretir (canli izleme icin sub stream, on-demand).
Kullanim: python -m edgeway.mediamtx_common.apply [/cikti/yolu.yml]
"""
from __future__ import annotations

import re
import sys

from edgeway import config
from edgeway.mediamtx_common.generator import generate

MASK = re.compile(r"//[^/@\s:]+:[^@\s]+@")


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/edgeway/mediamtx.yml"
    cams = {}
    for name, url in config.cameras().items():
        cams[name] = url.replace("/main/", "/sub/")  # canli = sub, kayit = main
    if not cams:
        print("EDGEWAY_CAMERAS bos", file=sys.stderr)
        sys.exit(1)
    yml = generate(cams, hls_variant="fmp4",
                   version=config.env("EDGEWAY_MEDIAMTX_VERSION", "1.11"),
                   on_demand=True)
    with open(out_path, "w") as f:
        f.write(yml)
    print(f"yazildi: {out_path}")
    for n, u in cams.items():
        print(f"  {n}: {MASK.sub('//***:***@', u)}")


if __name__ == "__main__":
    main()
