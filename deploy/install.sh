#!/usr/bin/env bash
set -euo pipefail
sudo useradd -r -s /usr/sbin/nologin edgeway 2>/dev/null || true
sudo mkdir -p /opt/edgeway /etc/edgeway /var/lib/edgeway/recordings
sudo rsync -a --delete --exclude .venv --exclude .git ./ /opt/edgeway/
cd /opt/edgeway
sudo python3 -m venv .venv
sudo .venv/bin/pip install -q -r requirements.txt
[ -f /etc/edgeway/edgeway.env ] || sudo cp .env.example /etc/edgeway/edgeway.env
sudo chmod 600 /etc/edgeway/edgeway.env
sudo chown -R edgeway:edgeway /opt/edgeway /var/lib/edgeway
sudo cp deploy/systemd/*.service deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now edgeway-api edgeway-recorder edgeway-heartbeat edgeway-uploader.timer
echo "kurulum tamam — /etc/edgeway/edgeway.env dosyasini doldurmayi unutma"
