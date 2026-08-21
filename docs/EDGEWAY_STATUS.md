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
