"""Saglik motorunu mevcut agaca baglar. Idempotent: iki kez kosmak zararsiz.

Capa bulunamaz veya tekil degilse HIC DEGISIKLIK YAPMADAN durur (kod 1).
Repo kokunden kosturulur: python3 scripts/apply_health.py
"""
from __future__ import annotations

import sys
from pathlib import Path

FAIL = []


def need(path: Path) -> str:
    if not path.exists():
        FAIL.append(f"dosya yok: {path}")
        return ""
    return path.read_text()


def anchor(text: str, needle: str, label: str) -> bool:
    n = text.count(needle)
    if n != 1:
        FAIL.append(f"capa tekil degil ({n} adet): {label}")
        return False
    return True


HEALTH_LOOP = '''def health_loop() -> None:
    while RUN:
        try:
            health_engine.persist(health_engine.snapshot())
        except Exception as e:
            print(f"[health] hata: {type(e).__name__}: {e}", file=sys.stderr)
        for _ in range(60):
            if not RUN:
                break
            time.sleep(1)


'''

VERIFY_ADD = (
    'check edgeway/health/engine.py "def snapshot"     "yerel saglik motoru (tek hesap noktasi)"\n'
    'check edgeway/health/engine.py "def last24h"      "24s saglik gecmisi ve bosluk ozeti"\n'
    'check edgeway/health/engine.py "days\\[:2\\]"        "rec_age taramasi arsivle buyumez"\n'
    'check edgeway/recorder/segmenter.py "health_loop" "saglik gecmisi yaziliyor"\n'
)


def main() -> int:
    root = Path(".")
    seg_path = root / "edgeway" / "recorder" / "segmenter.py"
    ver_path = root / "scripts" / "verify_tree.sh"
    init_path = root / "edgeway" / "health" / "__init__.py"
    eng_path = root / "edgeway" / "health" / "engine.py"

    seg = need(seg_path)
    ver = need(ver_path)
    if not eng_path.exists():
        FAIL.append("engine.py yok — zip dogru yere acilmamis")

    seg_done = "health_loop" in seg
    ver_done = "def snapshot" in ver

    if not seg_done and seg:
        for needle, label in (
            ("from edgeway import config", "segmenter import"),
            ("def retention_loop() -> None:", "retention_loop"),
            ("threads.append(threading.Thread(target=retention_loop, daemon=True))",
             "retention thread kaydi"),
        ):
            anchor(seg, needle, label)

    if not ver_done and ver:
        anchor(ver, '[ $FAIL -eq 0 ] && echo "TUM KAZANIMLAR YERINDE', "verify kuyrugu")

    if FAIL:
        for f in FAIL:
            print("KIRMIZI: " + f)
        print("DEGISIKLIK YAPILMADI")
        return 1

    init_path.parent.mkdir(parents=True, exist_ok=True)
    if not init_path.exists():
        init_path.write_text("")
        print("health/__init__.py olusturuldu")

    if seg_done:
        print("segmenter.py zaten yamali")
    else:
        seg = seg.replace(
            "from edgeway import config",
            "from edgeway import config\nfrom edgeway.health import engine as health_engine")
        seg = seg.replace("def retention_loop() -> None:",
                          HEALTH_LOOP + "def retention_loop() -> None:")
        seg = seg.replace(
            "threads.append(threading.Thread(target=retention_loop, daemon=True))",
            "threads.append(threading.Thread(target=retention_loop, daemon=True))\n"
            "    threads.append(threading.Thread(target=health_loop, daemon=True))")
        seg_path.write_text(seg)
        print("segmenter.py yamalandi")

    if ver_done:
        print("verify_tree.sh zaten yamali")
    else:
        tail = '[ $FAIL -eq 0 ] && echo "TUM KAZANIMLAR YERINDE'
        ver_path.write_text(ver.replace(tail, VERIFY_ADD + tail))
        print("verify_tree.sh yamalandi")

    final = seg_path.read_text()
    i = final.index("def retention_loop")
    if "health_engine.persist" not in final[:i]:
        print("KIRMIZI: health_loop govdesi yerinde degil")
        return 1
    if "target=health_loop" not in final:
        print("KIRMIZI: health_loop thread olarak kaydedilmemis")
        return 1
    print("BAGLANTI OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
