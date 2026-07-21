# Kaynaklar (Sources) Veri Modeli — v0
# Hiyerarsi: domain > site > cihaz > kaynak(DVR) > kameralar

{
  "domain": "cam",
  "site": "site-002",
  "devices": [
    {
      "id": "edgeway-rpi-01",
      "hw": "rpi3b+",
      "sources": [
        {
          "id": "DVR-0001",
          "brand": "hikvision",          // marka preset -> rtsp path sablonu
          "model": "",
          "ip": "192.168.0.4",
          "port": 554,
          "user": "admin",
          "password": "(vault ref — plain yazilmaz)",
          "path_template": "/h264/ch{ch}/{stream}/av_stream",
          "cameras_available": [1,2,3,4,5,6,7,8],   // discover sonucu
          "cameras_selected":  [1,2]                 // kayit+canli acik olanlar
        }
        // DVR-0002: baska IP/kullanici, ayni liste mantigi — baska cihazdan bile olabilir
      ]
    }
  ]
}

# Kurallar:
# - Cihazdaki hali: /etc/edgeway/sources.json (640 root:edgeway); sifreler vault/secrets'ta
# - Kaydet aksiyonu zinciri: sources.json -> EDGEWAY_CAMERAS turet -> mediamtx.yml uret (generator) -> servis restart
# - Portal "Kaynaklar" sayfasi bu modelin CRUD'u; test/discover endpointleri mevcut sihirbazdan
# - Kamera adlandirma: <sourceId>-ch<N> (dvr0001-ch1) — coklu DVR celismez
