# CAMM-170 → EdgeWay: RPi saha dönüşü + MediaMTX kaynak geçişi

**Tarih:** 14 Ekim 2026
**Kimden:** CamMind (CAMM-169 saha ağı kurtarma)
**Kime:** EdgeWay projesi (`~/DEV/edge_way`)
**Durum:** CamMind tarafı ✅ (23/23 kamera canlı). EdgeWay RPi ❌ kaynaksız / Tailscale dışı / **düşük voltaj**.
**v2 (11:01):** RPi bulundu → **`192.168.0.43`** (host key eski `100.80.46.1` ile aynı, doğru cihaz). Güç sorunu eklendi (bölüm 0).

---

## 0. ⚠️ GÜÇ — önce bu

RPi3B+ şu an **OPi5'in USB portundan** besleniyor.

```
throttled=0x50005   ← ŞU AN düşük voltaj + ŞU AN throttle (+ geçmişte ikisi de)
volt=1.2000V  load 0.17  uptime 18 dk
```

Boşta (load 0.17) bile düşük voltajda. ffmpeg kaydı + upload altında daha kötü olur → SD bozulması, sessiz kayıt kesintisi, rastgele reboot. EW'nin eski açıklanamayan kesintileri için de aday.

- **Fiziksel düzeltme (sahada):** RPi'ye ayrı **5V / 2.5A** adaptör. OPi5 USB'sinden besleme bırakılacak (OPi5'in kendi bütçesini de zorluyor, OPi5 reboot'u RPi'yi de düşürüyor).
- Adaptör takılana kadar: kayıt/yük artıran yeni iş başlatma; sadece IP/kaynak geçişi.
- Takıldıktan sonra doğrula: `vcgencmd get_throttled` → **`0x0`** (reboot sonrası; geçmiş bitleri reboot'ta sıfırlanır).

> Not: `journalctl -k | grep -ci under-voltage` = 0 döndü ama yanıltıcı; kernel mesajı `Undervoltage detected!` biçiminde olabilir. Kaynak olarak `get_throttled` esas.

---

## 1. Ne değişti (EW'yi etkileyen kısım)

- Sahada **iki ayrı `192.168.0.0/24` ağı** var. Doğru olan **A ağı**: gateway MAC `c8:3a:35:81:39:70`, DVR burada.
- **RPi artık A ağında, doğrudan Tenda'dan DHCP alıyor: `192.168.0.43`.** OPi5 NAT'ının arkasında değil. DHCP olduğu için değişebilir; kalıcı erişim Tailscale ile sağlanacak.
- OPi5 LAN IP'si değişti: `192.168.0.2` / `.3` → **`192.168.0.200`**.
- Orin artık OPi5'in 2. portunun arkasında: **`192.168.10.39`** (OPi5 NAT + dnsmasq, `192.168.10.0/24`).
- Tüm Tailscale IP'leri değişti. Yeni tailnet **`alpertia@github`**, sunucularda key expiry kapalı.

### Ölü adresler (repo + cihazda ara, değiştir)

| Eski | Neydi | Durum |
|---|---|---|
| `100.80.20.60` | Orin Tailscale | ❌ → `100.117.235.84` |
| `100.95.169.39` | OPi5 Tailscale | ❌ → `100.87.168.14` |
| `100.80.46.1` | RPi Tailscale | ❌ → yeniden login gerekli |
| `192.168.0.3` / `192.168.0.2` | OPi5 LAN | ❌ → `192.168.0.200` |

Bilinen yerler: `generator.py` (`100.80.20.60`), `scripts/deploy_rpi.sh` (`100.80.46.1`), `/etc/edgeway/edgeway.env*`, `/etc/mediamtx/mediamtx.yml`.

> ⚠️ Saha içi trafik **LAN IP'si** kullanmalı, Tailscale değil. Tailscale yalnız uzaktan erişim içindir (CAMM-169 dersi #5).

---

## 2. Görev

1. RPi'yi bul, eriş.
2. RPi Tailscale → `alpertia@github`, key expiry kapat.
3. **MediaMTX kaynağını `generator.py`'de düzelt**, cihazda elle sed YAPMA (deploy geri yazar). `verify_tree.sh` → `deploy_rpi.sh`.
4. Aşağıdaki iki kaynağı dene, sonucu raporla.

### Kaynak seçenekleri

| # | Kaynak | URL | Not |
|---|---|---|---|
| **A** | **OPi5 MediaMTX** (önerilen) | `rtsp://192.168.0.200:8554/<cam>` | Aynı L2 ağ, ek ayar gerekmez. OPi5 v1.18.2, 23/25 path hazır |
| **B** | **Orin** | `rtsp://192.168.10.39:8554/<cam>` | ⚠️ İki engel: (1) Orin MediaMTX **masked**, (2) RPi `192.168.10.0/24`'ü görmez, RPi'de `192.168.10.0/24 via 192.168.0.200` rotası + OPi5'te A→10 FORWARD izni gerekir. Denemeden önce CamMind tarafına sor |
| (C) | DVR direkt | `rtsp://<user>:<pwd>@192.168.0.4:554/...` | Eski yol. DVR oturum yükünü artırır |

> Ders (EW kendi notu): MediaMTX `ready` alanı kaynak varlığı değildir. Doğrulamayı gerçek kare/byte akışıyla yap (`ffprobe`).

---

## 3. Komutlar

**RPi IP'sini bul** (OPi5 üzerinden A ağını tara, RPi MAC'lerini süz):
```bash
ssh opi5 "for i in \$(seq 2 254); do ping -c1 -W1 192.168.0.\$i >/dev/null 2>&1 & done; wait; ip neigh show dev enP3p49s0 | grep -iE 'b8:27:eb|dc:a6:32|e4:5f:01|d8:3a:dd|2c:cf:67'"
```

**Mevcut durum:**
```bash
ssh -J opi5 pi@192.168.0.43 "grep -nE 'source:|rtsp://' /etc/mediamtx/mediamtx.yml; systemctl is-active mediamtx edgeway-recorder edgeway-api edgeway-heartbeat; tailscale status | head -1"
```

**Kaynak A erişim testi (RPi'den):**
```bash
ssh -J opi5 pi@192.168.0.43 "ffprobe -v error -rtsp_transport tcp -select_streams v:0 -show_entries stream=codec_name,width,height -of csv=p=0 rtsp://192.168.0.200:8554/cam1"
```

**OPi5'te hazır path listesi:**
```bash
ssh opi5 "curl -s localhost:9997/v3/paths/list | python3 -c \"import sys,json;print(sorted(p['name'] for p in json.load(sys.stdin)['items'] if p['ready']))\""
```

---

## 4. Kabul kriteri

- [x] RPi IP'si bulundu, `ssh -J opi5 pi@192.168.0.43` çalışıyor
- [ ] RPi ayrı 5V/2.5A adaptörde, `get_throttled` = `0x0`
- [ ] RPi Tailscale `alpertia@github`, key expiry kapalı, Mac `~/.ssh/config`'e `rpi` girdisi
- [ ] `generator.py` + `deploy_rpi.sh` güncellendi, eski IP repo'da kalmadı (`git grep -nE '100\.80\.20\.60|100\.80\.46\.1|100\.95\.169\.39|192\.168\.0\.(2|3)\b'` boş)
- [ ] `verify_tree.sh` PASS, deploy tamam
- [ ] Kaynak A: kamera başına `ffprobe` gerçek akış veriyor; recorder segment üretiyor
- [ ] Kaynak B: denendi / ertelendi, gerekçesiyle
- [ ] Sonuç CamMind'a geri bildirildi (hangi kaynak, kaç kamera, IP)

## 5. Dokunma

- OPi5 netplan / dnsmasq / iptables: CamMind tarafının.
- Orin MediaMTX unmask: CamMind'a sormadan yapma.
- Kimlik bilgisi paylaşırken **maskeli** yaz (`ab***9`).
