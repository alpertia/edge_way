# EdgeWay Umbrella Management — Yol Haritasi

## A. Filo yonetimi
- Hiyerarsi: firma > site > cihaz > kamera; QR/claim ile kayit; online/stale/offline rozetleri
  (devices+heartbeats tablolari hazir, watchdog cron)
- Uzaktan yonetim: config push, surum guncelleme, restart, log cekme
  (cihaz bulut komut kuyrugunu poll eder — outbound-only ilkesi; imzali uygulayici)

## B. Kullanici & yetki
- Multi-tenant + roller: owner / operator / viewer (Supabase Auth + RLS site_id)

## C. Canli
- Tekli izleme [VAR] · coklu grid 2x2/3x3 (sub-stream on-demand) · tek dokunus kamera gecisi
- Tam ekranda main-stream'e terfi

## D. Playback
- Gun cizelgesi + kesintisiz akis [VAR]
- Coklu kamera SENKRON playback: tek zaman imleci, tum kameralar ayni ana atlar
  (segment adlari mutlak saat = ortak eksen; sart: cihazlarda NTP/chrony)
- Klip export t1-t2 (cihazda ffmpeg trim, indirilebilir link)
- Olay isaretleri: hareket/AI event noktalari (CamMind entegrasyonu)

## E. Kayit yonetimi
- Depolama gorunurlugu: pencere (ilk-son), boyut, bulut senkron durumu [BU PAKETTE]
- Silme: sadece owner, lokal+bulut birlikte, AUDIT LOG zorunlu (kim/ne araligi/ne zaman);
  istege bagli legal-hold (silinemez mod)
- Kamera ekle/cikar portalden: discover -> config push -> recorder reload
- Plan bazli saklama politikalari (gun + GB + bulut katmani) — motor calisiyor, UI dugmesi eksik

## F. Uyari & saglik
- offline / disk / sicaklik / kamera-down / upload-gecikmesi -> TalkMind + e-posta (alerts tablosu hazir)

## G. Plan & faturalama
- Kamera sayisi, retention, bulut GB limitleri; kullanim olcumu

## Sira
1. cam2 + senkron playback (D) — termal olcumle birlikte
2. Silme + audit (E)
3. Grid canli (C)
4. Bulut portal + roller (B, A) — edgeway.ant-soft.uk
5. Klip export, olay isaretleri, faturalama
