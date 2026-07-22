# EDGEWAY_STATUS.md — 21 Tem 2026 gece kapanisi
Diger sohbetlere/yarina devir dokumani. Tum degerler MASK'li.

## Urun
edgeWAY Pro2 — mevcut kamera/DVR'a dokunmadan takilan kutu: RTSP alir, lokale kaydeder,
AWS'ye sifreli yedekler, web portaldan canli + DVR tarzi geri gosterim. Repo: github.com/alpertia/edge_way (private).

## Saha durumu (Tahtasaray, site-002)
- Cihaz: RPi3B+ (edgeway-rpi-01), Tailscale 100.80.46.1, kaynak ~/edge_way, calisan /opt/edgeway
- Kameralar: cam1 + cam2 (DVR 192.168.0.4, Hikvision tipi, HEVC; main kayit, sub canli)
- Servisler: edgeway-api(:8080) / edgeway-recorder / edgeway-heartbeat / edgeway-uploader.timer(2dk) — hepsi active
- MediaMTX v1.11.3: config ARTIK generator uretimi (/etc/mediamtx/mediamtx.yml), cam1+cam2 sub on-demand; test_cam1 (Orin relay) emekli
- Termal: 59-62C bandi (ortam kaynakli, yuk degil); cam2 etkisi ~gurultu; temp.log haftalik veri topluyor; fan planli
- Config: /etc/edgeway/edgeway.env (640 root:edgeway) — DVR sifresi ve AWS cihaz anahtari sadece burada

## Depolama & bulut
- Lokal: 60sn segment, retention = 1 gun + 2GB tavan + %85 disk; silme segment-bazli en-eskiden (FIFO); ~4MB/dk => 2GB ~ son 8-9 saat
- Yukleme: 2dk'da bir, kronolojik (FIFO), .up sidecar isareti; kopukta bekler, donunce devam; TimeoutStartSec=2h
- AWS (hesap: alper.private): bucket edgeway-antsoft-site-002 (eu-central-1, SSE, public-block), lifecycle 90g->Glacier IR, 180g->Deep Archive, 730g sil
- IAM: cihaz kullanicisi edgeway-rpi-01 (sadece bu bucket); admin anahtari yalniz Mac'te

## Portal (:8080)
- Canli: rozetli, kontrolsuz; kayit/bulut: gun sec -> kesintisiz akis, gun cizelgesi, jog kadrani (1 tur=60sn),
  -1dk/+1dk, gercek saat; bozuk segment otomatik atlanir; ayni-segment seek reload'suz
- Senkron: 2+ kamera yan yana, tek cizelge/jog; kapsam disi kamera "bu saatte kayit yok"
- Depolama satiri: kayit sayisi, GB/tavan, en eski/yeni goreli ("11 sa once"), bulut senkron durumu
- Bulut sekmesi: S3 presigned dogrudan tarayiciya (cihaz bandi sifir)
- /setup sihirbazi: DVR test + kamera kesfi + env'i kutunun yazmasi (apply-env sudo helper); provision sonrasi token kilidi
- Bilinen: HEVC tarayici uyumu degisken (Safari/iPhone OK; cozum yol haritasinda H.264 transcode katmani — RPi5/OPi5 tier isi)

## Calisma duzeni (ZORUNLU)
- Deploy TEK komut: ./scripts/deploy_rpi.sh — once scripts/verify_tree.sh (26 invariant) gecmeden cihaza bayt gitmez
- Yeni ozellik = verify_tree.sh'a yeni satir. "Update eski kazanimi bozamaz" kurali mekanik.
- Sifre/anahtar asla chat'e/log'a: read -s ile cihaza, debug ciktilari sed 's/eyJ.../MASKED/' + ffmpeg log maskesi cihazda
- MediaMTX config degisikligi: sudo PYTHONPATH=/opt/edgeway .venv/bin/python -m edgeway.mediamtx_common.apply /etc/mediamtx/mediamtx.yml (yedek+geri alim refleksi)

## Yol haritasi (docs/UMBRELLA.md)
SIRADAKI: "Kaynaklar" menusu — docs/SOURCES_SCHEMA.md modeli: domain(cam) > site > cihaz > DVR-0001(marka/IP/kullanici/sifre)
> available/selected kameralar; portal CRUD + kaydet zinciri (sources.json -> env -> mediamtx.yml -> restart). Terminal olur.
Sonra: silme+audit, canli grid, bulut portal (edgeway.ant-soft.uk, yeni Supabase, roller), klip export, iOS, QR/AP (hostapd), faturalama.

## Acik ucler
- Tarayici testi bekliyor: cam2 canli + senkron "kayit yok" davranisi (sert yenile sart)
- SSH PasswordAuthentication hala yes (key calisiyor; uretim imajinda kapatilacak)
- Sihirbaz marka preset listesi (Hikvision/Dahua/XMEye path sablonlari)
- RPi4/RPi5 karari: 1 haftalik temp.log sonrasi; kasa yan paneli RPi4 icin revize
