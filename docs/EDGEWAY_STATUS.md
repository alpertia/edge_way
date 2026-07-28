# EDGEWAY_STATUS.md — 28 Tem 2026 kapanis (v2)
Devir dokumani. Onceki surumun ustune gecer (docs/EDGEWAY_STATUS.md). Degerler MASK'li.

## Su anki mod: EV LABORATUVARI
- Kutu (RPi3B+, edgeway-rpi-01, TS 100.80.46.1) Alper'in evinde; kayit kaynagi DVR degil
  ORIN RELAY: EDGEWAY_CAMERAS=cam1/cam2/cam22 = rtsp://100.80.20.60:8554/camX (Tailscale uzeri)
- Saha config yedegi cihazda: /etc/edgeway/edgeway.env.saha — sahaya donuste geri yuklenecek
- Saha donus plani: eski kablo+port ile test (kesin kok neden), yeni patch kablo + yedek 5V/2.5A
  adaptor + "KAPATMAYIN" etiketi goturulecek; surekli-acik prize alinacak

## Olay dosyalari (3 kesinti — hepsi kapandi)
1. 35s: ffmpeg soket timeout yoklugu + DVR gece reboot -> stall nobetcisi (180sn) eklendi
2. 21s: BENIM hatam — rw_timeout bayragi cihaz ffmpeg'inde yok (kod=8); bayrak kaldirildi
3. 55s: saha Ethernet yolu (kablo/port suphesi) — kutu evde saniyesinde bagladi, donanim temiz
Ortak ders: WATCHDOG sart (uc kez de Alper fark etti). rec_age_s nabizda akiyor, bulut bekcisi bekliyor.
Journal artik KALICI (100M) — bir daha "defter bos" yok.

## YENI: Event-klip motoru [UCTAN UCA DOGRULANDI]
- Karar: olay kaynagi CamMind/Orin webhook; plan bazli bulut (EDGEWAY_UPLOAD_MODE=continuous|events|both,
  cihazda su an both); kirpma = ZAMAN kirpma tam kare (kanit butunlugu)
- Akis: POST /api/events {cam, ts(epoch|ISO|bos=simdi), type, pre_s=10, post_s=20}
  -> events/<gun>.jsonl -> ring tampondan concat inpoint/outpoint + -c copy klip
  -> clips/<cam>/<gun>/HHMMSS_<type>.mp4 -> S3 clips/ prefix (kanit: 143532_person.mp4 Frankfurt'ta)
- Sozlesme dokumani: docs/EVENTS_API.md (CamMind sohbetine tasinacak)
- Bilinen ince ayar: klip keyframe'e yaslanir (+-1-2sn genis) — dogru davranis
- Acik tasarim karari (Alper): event kaynagi da kameralar gibi config'te olmali —
  EDGEWAY_EVENT_SOURCE=push|poll:URL (outbound-only prensibi); CamMind entegrasyonuyla yazilacak
- Processing delay cevabi: klip ts'e gore kesilir, gecikme zarar vermez; sart = CamMind ts gondersin
  + NTP hizasi + gecikme < ring penceresi (~70dk)

## Portal v2.1 (mevcut)
Modsuz tek pencere: varsayilan canli, kadranla ayni pencerede time-shift, kirmizi CANLI donusu,
canliya yetisince otomatik gecis; aylik takvim; tek Zaman kadrani + buyuk tarih/saat (jog aninda akar);
secimli senkron (soldan kutucuk, limit 4, 2x2); tikla-buyut 3 kademe; birlesik takvim (lokal+bulut tek gorunum);
faz farki ayar menusu (localStorage MVP); bos gun dayanikliligi; faststart (bulut aninda acilis).

## Degismeyen omurga
Depolama: ring 1.5GB (~70dk/3kam) + S3 arsiv (edgeway-antsoft-site-002, eu-central-1, lifecycle);
uploader FIFO 2dk + TimeoutStartSec=2h + durust exit; NOPASSWD pi; deploy TEK komut ./scripts/deploy_rpi.sh
(46 invariant gecmeden bayt gitmez); sifreler asla chat'e — maskeli akis; attach_ssd.sh hazir.

## SURECKURALLARI (Alper koydu, kalici)
1. Acik ariza varken yeni ozellik yok — sadece tek-degisiklik hotfix
2. Cihazda kosan arac bayraklari (ffmpeg vb.) once cihazda test edilir
3. Zip YALNIZ yesil testten sonra uretilir (bugun iki kez kendini odedi)

## Sirada (oncelik tartisilacak)
- WATCHDOG (onay bekliyor — uc olayin dersi): bulut nabiz alicisi + 5dk bekci + TalkMind uyari
- Portal cizelgesinde olay isaretleri (events jsonl hazir)
- CamMind webhook entegrasyonu (EVENTS_API.md ile; ilk-tespit-aninda-gonder kurali + tipik delay sorusu)
- edgeway.ant-soft.uk: / = tanitim, /app = bulut portal (kutu olse de izleme — elektrik dersinin cevabi)
- Kaynaklar menusu (SOURCES_SCHEMA.md), silme+audit, iOS, QR/AP cihaz tarafi
- Hijyen: __pycache__ gitignore'a
