#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pet_dir="${CODEX_HOME:-$HOME/.codex}/pets/udon"

mkdir -p "$pet_dir"
cp "$repo_root/codex-pets/udon/pet.json" "$repo_root/codex-pets/udon/spritesheet.webp" "$pet_dir/"

echo "Installed Udon pet to $pet_dir"
