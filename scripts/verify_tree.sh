#!/usr/bin/env bash
# Kazanim koruyucusu: deploy oncesi zorunlu. Eksik varsa deploy DURUR.
# Yeni bir ozellik eklendiginde buraya bir satir eklenir.
set -uo pipefail
cd "$(dirname "$0")/.."
FAIL=0
check() { grep -q "$2" "$1" 2>/dev/null || { echo "EKSIK: $1 -> $3"; FAIL=1; }; }
check web/index.html          "object-fit:fill"        "video fill (oran duzeltmesi)"
check web/index.html          "liveBadge"              "canli rozeti / kontrolsuz canli"
check web/index.html          "buildTimeline"          "gun cizelgesi (DVR akis)"
check web/index.html          "location.hostname"      "canli URL host duzeltmesi"
check web/index.html          "playAt"                 "kesintisiz segment akisi"
check edgeway/config.py       "except OSError"         "env okunamazsa ayakta kal"
check edgeway/config.py       "FFMPEG_EXTRA"           "ffmpeg ek parametre (hvc1)"
check edgeway/config.py       "MAX_STORAGE_GB"         "boyut tavani"
check edgeway/config.py       "def live_paths"         "canli path eslemesi"
check edgeway/recorder/segmenter.py "_pipe_masked"     "ffmpeg log maskesi"
check edgeway/recorder/segmenter.py "KEEP_LAST"        "segment-bazli retention"
check edgeway/uploader/s3sync.py "return 0 if fail == 0 else 1" "uploader durust exit"
check deploy/install.sh       "chmod 640"              "env 640 root:edgeway"
check deploy/install.sh       "edgeway-apply-env"      "sihirbaz sudo helper"
check edgeway/provision/routes.py "setup_apply"        "kurulum sihirbazi"
check infra/bootstrap_aws.sh  "command -v aws"         "aws cli on-kontrol"
check deploy/systemd/edgeway-uploader.service "TimeoutStartSec" "uploader zaman asimi"
check edgeway/api/main.py     "api_storage"            "depolama gorunurlugu"
check web/index.html          "relTime"                "goreli zaman etiketleri"
check web/index.html          "atlandi"                "bozuk segment atlama"
check web/index.html          "jogWrap"                "jog kadrani (ince ayar)"
check web/index.html          "setNote"                "tek gecici hata notu"
check web/index.html          "syncSeekTo"             "coklu kamera senkron playback"
[ $FAIL -eq 0 ] && echo "TUM KAZANIMLAR YERINDE ($(grep -c '^check ' "$0") kontrol)" || exit 1
