#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/verify_tree.sh
HOST="${1:-pi@192.168.0.43}"
JUMP="${EDGEWAY_JUMP:-opi5}"
if [ -n "$JUMP" ]; then
  RSH="ssh -J $JUMP"
  SSH_ARGS=(-J "$JUMP")
else
  RSH="ssh"
  SSH_ARGS=()
fi
rsync -a --exclude .venv --exclude .git -e "$RSH" ./ "$HOST":~/edge_way/
ssh "${SSH_ARGS[@]}" -t "$HOST" "sudo rsync -a --exclude .venv ~/edge_way/ /opt/edgeway/ && sudo chown -R edgeway:edgeway /opt/edgeway && UNITS=\"edgeway-api edgeway-heartbeat\" && if systemctl is-enabled edgeway-recorder >/dev/null 2>&1; then UNITS=\"\$UNITS edgeway-recorder\"; else echo \"edgeway-recorder devre disi, atlandi\"; fi && sudo systemctl restart \$UNITS && sleep 8 && systemctl is-active \$UNITS"
