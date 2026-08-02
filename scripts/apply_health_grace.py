"""Saglik motoruna acilis toleransi ekler.

Sorun: servis restart'inin hemen ardindan bir kamera henuz ilk segmentini
kapatmamis olabilir -> rec_age None -> CRIT -> her deploy'da bulut bekcisi
bosuna alarm calar (31 Tem: cam1 null, cam2/cam22 10sn).

Cozum: acilistan sonraki ilk GRACE_S saniyede "hic kayit yok" WARN sayilir.
Sure dolunca yine CRIT. Bayat kayit (yas esigi asimi) her zaman CRIT kalir.

Idempotent. Capa tekil degilse HIC DEGISIKLIK YAPMADAN durur (kod 1).
Repo kokunden: python3 scripts/apply_health_grace.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ENG = Path("edgeway/health/engine.py")
VER = Path("scripts/verify_tree.sh")

CONST_ANCHOR = 'RANK = {"OK": 0, "WARN": 1, "CRIT": 2}'
CONST_NEW = (
    'RANK = {"OK": 0, "WARN": 1, "CRIT": 2}\n'
    'GRACE_S = 150          # acilistan sonra ilk segment icin tolerans\n'
    'START_TS = time.time()  # modul import ani = servis acilis ani'
)

OLD_BLOCK = '''        if age is None:
            bump("CRIT", f"{cam} hic kayit yok")'''
NEW_BLOCK = '''        if age is None:
            if now - START_TS < GRACE_S:
                bump("WARN", f"{cam} ilk segment bekleniyor")
            else:
                bump("CRIT", f"{cam} hic kayit yok")'''

VERIFY_ADD = (
    'check edgeway/health/engine.py "GRACE_S"           "acilis toleransi (deploy sonrasi sahte alarm yok)"\n'
)


def main() -> int:
    fail = []
    if not ENG.exists():
        fail.append(f"dosya yok: {ENG}")
    if not VER.exists():
        fail.append(f"dosya yok: {VER}")
    if fail:
        for f in fail:
            print("KIRMIZI: " + f)
        print("DEGISIKLIK YAPILMADI")
        return 1

    eng = ENG.read_text()
    ver = VER.read_text()
    eng_done = "GRACE_S" in eng
    ver_done = "acilis toleransi" in ver

    if not eng_done:
        for needle, label in ((CONST_ANCHOR, "RANK sabiti"), (OLD_BLOCK, "hic kayit yok bloku")):
            n = eng.count(needle)
            if n != 1:
                fail.append(f"capa tekil degil ({n} adet): {label}")
    if not ver_done:
        tail = '[ $FAIL -eq 0 ] && echo "TUM KAZANIMLAR YERINDE'
        if ver.count(tail) != 1:
            fail.append("capa tekil degil: verify kuyrugu")

    if fail:
        for f in fail:
            print("KIRMIZI: " + f)
        print("DEGISIKLIK YAPILMADI")
        return 1

    if eng_done:
        print("engine.py zaten yamali")
    else:
        eng = eng.replace(CONST_ANCHOR, CONST_NEW).replace(OLD_BLOCK, NEW_BLOCK)
        ENG.write_text(eng)
        print("engine.py yamalandi")

    if ver_done:
        print("verify_tree.sh zaten yamali")
    else:
        tail = '[ $FAIL -eq 0 ] && echo "TUM KAZANIMLAR YERINDE'
        VER.write_text(ver.replace(tail, VERIFY_ADD + tail))
        print("verify_tree.sh yamalandi")

    final = ENG.read_text()
    if "ilk segment bekleniyor" not in final or "START_TS = time.time()" not in final:
        print("KIRMIZI: yama govdesi yerinde degil")
        return 1
    print("BAGLANTI OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
