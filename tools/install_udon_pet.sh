#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pet_dir="${CODEX_HOME:-$HOME/.codex}/pets/udon"
state_file="${CODEX_HOME:-$HOME/.codex}/.codex-global-state.json"
codex_running=0
allow_running=0

if [ "${1:-}" = "--force-running" ]; then
  allow_running=1
fi

if ps -axo command | grep -F "/Applications/Codex.app/Contents/MacOS/Codex" | grep -v grep >/dev/null 2>&1; then
  codex_running=1
fi

if [ "$codex_running" -eq 1 ] && [ "$allow_running" -ne 1 ]; then
  cat >&2 <<'EOF'
Codex is currently running.

Quit Codex before installing Udon, then rerun:

  ./tools/install_udon_pet.sh

Reason: Codex keeps the selected avatar in memory and may overwrite
.codex-global-state.json after this script writes custom:udon.

If you intentionally want to install while Codex is open, rerun with:

  ./tools/install_udon_pet.sh --force-running

Then open Appearance/Pet settings or restart Codex if the old pet remains visible.
EOF
  exit 2
fi

mkdir -p "$pet_dir"
cp "$repo_root/codex-pets/udon/pet.json" "$repo_root/codex-pets/udon/spritesheet.webp" "$pet_dir/"

if command -v python3 >/dev/null 2>&1; then
  CODEX_STATE_FILE="$state_file" python3 - <<'PY'
import json
import os
from pathlib import Path

state_file = Path(os.environ["CODEX_STATE_FILE"])
state_file.parent.mkdir(parents=True, exist_ok=True)

if state_file.exists() and state_file.stat().st_size > 0:
    data = json.loads(state_file.read_text())
else:
    data = {}

state = data.setdefault("electron-persisted-atom-state", {})
state["selected-avatar-id"] = "custom:udon"
state_file.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
PY
else
  echo "python3 not found; installed files, but could not set selected-avatar-id automatically." >&2
fi

echo "Installed Udon pet to $pet_dir"
echo "Selected Codex avatar id: custom:udon"

if [ "$codex_running" -eq 1 ]; then
  echo "Codex is currently running because --force-running was used."
  echo "Open Appearance/Pet settings or restart Codex if the old pet remains visible."
fi
