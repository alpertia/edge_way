#!/usr/bin/env bash
# USB SSD'yi EdgeWay kayit diski yapar (cihazda sudo ile calistir).
# Kullanim: sudo ./attach_ssd.sh [/dev/sda] [GB tavani, vars 400]
# Yapilanlar: (bos ise) bolumle+ext4, fstab'a UUID ile ekle (nofail),
# mevcut kayitlari tasi, /var/lib/edgeway/recordings -> SSD symlink, tavani yukselt.
set -euo pipefail
DEV="${1:-/dev/sda}"
CAP="${2:-400}"
[ -b "$DEV" ] || { echo "HATA: $DEV bulunamadi — USB diski tak ve tekrar dene"; exit 1; }
PART="${DEV}1"
if ! blkid "$PART" >/dev/null 2>&1; then
  echo "UYARI: $DEV bos gorunuyor — bolumlenip ext4 yapilacak, DISKTEKI HER SEY SILINIR."
  echo "Vazgecmek icin 8 saniye icinde Ctrl+C..."; sleep 8
  parted -s "$DEV" mklabel gpt mkpart primary ext4 0% 100%
  sleep 2
  mkfs.ext4 -F -L EDGEWAY "$PART"
fi
UUID=$(blkid -s UUID -o value "$PART")
MNT=/mnt/edgeway-ssd
mkdir -p "$MNT"
grep -q "$UUID" /etc/fstab || echo "UUID=$UUID $MNT ext4 defaults,noatime,nofail 0 2" >> /etc/fstab
systemctl daemon-reload
mountpoint -q "$MNT" || mount "$MNT"
systemctl stop edgeway-recorder edgeway-uploader.timer
mkdir -p "$MNT/recordings"
if [ -d /var/lib/edgeway/recordings ] && [ ! -L /var/lib/edgeway/recordings ]; then
  rsync -a /var/lib/edgeway/recordings/ "$MNT/recordings/" || true
  rm -rf /var/lib/edgeway/recordings
fi
ln -sfn "$MNT/recordings" /var/lib/edgeway/recordings
chown -R edgeway:edgeway "$MNT/recordings"
sed -i "s/^EDGEWAY_MAX_STORAGE_GB=.*/EDGEWAY_MAX_STORAGE_GB=$CAP/" /etc/edgeway/edgeway.env
systemctl start edgeway-recorder edgeway-uploader.timer
echo "SSD aktif: $MNT — kayit tavani ${CAP}GB"
df -h "$MNT" | tail -1
# NOT: SSD sokulur/arizalanirsa symlink SD'ye yazmaya dusebilir; watchdog disk metrigi bunu gosterir.
# Urun surumu: udev kuraliyla tam otomatik tak-calis (yol haritasi).
