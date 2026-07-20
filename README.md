# edgeWAY Pro2

Mevcut kamera/DVR sistemine dokunmadan yanina takilan kutu: RTSP alir, yerel SSD'ye
kaydeder (90 gun), sifreleyip AWS'ye yedekler (S3 -> Glacier IR -> Deep Archive),
web portaldan canli izleme + geri gosterim sunar.

## Bilesenler
- edgeway/api        FastAPI: /health, kamera & kayit API'si, /media oynatma, S3 presign, web portal
- edgeway/recorder   ffmpeg passthrough segmenter (60sn mp4) + retention (gun/disk esigi)
- edgeway/uploader   S3 sync (SSE, sidecar .up isareti, kopukta bekler)
- edgeway/heartbeat  15sn nabiz + termal esik aksiyonlari (70/78/82C)
- edgeway/mediamtx_common  version-aware mediamtx.yml uretici (tum Mind'larla ortak)
- web/               MVP portal (hls.js canli + segment geri gosterim)
- deploy/            systemd birimleri + install.sh (RPi/OPi5)
- infra/             S3 bucket bootstrap + lifecycle policy
- db/                Supabase bulut semasi (sites/devices/heartbeats/alerts)

## Mac'te gelistirme
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    EDGEWAY_ENV=./dev.env .venv/bin/uvicorn edgeway.api.main:app --reload --port 8080
dev.env icin .env.example'i kopyala (repo'ya girmez, .gitignore'da).
Tarayici: http://127.0.0.1:8080

## Cihaza kurulum (RPi)
    rsync -a --exclude .venv --exclude .git ./ pi@100.80.46.1:~/edge_way/
    ssh pi@100.80.46.1 "cd ~/edge_way && ./deploy/install.sh"
    sudo nano /etc/edgeway/edgeway.env   # kamera URL + token'lari doldur (600)

## AWS
    cd infra && ./bootstrap_aws.sh edgeway-<site> eu-central-1

## Guvenlik kurallari
- Secret'lar SADECE /etc/edgeway/edgeway.env (600) — koda/log'a asla
- Debug ciktisi paylasmadan: sed -E 's/eyJ[A-Za-z0-9._-]+/MASKED/g'
- API_TOKEN bos birakma (bos = dev modu, auth kapali)

## Yol haritasi
Sprint 1: DVR-direkt saha testi, sqlite segment indeksi, WebRTC canli
Sprint 2: Supabase multi-tenant portal (edgeway.ant-soft.uk), watchdog+TalkMind
Sprint 3: iOS uygulamasi (Swift, HLS player + push bildirim)
