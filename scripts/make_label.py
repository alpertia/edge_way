#!/usr/bin/env python3
"""Uretim etiketi: WiFi QR (kutunun AP'sine baglanma) + seri + AP sifresi.
Kullanim: python3 scripts/make_label.py EW26-0001 [cikti.png]
Gereksinim (Mac): pip3 install qrcode pillow
"""
import secrets
import string
import sys

import qrcode
from PIL import Image, ImageDraw

def ap_password() -> str:
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))

def main() -> None:
    serial = sys.argv[1] if len(sys.argv) > 1 else "EW26-0000"
    out = sys.argv[2] if len(sys.argv) > 2 else f"label_{serial}.png"
    ssid = f"edgeWAY-{serial.split('-')[-1]}"
    pw = ap_password()
    qr = qrcode.make(f"WIFI:T:WPA;S:{ssid};P:{pw};;", box_size=8, border=2)
    label = Image.new("RGB", (560, 340), "white")
    label.paste(qr.resize((260, 260)), (20, 40))
    d = ImageDraw.Draw(label)
    d.text((300, 50), "edgeWAY Pro2", fill="black")
    d.text((300, 90), f"Seri: {serial}", fill="black")
    d.text((300, 130), f"Ag: {ssid}", fill="black")
    d.text((300, 170), f"Sifre: {pw}", fill="black")
    d.text((300, 230), "1. QR'i telefonla okut", fill="gray")
    d.text((300, 255), "2. Acilan sayfada kurulumu yap", fill="gray")
    d.text((20, 310), "kurulum: http://192.168.4.1  ·  destek: ant-soft.uk", fill="gray")
    label.save(out)
    print(f"etiket: {out}  ssid={ssid}  sifre={pw}")

if __name__ == "__main__":
    main()
