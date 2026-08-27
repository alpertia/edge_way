# EDGEWAY_STATUS.md — 2 Agu 2026 kapanis (v3)
Devir dokumani. Onceki surumun ustune gecer (docs/EDGEWAY_STATUS.md). Degerler MASK'li.

## Su anki mod: EV LABORATUVARI
- Kutu (RPi3B+, edgeway-rpi-01, TS 100.80.46.1) Alper'in evinde; kayit kaynagi DVR degil
  ORIN RELAY: EDGEWAY_CAMERAS=cam1/cam2/cam22 = rtsp://100.80.20.60:8554/camX (Tailscale uzeri)
- Saha config yedegi cihazda: /etc/edgeway/edgeway.env.saha — sahaya donuste geri yuklenecek
- Saha donus plani degismedi: eski kablo+port ile test, yeni patch kablo + yedek 5V/2.5A adaptor
  + "KAPATMAYIN" etiketi, surekli-acik priz
- Son durum (2 Agu 09:12 deploy sonrasi): status OK, uc kamera rec_age 0sn, disk %73.9,
  temp 56C, load1 1.24, uc servis active. HEAD = c4946ad, agac temiz, 53 invariant yesil.

## GUNCEL DURUM — 27 Agu

Kayit: cam1, cam19 (2 kamera). Izleme: 19 kamera (EDGEWAY_VIEW_CAMERAS).
Kaynak OPi5 (CAMM-131), Tailscale uzeri — kutu evde, LAN erisimi YOK.
wa %8.3, CPU %84 bosta, 62.8C. HEAD = 26ce127.

### DARBOGAZ DISK, ISLEMCI DEGIL (27 Agu, sayisal)
12 kamera mainstream H.265 ile: wa=%89.9, id=%0.0, us=%5.9.
CPU bos, surecler DISKE YAZMAYI bekliyor. Kart: SD8GB, 09/2015 — 11 yillik.
2 kameraya inince wa %89.9 -> %8.3.

  5 kamera  load15 3.61   6 kamera 4.46   7 kamera 4.97
  8 kamera  load15 5.35  12 kamera 9.50   stall hepsinde 0

SONUC: RPi4'e gecmek YANLIS yon. Kart degisimi dogru yon.
Endurance microSD (Kingston/Samsung PRO Endurance) 64-256GB.
Kapasite testi sirasinda tavan bulunamadi — 12 kamerada bile stall yok,
yalniz kart tikandi.

### IZLEME/KAYIT AYRIMI (26ce127)
Izleme diske YAZMAZ, kayit yazar. Bu yuzden listeler ayrildi:
  EDGEWAY_CAMERAS       -> kaydedilecekler (kayitci)
  EDGEWAY_VIEW_CAMERAS  -> yalniz canli izlenecekler
/api/cameras ikisini birlestirir, recorded bayragi doner.
sourceOnDemand sayesinde izlenmeyen kamera SIFIR maliyet.

### LOG FIRTINASI KESILDI (472a57c)
edgeway-recorder dakikada ~325 satir yaziyordu; 3dk'lik ornekte 371 satirin
371'i "Non-monotonic DTS". Bedeli: journald zinciri systemd/dbus'i %50-70
CPU'ya cikariyordu ve 8 kamera olcumu 5.35 yerine 9.79 gosteriyordu.
_pipe_masked artik tekrar eden satiri 60sn bastirir, "xN kez" ozeti yazar.
1624 -> 61 satir/5dk. Ayni sel 1/2 Agu'da kaniti yok etmisti.

### PORTAL (472a57c, LIVE-RESUME-v1)
- Acilista ~00:26'dan oynatiyordu: render() span[0] (arsivin EN ESKISI)
  kullaniyordu, bulut arsivi birlesince gunun basina atliyordu. Artik
  bugundeyse CANLI, gecmis gunde EN YENI an.
- Sekme arka planda kalinca HLS oluyordu; visibilitychange ile tazelenir.
- CANLI rozeti kaldirildi, kamera adi etiketi canliyken kirmizi + nokta.

## OLCUM DERSI (27 Agu, kalici)
`ps -o pcpu` SUREC OMRU ORTALAMASI verir, anlik degil. Uc olcum boyunca
"tailscaled %80, kamera sayisindan bagimsiz" diye okundu; `top -bn2` ayni
anda %0 gosterdi. Hesap: 9s14dk omur, 405dk CPU -> %73 ortalama.
ANLIK CPU icin `top -bn2` veya `vmstat` kullanilir, `ps` KULLANILMAZ.
Bu hata bugunku butun kapasite sayilarini kirletti; load ortalamalari
(uptime) ve wa (vmstat/top) saglam kaldi.

## CAMM-131 DUZELTMESI
Handoff "RPi kaynagi 192.168.0.3'e cevrilmis" diyor — YANLIS. Kutu evde,
LAN erisilemiyor (ping duser). Tailscale kullanildi: 100.95.169.39:8554.
DVR oturum hesabi etkilenmiyor: cekilen kameralarin hepsinin OPi5'te
zaten okuyucusu var, ek oturum acilmaz.
"RPi telemetrisi 4 gundur sessiz" kalemi KAPANDI: rpimon-push 21 Agu'da
KASTEN durduruldu (Orin icin yazilmisti, rpi'de yanlis veri uretiyordu).

## GUNCEL DURUM — 23 Agu 09:20
Kayitli kameralar: cam1, cam23, cam19, cam20 (Orin relay uzeri, dorde cikildi).
status OK, dordu de taze, disk %70, temp 60C, load1 ~2.2, uc servis active.
NABIZ ARTIK BULUTA GIDIYOR (CONTRACT adim 5-7 kapandi).
PORTAL INTERNETTEN ERISILEBILIR: https://edgeway.ant-soft.uk (giris korumali).
HEAD = 75a146c.

Adresler:
  edgeway.ant-soft.uk       -> cihaz portali (cloudflared, localhost:8080)
  edgeway-live.ant-soft.uk  -> HLS canli akis (localhost:8888)
  100.80.46.1:8080          -> Tailscale (yerel, degismedi)

## GUNCEL DURUM — 22 Agu 01:35
Kayitli kameralar: cam4, cam6, cam19 (SpaceMind icin; Orin relay uzeri).
Eski cam1/cam2/cam22 listeden CIKARILDI — bkz. kaynak basina kota vakasi.
status OK, rec_age 0/2/3sn, disk %69.5, temp 58C, load1 1.00, uc servis active.
HEAD = a473314, 53 invariant yesil.

### RPi3B+ KAPASITE OLCUMU (21 Agu) — sayisal
Ayni kutu, ayni kosullar, yalniz kamera sayisi degisti (-c copy, transcode YOK):
  3 kamera: load1 ~1.0-1.5, sicaklik 62C, saatlik stall/cikis sayaci = 0
  6 kamera: load1 8.0 (load15 6.9), sicaklik 67C, CPU %97-100,
            SAATLIK STALL/CIKIS SAYACI = 19
Uce donuldugunde sayac tekrar 0. Sinir dort cekirdekte alti kamera.

Bu olcum ACIK KARAR 1'i (HDMI canli grid) buyuk olcude cevapliyor:
kayitta bile alti kamera siniri zorluyorsa, ustune decode + compositing
HIC kaldirmaz. RPi4 karari guclendi.

## ACIK OLAY — 1/2 Agu gecesi, 11s50dk kayit boslugu [KOK NEDEN BULUNDU — 5 Agu]

KOK NEDEN: korumasiz stat -> daemon thread olumu.
_newest_age (segmenter) rglob ile listeledigi dosyayi stat ederken retention
o dosyayi silince FileNotFoundError firliyor; record_loop thread'i oluyor,
servis "active" gorunmeye devam ediyor. Olen thread stall bekcisini de
goturuyor, asili ffmpeg'i kimse terminate etmiyor -> sessiz kayit boslugu.
Logda dort kez dogrulandi: 02/08 09:42 cam22, 02/08 12:32 cam2,
03/08 01:14 cam1, 05/08 04:08 cam22.
cam1'in gun donumu imzasi da ayni zincir: 00:00:00'da segment acilamadi,
beklenen "[recorder] cam1 ffmpeg cikti" satiri YOK cunku kod oraya
ulasmadan thread oldu — log budanmasindan degil.
Sistemin ILK KEZ kendi yakaladigi kesinti (onceki uc olayi hep Alper fark etmisti).
engine.last24h() ciktisi: 01/08 21:21 -> 02/08 09:11, 710 dk, 1427 ornekte 705 CRIT.

Zaman cizelgesi (elde kalan kanitla):
- 21:11 civari cam2 durdu — SEBEBI BILINMIYOR, kanit silindi (asagi bak)
- 23:40 cam22 Non-monotonic DTS seli basladi
- 00:00:00 cam1 oldu: "Error submitting a packet to the muxer: No such file or directory"
  + "Error writing trailer: Invalid argument" — gun donumu imzasi
- 09:12 deploy restart'i uc kamerayi da geri getirdi

KANIT IMHASI (asil bulgu): gece 132.955 journal satirinin 132.828'i cam22'nin DTS uyarisi
(%99.9). Journal 100M tavaninin 92M'inde; bu servisin en eski kaydi artik 01/08 23:40:13.
21:00-23:40 arasi BUDANDI. cam2'nin durma sebebini gosteren satirlar yok edildi.
Ayrica journald ratelimit suphesi: cam1'in muxer hatasindan sonra gelmesi gereken
"[recorder] cam1 ffmpeg cikti (kod=...)" satiri da yok — DTS seli teshis satirlarini
bogmus olabilir (dogrulanmadi, "Suppressed N messages" aranacak).
DTS kaynagi Orin MediaMTX 1.18.2 -> CAMM-93 ile ayni dikis. Surum sapmasi artik soyut
bir borc degil, EdgeWay'in teshis yetenegini yedi.

Sayimlar: cam1 5 dosya, cam2 5 dosya, cam22 407 dosya.
ffmpeg surec sayisi 3 (dorduncu satir pgrep sarmalayicisiydi — oksuz surec YOK).
cikti:0 stall:0 traceback:0 systemd restart:0 (gece boyunca) — ama bu yokluk KANIT DEGIL,
cunku log budanmis. Bu turda iki hipotez kuruldu ve ikisi de curudu (thread olumu,
oksuz ffmpeg); ucuncusu (ratelimit) acik.

DUZELTME (5 Agu):
- "thread olumu hipotezi curudu" YANLIS. Gerekce "ffmpeg surec sayisi 3,
  oksuz yok" idi; ana surec yasadigi icin olen thread'in ffmpeg'i zaten
  mesru cocuk olarak sayilir. Sayim hipotezi curutmuyor, onunla tutarli.
  Hipotez DOGRUYMUS.
- Ratelimit hipotezi curudu: pencerede tek "Suppressed" satiri yok, ayrica
  3,9 satir/sn sinirin (333/sn) seksen kat altinda. Budama sebebi duz hacim:
  SystemMaxUse=100M, rotate + vacuum satir degil DOSYA siler.
- "traceback:0 / systemd restart:0" YANLIS. Grep yalniz edgeway-recorder'a
  bakmis; edgeway-heartbeat'te ayni gece alti traceback ve restart var.

## Bu sprintte kapanan uc is
1. KLIP RETENTION TAVANI (9738221)
   Bulgu: retention modulu clips/ dizininin varligindan habersizdi; _total_bytes() yalniz
   REC_DIR sayiyordu. CamMind webhook'u baglandiginda kart sessizce dolacakti.
   Cozum: enforce_clips_retention() + EDGEWAY_CLIPS_MAX_GB=0.5. YALNIZCA .up isaretli
   (buluta cikmis) klipler silinir — kanit buluta gitmeden asla silinmez.
   Sahadaki dogruluk kaniti silmesi degil SILMEMESIYDI (1.5MB tavan altinda, [clips] logu yok).

2. YEREL SAGLIK MOTORU (13fb61f) — edgeway/health/engine.py
   Karar: nabiz iki katmanli. Yerel motor internetsiz calisir; bulut ustune binen tuketici.
   snapshot() TEK HESAP NOKTASI — /api/health, bulut nabzi ve portal ayni ciktiyi okuyacak.
   rec_age artik heartbeat ve segmenter'da ayri ayri hesaplanmayacak.
   Esikler: rec_age 180 WARN / 600 CRIT, disk 85/93, temp 75/82, servis dususu CRIT.
   Gecmis: health_history.jsonl 24s, otomatik budama, last24h() sessiz bosluk cikarimi.
   Olcek tuzagi kapatildi: rec_age taramasi en yeni IKI GUN klasoruyle sinirli
   (eski hali her 15sn tum arsivi stat'liyordu — SSD'ye gecince 3x20.000 stat/15sn olurdu).
   hw_id = 000000004803ffaa (QR/pairing capasi; DEVICE_ID env'den degisir, seri degismez).

3. ACILIS TOLERANSI (c4946ad)
   Bulgu: 30 Tem deploy'unda tek CRIT — cam1 null, digerleri 10sn. Restart sonrasi ilk
   segment henuz kapanmamisti. Bulut bekcisi kurulsa her deploy'da sahte alarm calacakti.
   Cozum: GRACE_S=150, acilis penceresinde "ilk segment bekleniyor" WARN.
   Sure dolunca yine CRIT; BAYAT kayit acilis penceresinde bile CRIT kalir (testle sabit).

4. TOCTOU KORUMASI (5 Agu)
   agent._rec_ages + segmenter._newest_age / _segments_oldest_first /
   _total_bytes: stat try/except ile korundu, kaybolan dosya atlanir.
   Sessiz yutma YOK — beklenmedik istisna hala yukari cikar.

5. TOCTOU YAMASI DOGRULANDI (16 gun saha kaniti)
   5 Agu - 21 Agu arasi: sifir thread olumu, sifir traceback, sifir restart.
   Yamadan onceki dort gunde dort kez olmustu. Recorder PID degismedi.
   Gun donumu artik kayip uretmiyor: ffmpeg'ler 00:00'da yeniden basliyor,
   thread yasiyor, backoff calisiyor.

6. HEARTBEAT_CONTRACT v1 + CIHAZ TARAFI BAGLAMA (75a8515, a473314)
   docs/HEARTBEAT_CONTRACT.md yazildi (ONCE SOZLESME kurali).
   Bulgu: /api/health ucu HIC YOKTU (404). Mevcut /health kendi hesabini
   yapiyor ve sabit "status":"ok" donuyordu — portal ne kadar bozuk olursa
   olsun hep OK derdi. agent._rec_ages() de kendi taramasini yapiyordu;
   13fb61f'in "tek hesap noktasi" karari HICBIR YERE uygulanmamisti.
   Cozum: /api/health eklendi (auth'lu, snapshot() doner), /health motora
   baglandi, _rec_ages KALDIRILDI.
   Sozlesme adimlari: 1-4 KAPANDI, 5-7 ACIK.

7. _newest_age KORLUGU KAPANDI (a473314)
   Bos arsivde 0.0 yerine None doner; stall bekcisi artik bos arsivde de
   tetikleniyor. 1/2 Agu'da tetiklenmemisti cunku KEEP_LAST=5 sayesinde
   bayat mtime donuyordu — korluk gercekti ama o gecenin sebebi degildi.

8. CONTRACT ADIM 5-7 KAPANDI — EKSIK HALKA BAGLANDI (22 Agu)
   Motor 1/2 Agu gecesini kaydetmisti ama soyleyecek kimsesi yoktu. Artik var.
   Zincir: engine.snapshot() -> /api/health -> device-token guard ->
   device_health -> v_device_health -> OPi5 timer'in tetikledigi
   /api/cron/health-check -> service_health_incidents + TalkMind alarmi.

   cooks_mind tarafi:
     supabase/migrations/20260822_device_health.sql
       device_tokens (hw_id, token_hash) — token CIHAZ BASINA, paylasilan
       tek sir DEGIL. Bilinmeyen cihaz / pasif cihaz / yanlis token AYNI 401.
       device_health (hw_id PK) + v_device_health (stale 90sn / offline 300sn).
       Tazelik SUNUCU saatinden (updated_at) hesaplanir — cihaz saati kayabilir.
     /api/cooksmind/v1/device/health  — POST alici
     /api/health/device-crit          — "CRIT diyen var mi" -> 503
     /api/health/devices              — panel veri ucu
     registry.ts: edgeway (db_freshness) + edgeway_status (healthz_url)
       IKI AYRI ARIZA: nabiz gelmiyor / nabiz geliyor ama cihaz CRIT diyor.
       db_freshness ikincisini YAKALAYAMAZ (updated_at taze kalir).
     settings/edge sayfasina DeviceHealthPanel — CamMind ajan modelinden AYRI.
       Baglanti kopuksa metrikler soluk + uyari: donmus deger CANLI sanilmasin.

   edge_way tarafi (3955e73, a473314):
     /api/health ucu eklendi, /health motora baglandi (sabit "ok" kalkti),
     agent._rec_ages KALDIRILDI, _newest_age bos arsivde None.

9. BEKCI ILK GERCEK OLAYINDA CALISTI (22 Agu 18:45)
   Kurulumundan 20 dakika sonra "EdgeWay durum DOWN / HTTP 503" Telegram'a dustu.
   Yalanci alarm DEGILDI: cihaz cam2/cam6 icin CRIT diyordu, oysa o kameralar
   listeden cikarilmisti. Sebep: .env degistirilirken edgeway-heartbeat
   RESTART EDILMEMISTI — ajan bayat config tasiyordu.
   Bekci olmasa fark edilmezdi. Bkz. surec kurali 8.

10. PORTAL BASTAN YAZILDI (75a146c)
   Bes ayri yama ust uste celiskiye dustu (biri revert edildi). Sorun tek tek
   hatalar degil MODELDI:
     - IKI secim: ad dugmesi (tek kamera) + kutu (senkron kumesi), habersiz
     - IKI oynatici: #v ve SC[] — canli YALNIZCA #v'de yaziliydi
     - IKI zamanlayici: liveTimer + timeupdate, ayni alana yazip titretiyordu
     - Bayat async: pickDay'in .then()'i mod degistikten SONRA goLive() cagiriyordu
     - Takma ad: segs = withSegs[0].segs
   Yeni model: TEK secim kumesi (1 secili = tam ekran, 2-4 = izgara),
   TEK doseme tipi (canli her ikisinde de ayni yoldan — ayri ozellik degil),
   TEK surucu (500ms tick), her yuklemede GEN sayaci.
   20 verify_tree capasinin hepsi korundu (davranis adlari, uygulama degil).

11. TUNEL + GIRIS (75a146c)
   cloudflared 2026.8.2, tunnel id 61cdd649-...
   /api/login: kullanici + sifre -> API token. Duz sifre SAKLANMAZ,
   .env'de yalnizca sha256 ozeti (EDGEWAY_UI_USER / EDGEWAY_UI_PASS_SHA256).
   Sabit sureli karsilastirma, yanlis denemede 1sn bekleme.
   EDGEWAY_API_TOKEN artik ZORUNLU — tunel acikken portal korumasiz kalmasin.

## SIRADAKI IS: teshis edilebilirlik paketi (uc kalem, tek paket)
1. Gurultuyu kaynaginda kes — _pipe_masked tekrar eden satirlari bastirsin
   (ayni mesaj 60sn'de bir, "xN kez" ozetiyle). DTS uyarisi -c copy'de beklenen sey.
2. Recorder'in kendi sesini ayir — [recorder]/[retention] satirlari ffmpeg gurultusuyle
   ayni kanali paylasmasin; kritik teshis satiri asla dusurulmesin.
3. _newest_age KORLUGU — bos arsivde 0.0 donuyor, 0.0 > 180 asla dogru olmuyor.
   Retention olu kameranin dosyalarini silince nobetci TAM DA EN GEREKLI ANDA kor kalir.
   Teshisin sonucundan BAGIMSIZ gercek kusur.
Once "Suppressed N messages" aramasi yapilacak (ratelimit hipotezi).

## Sirada (oncelik sirasiyla)
- TANITIM SAYFASI YOK. web/ altinda yalniz index.html (portal) + setup.html.
  Karar bekliyor: cihazda mi (/ tanitim, /app portal) yoksa Vercel'de mi.
  Vercel onerilir — cihaz kapaliyken de acik kalir ve cok kiracili /app
  zaten bulutta olacak (device_health altyapisi CooksMind'da).
  O durumda cihaz ayri ada tasinir: edgeway-01.ant-soft.uk gibi.
- COK KIRACILI YAPI: cihazda OLAMAZ (rpi yalniz kendi kameralarini bilir).
  Dogru yer control-plane: sites + site_users, device_tokens zaten
  hw_id -> site bagini tasiyabilir.
- db_freshness IKINCI CIHAZDA KORLESIR: EN TAZE satira bakar, saglam cihaz
  olu cihazi maskeler. CM-89'daki cam15/cam16 korlugunun aynisi.
  ParkMind eklenmeden once stale_count benzeri bir tur gerekecek.
- CONTRACT §3 alan adlari GERCEKLE UYUSMUYOR: dokumanda disk_pct/mem_pct/
  product/uptime_s/version yaziyor, snapshot() disk_used_pct/mem_used_pct
  gonderiyor, son ucu hic gondermiyor. Sozlesme gercege uydurulacak.
- Panel esikleri (180/600sn) motorun KOPYASI. Kopya sapar; esikler de
  sozlesmeden gelmeli.
- CONTRACT adim 5: control-plane device-token guard + alici uc (CooksMind).
  Cihazda EDGEWAY_CLOUD_URL hala BOS — nabiz hicbir yere gitmiyor.
- CONTRACT adim 7: bekci (nabiz kesilirse TalkMind/WhatsApp uyarisi).
- threading.excepthook YOK — thread olumu hicbir yere yazilmiyor.
  systemctl is-active cok thread'li serviste saglik kaniti DEGIL.
  5 Agu yamasi BILINEN yarisi kapatti, bilinmeyeni degil.
- PORTAL SECIM KUSURU: ayni kamera birden fazla secilebiliyor, "max 4"
  uygulanmiyor. 5 Agu'da 12-13 dosemeye cikildi, sayfa kilitlendi.
- MEDIAMTX-ENV KOPUKLUGU: kamera degisince mediamtx.yml eski kaldi.
  Kayit calisiyor (ffmpeg Orin'e dogrudan bagli) ama CANLI IZLEME SIYAH
  (portal canli akisi rpi'nin kendi MediaMTX'inden cekiyor, yol tanimli degil).
  Kaynak menusu yazilirken zincir TEK olmali: env + mediamtx yolu + iki servis.
- threading.excepthook YOK — thread olumu hicbir yere yazilmiyor.
  systemctl is-active cok thread'li serviste saglik kaniti DEGIL.
  5 Agu yamasi BILINEN yarisi kapatti, bilinmeyeni degil.
- _newest_age bos arsivde 0.0 donuyor (bekci korlugu) — hala acik.
  Bu gece tetiklenmedi cunku KEEP_LAST=5 sayesinde bayat mtime dondu.
- Teshis edilebilirlik paketi (yukarida)
- KAYNAK BASINA KOTA: ring kuresel olarak en eskiden siliyor; saglam kamera arizalinin
  gecmisini yiyor (cam1:5 cam2:5 cam22:407). Kanit acisindan ciddi.
  YENI VAKA (21 Agu): ayni kusur baska bicimde calisti. Kamera listesinden
  cikarilan uc kaynagin (cam1/cam2/cam22) 1.5G gecmisi DAKIKALAR ICINDE silindi —
  cikarilinca arsivin en eskisi haline geldiler, ring sirayla hepsini yedi.
  RETENTION_DAYS=1 beklenmedi. Ev laboratuvari oldugu icin kayip onemsizdi;
  sahada bir kamera GECICI cikarilsa ayni sey olurdu.
  SONUC: kota, Girisler/Cikislar menusunden ONCE gelmeli. Menu kamera
  degistirmeyi kolaylastirirsa bu kayip da kolaylasir.
- /api/health ucu + portal ust seridi (motor hazir, sadece okunacak)
- BULUT NABIZ + BEKCI + TalkMind uyarisi — EKSIK HALKA. Motor bu geceyi kaydetti ama
  soyleyecek kimsesi yoktu. Kurulu olsaydi 21:26'da telefon calardi.
  Alici CooksMind control-plane'de (karar 31 Tem, ayri Supabase DEGIL).
  DIKKAT: oradaki api/health/route.ts guard'i supabase.auth.getUser() — cihazin kullanici
  oturumu YOK. Ayri device-token guard gerekecek (cihaz CLOUD_TOKEN ile POST, alici
  token'i hw_id'ye karsi dogrular).
- Girisler/Cikislar menusu (SOURCES_SCHEMA.md): giris = DVR/NVR/IP kamera + secili kanallar,
  cikis = USB / AWS / HDMI. Ikisi de ayni zincir: kaydet -> config -> servis tazele.
- Relay + pairing (uzaktan erisim) — asagida
- CAMM-93 handoff'unun TAM METNI okunacak (elde sadece iki uc var, ortasi kesik)
- Portal cizelgesinde olay isaretleri, silme+audit, iOS, QR/AP cihaz tarafi

## DURDURULAN: rpimon-push.service (21 Agu)
CamMind'dan kalma /home/pi/cam_mind/scripts/rpimon-push.sh rpi'de kosuyordu,
Orin Supabase'e metrik atiyordu. stop + disable edildi. Iki gerekce:
  (a) YANLIS VERI: dvr_reachable hesabi len(ready) > 0. Script Orin icin
      yazilmis, orada yollar surekli besleniyor. rpi'de MediaMTX yollari
      ON-DEMAND; izleyen yokken hicbiri ready degil. Sonuc: dvr_reachable
      daima false, down_cams daima alti yol — uc kamera kaydederken.
      Panelde "Kameralar (0)", "tracker idle" (rpi'de runner zaten yok).
      Ters yonde sessiz ariza: gercek kesinti de fark edilmezdi, hep kirmiziydi.
  (b) YUK: PUSH_INTERVAL=3 — uc saniyede bir bash + iki curl + iki python3.
Script silinmedi, yalniz durduruldu (CamMind Orin/OPi5 tarafi ayrica bakilacak).
CamMind paneli artik bu cihazi "offline" gosteriyor — BEKLENEN. Dogru cozum
CONTRACT adim 5: EdgeWay kendi nabzini control-plane'e gonderecek.

## Ekosisteme tasinacak kazanimlar (2 Agu tartismasi)
Karar: ONCE SOZLESME, SONRA KOD. docs/HEARTBEAT_CONTRACT.md yazilacak; motor bir-iki
gercek olay daha atlattiktan sonra ant_edge_common gibi paylasilan pakete cikarilacak.
Kopyala-yapistir YASAK — uc ay sonra uc farkli surum olur.
Alan UI'i ayri, cihaz duzlemi ORTAK: ParkMind kendi operasyon UI'ini yazsin ama cihaz
sagligini yeniden icat etmesin, control-plane'den okusun.
Tasinacaklar: nabiz sozlesmesi (hw_id/site_id/device_id/status/reasons/rec_age_s/...),
device-token guard, yerel-once saglik deseni, kanit korumali silme (.up kurali),
kaynak basina kota, acilis toleransi, verify_tree kapisi, idempotent apply_*.py deseni,
QR/hw_id pairing + relay.
- threading.excepthook + thread-olumu alarmi (CamMind'da da gecerli;
  olay gelmemesi kanit degildir, tipki log yoklugu gibi)
23 Agu dersleri:
  (f) Cloudflare Universal SSL YALNIZCA TEK SEVIYE joker kapsar.
      live.edgeway.ant-soft.uk iki seviye derinde kaldi, TLS el sikismasi
      basarisiz oldu (curl 000). Cozum: edgeway-live.ant-soft.uk.
  (g) sourceOnDemand MediaMTX yollari ILK istekte 404 doner (yol henuz acik
      degil). hls.js olumcul hatada birakilirsa doseme SIYAH kalir. Yeniden
      deneme sart — "canli calismiyor ama kadran calisiyor" bundandi:
      ikinci deneme isinmis yola denk geliyordu.
  (h) YENIDEN YAZIM hata siniflarini YAPISAL olarak kapatir (iki zamanlayici
      yoksa titresim olamaz) ama KENDI yeni hatalarini getirir. Ornek: yarislari
      onlemek icin eklenen GEN sayaci iki fonksiyonda paylasilinca render()
      kendi kendini iptal etti — siyah ekran, donmus saat. "Bastan yazinca
      hata cikmaz" beklentisi yanlistir.
  (i) Cok kiracili yapi CIHAZDA kurulamaz. Cihaz yalniz kendi kaynaklarini
      bilir; firma/kullanici duzlemi control-plane'e aittir.

Genel dersler (sozlesmeye girecek): (a) cok kaynakli kayitta kota yoksa saglam kaynak
arizalinin gecmisini yer; (b) zamana gore klasor yazan her servis klasoru yazmadan once
garanti altina almali; (c) bir kaynagin log gurultusu digerinin ariza kanitini yok edebilir.

## SURECKURALLARI (Alper koydu, kalici)
1. Acik ariza varken yeni ozellik yok — sadece tek-degisiklik hotfix
2. Cihazda kosan arac bayraklari (ffmpeg vb.) once cihazda test edilir
3. Zip YALNIZ yesil testten sonra uretilir
4. YENI: uzun cok satirli terminal yapistirmasi kirilgan (iki kez parse error + bir kez
   baska oturumdan metin karismasi). Paketler zip + tek satir komutla gonderilir.
   apply_*.py capa tekil degilse HIC DEGISIKLIK YAPMADAN durur (kasten bozulmus agacta sinandi).
5. YENI: log yoklugu kanit degil. Grep deseni kodun GERCEK kelimesiyle yazilir
   ("cikti", "stall"), tahminle degil — bu turda bir kez yanlis teshise yol acti.
6. YENI (22 Agu): grep BIRIM kapsami da yanlis olabilir. 2 Agu'da "traceback:0"
   sonucu yalniz edgeway-recorder'a bakildigi icin cikmisti; heartbeat'te alti
   traceback vardi. Kapsam once dogrulanir, sonra sayilir.
7. YENI: deploy komutu KOSARKEN sonraki komut yapistirilmaz — stdin'e gidiyor,
   dogrulama hic calismamis oluyor (bu turda uc kez oldu).
8. YENI (23 Agu): .env degisikligi UC servisi ilgilendirir —
   edgeway-recorder, edgeway-api, edgeway-heartbeat. 22 Agu'da ikisi ayri
   ayri unutuldu: biri portali uc kamerada birakti, digeri buluta BAYAT CRIT
   gonderip yanlis alarm caldirdi. Kaynak menusu yazilirken
   "kaydet -> config -> servisleri tazele" zinciri UCUNU de kapsamali.
9. YENI: apply_*.py dogrulamasi YAZMADAN ONCE yapilir. Yazma sonrasi
   dogrulama tutmazsa "HIC DEGISIKLIK YAPILMADI" mesaji YALAN olur —
   dosya zaten yazilmistir (22 Agu'da bir kez oldu).
10. YENI: ayni ada indirilen dosya (~/Downloads/index.html) eski surumle
   karisiyor. Kopyaladiktan sonra SILINIR.

## Degismeyen omurga
Ring 1.5GB (~70dk/3kam) + S3 arsiv (edgeway-antsoft-site-002, eu-central-1, lifecycle);
klip tavani 0.5GB (.up korumali); uploader FIFO 2dk + TimeoutStartSec=2h + durust exit;
NOPASSWD pi; deploy TEK komut ./scripts/deploy_rpi.sh (53 invariant gecmeden bayt gitmez);
sifreler asla chat'e — maskeli akis; attach_ssd.sh hazir; journal kalici (100M).
Event-klip motoru uctan uca dogrulanmis (docs/EVENTS_API.md).
Portal v2.1 saglam: senkron/takvim/time-shift kayip DEGIL — index.html hash'i Mac ve
cihazda birebir ayni (5909b9ff...), capalar 19 yerde, /api/cameras uc kamerayi donuyor.
Ekranda gorunmuyorsa tarayici onbellegi; sert yenile.

## ACIK KARARLAR (kod seklini degistiriyor)
1. HDMI'nin isi ne? Sahada TV'de surekli canli grid mi, yoksa yalniz kurulum ekrani mi?
   Ilkiyse RPi3B+ uc kamera decode + compositing'i KALDIRMAZ -> RPi4 karari otomatik duser,
   kasa yan paneli revize. (load1 deploy tepesinde 3.28 gordu; RPi3B+ dort cekirdek.)
2. Uzaktan erisim: "portale girip HW numarasiyla cihaza baglanmak" outbound-only prensibiyle
   CELISIYOR. Musteri aginda port acmak kabul edilemez -> bulutta RELAY sart (cihaz disari
   kalici kanal acar, portal komutu buluta yazar, cihaz kanaldan ceker). Tailscale bugun bu
   isi yapiyor ama o Alper'in tailnet'i, musteriye olceklenmez. QR/urun kodu + sifre = relay'e
   pairing adimi. Yani "Kaynaklar menusu uzaktan" IKI ayri paket: menu (cihazda, LAN'dan,
   bugun yapilabilir) ve relay (buyuk, ayri).
