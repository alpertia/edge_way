#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/verify_tree.sh
HOST="${1:-pi@100.80.46.1}"
rsync -a --exclude .venv --exclude .git ./ "$HOST":~/edge_way/
ssh -t "$HOST" "sudo rsync -a --exclude .venv ~/edge_way/ /opt/edgeway/ && sudo chown -R edgeway:edgeway /opt/edgeway && sudo systemctl restart edgeway-api edgeway-recorder edgeway-heartbeat && sleep 8 && systemctl is-active edgeway-api edgeway-recorder edgeway-heartbeat"
