# EdgeWay Olay API'si — CamMind/Orin entegrasyon sozlesmesi

POST http://<edgeway-cihaz>:8080/api/events
Header: Content-Type: application/json
        Authorization: Bearer <EDGEWAY_API_TOKEN>   (token tanimliysa zorunlu)

Govde:
{
  "cam":   "cam22",                  # EdgeWay kamera adi (zorunlu)
  "ts":    1753701234.5,             # epoch sn YA DA "2026-07-28T13:53:00" — bos: simdi
  "type":  "person",                 # serbest etiket: person/vehicle/motion...
  "pre_s": 10, "post_s": 20          # istege bagli, varsayilan 10/20
}

Cevap: {"ok":true, "clip_eta_s":95}
Islek: olay jsonl'e yazilir -> post_s+~75sn icinde ring tampondan tam kare klip
kesilir (-c copy) -> clips/<cam>/<gun>/<HHMMSS>_<type>.mp4 -> uploader S3'e
clips/ prefix'iyle yukler (EDGEWAY_UPLOAD_MODE=events|both ise).
Not: olay ani ring penceresinden eskiyse klip kesilemez (log'a duser).
