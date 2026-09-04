# HEARTBEAT_CONTRACT.md — cihaz nabiz sozlesmesi (v1 taslak)

Tarih: 21 Agu 2026 | Durum: TASLAK, kod yazilmadan once onaylanacak
Kapsam: EdgeWay (ilk uygulayici), CamMind, ParkMind (gelecek tuketiciler)

Karar: ONCE SOZLESME, SONRA KOD. Bu dosya donmadan alici uc yazilmaz.

---

## 1. Neden

Cihaz sagligi her uruncle yeniden icat edilmemeli. Alan UI'i ayri
(EdgeWay arsiv, CamMind tracker, ParkMind park operasyonu), ama CIHAZ
DUZLEMI ORTAK: "bu kutu ayakta mi, kaydediyor mu, diski doluyor mu"
sorusunun tek bir cevabi olmali.

Bugunku durum bunun tersi:
- EdgeWay'in kendi motoru var (engine.snapshot()), ama disari soyleyemiyor
  (CLOUD_URL bos, /api/health ucu yok).
- rpi'de CamMind'dan kalma rpimon-push kosuyordu; Orin icin yazilmisti,
  rpi'de yanlis veri uretiyordu (Kameralar 0, tracker idle,
  dvr_reachable false — uc kamera kaydederken). 21 Agu'da durduruldu.

Iki ayri nabiz, iki ayri buluta, biri yanlis. Sozlesme bunu kapatir.

---

## 2. Tasarim ilkeleri

**Yerel once.** Cihaz internetsiz calisir. Bulut nabzi YEREL MOTORUN
USTUNE BINEN TUKETICIDIR, kaynagi degil. Bulut erisilemezse cihaz
kaydetmeye ve kendi sagligini hesaplamaya devam eder.

**Tek hesap noktasi.** status/reasons/rec_age YALNIZCA engine.snapshot()
icinde hesaplanir. Ajan, /api/health ucu ve bulut nabzi AYNI ciktiyi
okur. Ikinci bir hesap yazilmaz.

(Bugunku ihlal: agent._rec_ages() kendi hesabini yapiyor, engine'i import
bile etmiyor. Uygulama sirasinda kaldirilacak.)

**Yorum kaynakta.** "down" karari cihazda verilir, bulutta degil. Bulut
ham metrigi yeniden yorumlarsa rpimon-push hatasi tekrarlanir: on-demand
MediaMTX yollari izleyen yokken ready:false doner, bunu "kamera down"
sayan tuketici surekli yalanci alarm uretir.

**Yokluk kanit degildir.** Nabzin gelmemesi "cihaz saglikli degil"
demektir, "veri yok" demek degil. Alici tarafta sessizlik = alarm.

---

## 3. Payload

POST, JSON, tek gövde. Cihaz -> control-plane.

    {
      "hw_id":      "000000004803ffaa",
      "site_id":    "site-002",
      "device_id":  "edgeway-rpi-01",
      "product":    "edgeway",
      "ts":         1755777600,
      "status":     "OK" | "WARN" | "CRIT",
      "reasons":    ["WARN: cam4 kayit 240sn once"],
      "rec_age_s":  {"cam4": 12, "cam6": 12, "cam19": null},
      "disk_pct":   73.0,
      "temp_c":     62.8,
      "load1":      1.47,
      "mem_pct":    27.0,
      "services":   {"edgeway-recorder": "active", "edgeway-api": "active"},
      "uptime_s":   1892160,
      "version":    "db81b6b"
    }

Alan kurallari:

- `hw_id` DEGISMEZ (donanim serisi). Pairing/QR capasi budur.
- `device_id` env'den degisebilir; kimlik anahtari DEGILDIR.
- `status` uc degerden biri. Ara deger yok.
- `reasons` insan okur, makine PARSE ETMEZ. Bos dizi = gerekce yok.
- `rec_age_s` degeri `null` olabilir: "hic kayit yok" demek.
  `0` ile `null` ayni sey DEGIL. (Bkz. bilinen kusur: _newest_age bos
  arsivde 0.0 donuyor — sozlesme null bekliyor, uygulama duzeltilecek.)
- Bilinmeyen alan gonderilirse alici YOK SAYAR, reddetmez.
- Eksik istege bagli alan hata degildir.

Zorunlu: hw_id, site_id, device_id, product, ts, status.
Geri kalani istege bagli.

---

## 4. Kimlik dogrulama

Cihazin kullanici oturumu YOKTUR. Mevcut CooksMind guard'i
`supabase.auth.getUser()` kullaniyor; cihaz nabzi bu yoldan gecemez.

Ayri device-token guard gerekir:

- Cihaz `Authorization: Bearer <CLOUD_TOKEN>` ile POST eder.
- Alici token'i `hw_id`'ye KARSI dogrular. Token baska bir hw_id icin
  gelirse REDDEDILIR (401).
- Token cihaz basinadir; paylasilan tek anahtar KULLANILMAZ.
- service_role anahtari cihaza KONULMAZ.

---

## 5. Zamanlama

- Cihaz `HEARTBEAT_SECONDS` araliginda gonderir (varsayilan 15sn).
- Alici son nabzi saklar; **90sn** gecerse `stale`, **300sn** gecerse
  `offline` sayar.
- Push basarisiz olursa cihaz LOGLAR ama DONGUYU KIRMAZ.
  (agent.py docstring'i bunu zaten sozlesme olarak yaziyor:
  "Basarisiz push loglanir ama dongu olmez — cihaz bagimsiz calisir.")
- Cihaz kuyruk tutmaz. Kacan nabiz kacmistir; gecmis yerel
  health_history.jsonl'da durur.

---

## 6. Acilis toleransi

Restart sonrasi ilk segment henuz kapanmamis olabilir. GRACE_S=150
penceresinde `rec_age_s` null ise status WARN ("ilk segment bekleniyor"),
CRIT degil. Sure dolunca CRIT.

BAYAT kayit acilis penceresinde bile CRIT kalir. Bu ayrim testle sabit;
alici bunu yeniden hesaplamaz, cihazdan geleni okur.

---

## 7. Uygulama sirasi

1. Bu dosya onaylanir.
2. Cihaz: `/api/health` ucu (engine.snapshot() okur, hesap yapmaz).
3. Cihaz: agent._rec_ages() KALDIRILIR, ajan snapshot()'a baglanir.
4. Cihaz: EDGEWAY_CLOUD_URL ayarlanir.
5. Control-plane: device-token guard + alici uc.
6. Dogrulama: nabiz gidiyor mu, stale/offline gecisleri calisiyor mu.
7. Bekci: nabiz kesilirse uyari (TalkMind/WhatsApp).

Adim 7 EKSIK HALKA. 1/2 Agu gecesi motor 11s50dk kesintiyi kaydetti ama
soyleyecek kimsesi yoktu. Kurulu olsaydi 21:26'da telefon calardi.

---

## 8. Paylasilan pakete cikarma

HENUZ DEGIL. Motor bir-iki gercek olay daha atlatmadan `ant_edge_common`
gibi bir pakete cikarilmaz. Kopyala-yapistir da YASAK — uc ay sonra uc
farkli surum olur.

Bu sozlesme kod paylasmadan once ARAYUZU sabitler: ParkMind kendi
operasyon UI'ini yazar ama cihaz sagligini yeniden icat etmez,
control-plane'den okur.

---

## 9. Sozlesmeye giren dersler

(a) Cok kaynakli kayitta kota yoksa saglam kaynak arizalinin gecmisini
    yer. 21 Agu'da ayni kusur baska bicimde calisti: kamera listesinden
    cikarilan uc kaynagin 1.5G gecmisi dakikalar icinde silindi.
(b) Zamana gore klasor yazan her servis, klasoru yazmadan once garanti
    altina almali.
(c) Bir kaynagin log gurultusu digerinin ariza kanitini yok edebilir.
(d) Cok thread'li serviste `systemctl is-active` SAGLIK KANITI DEGILDIR.
    Olen daemon thread servisi active birakir. threading.excepthook
    kurulmadikca thread olumu hicbir yere yazilmaz.
(e) Ham metrigi tuketicide yeniden yorumlamak yalanci alarm uretir
    (rpimon-push / on-demand ready:false vakasi).

## Teslimat ile ariza ayrimi (3 Eylul 2026)

Olay: cihaz sagliktiydi, kayit kesintisizdi, portal 200 donuyordu — ama nabiz
buluta ulasmadi (`push hatasi: TimeoutError`) ve bekci 20 saat DOWN gosterdi.
Yerel `health_history.jsonl` ayni aralikta 1427 kayit, tamami OK, bes dakikadan
buyuk tek bosluk yok.

Kusur sozlesmedeydi: "cihaz oldu" ile "ag koptu" ayni sonuca cikiyordu.

Uc madde eklendi:

1. **`uptime_s`** — govdede. Nabiz gelmeyen bir aralikta uptime artmaya devam
   etmisse cihaz ayaktaydi, sorun teslimattadir.
2. **`boot_id`** — govdede. Degismediyse cihaz yeniden baslamamistir; degistiyse
   gercekten baslamistir. Sayac kullanilmadi cunku `snapshot()` portal ve
   `/api/health` tarafindan da cagriliyor, sayac orada da artardi.
3. **Tamponlama** — gonderilemeyen nabizlar cihazda `heartbeat_spool.jsonl`de
   birikir, baglanti donunce EN ESKIDEN baslayarak toplu gider. Bekci gecmise
   donuk duzeltebilir.

Bekci tarafinda (CooksMind) karsiligi: "nabiz gelmiyor" (BILINMIYOR) ile
"nabiz geldi ve sagliksiz diyor" (DOWN) ayri durumlar olmalidir.
