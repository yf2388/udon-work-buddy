# Udon Work Buddy

Udon Work Buddy is a custom Codex/OpenPet-style desktop pet package based on Udon, a gray-black Shih Tzu. It includes a Codex-compatible 8x9 spritesheet, manifest, preview GIFs, and the local build script used to regenerate the pet atlas.

Repository:

```text
git@github.com:yf2388/udon-work-buddy.git
```

## Codex Auto Configuration

Use this section when another Codex agent only receives the GitHub repository address and needs to configure the pet automatically.

Goal: install the `Udon` custom desktop pet into the active Codex home so the local Codex app can load it.

Expected result:

- `${CODEX_HOME:-$HOME/.codex}/pets/udon/pet.json` exists.
- `${CODEX_HOME:-$HOME/.codex}/pets/udon/spritesheet.webp` exists.
- `${CODEX_HOME:-$HOME/.codex}/.codex-global-state.json` contains `"selected-avatar-id":"custom:udon"`.
- Codex can show `Udon` in the pet selection UI after restart or refresh.

Recommended agent workflow:

1. Clone the repository into a temporary or user-approved workspace.

   ```bash
   git clone git@github.com:yf2388/udon-work-buddy.git
   cd udon-work-buddy
   ```

2. Run the installer from the repository root.

   ```bash
   ./tools/install_udon_pet.sh
   ```

3. Verify the installed files.

   ```bash
   test -f "${CODEX_HOME:-$HOME/.codex}/pets/udon/pet.json"
   test -f "${CODEX_HOME:-$HOME/.codex}/pets/udon/spritesheet.webp"
   ```

4. If Codex is already running and the pet does not appear immediately, restart Codex or open the appearance/pet settings once to refresh the avatar overlay.

Non-interactive one-liner:

```bash
git clone git@github.com:yf2388/udon-work-buddy.git && cd udon-work-buddy && ./tools/install_udon_pet.sh
```

If SSH access to GitHub is not configured, use the HTTPS URL instead:

```bash
git clone https://github.com/yf2388/udon-work-buddy.git
cd udon-work-buddy
./tools/install_udon_pet.sh
```

Notes for Codex agents:

- Do not initialize git in the parent workspace when configuring this pet.
- Do not copy unrelated workspace files into this repository.
- The installer writes `pet.json` and `spritesheet.webp` into the Codex pet directory, then sets `selected-avatar-id` to `custom:udon`.
- Respect `CODEX_HOME` when it is set; otherwise use `$HOME/.codex`.
- Ask for elevated filesystem permission only if writing to the Codex home is blocked by the local sandbox.

## Installation Pitfalls

These are the common issues that made the first installation look like it had not worked.

### Udon files exist, but Codex still shows the old pet

Installing a custom pet has two separate parts:

1. Copy the custom pet files into `${CODEX_HOME:-$HOME/.codex}/pets/udon/`.
2. Set the persisted Codex avatar selection to `custom:udon`.

If only the files are copied, Codex can discover Udon in the custom pet list, but the active pet may still fall back to the built-in `codex` avatar. The installer handles both steps automatically.

Verify the selected pet:

```bash
python3 - <<'PY'
import json
import os
from pathlib import Path

state_file = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / ".codex-global-state.json"
state = json.loads(state_file.read_text()).get("electron-persisted-atom-state", {})
print(state.get("selected-avatar-id"))
PY
```

Expected output:

```text
custom:udon
```

If the value is missing or different, run:

```bash
./tools/install_udon_pet.sh
```

### Running Codex may cache the old overlay

The floating desktop pet overlay can keep the old avatar in memory while Codex is already running. After installation, if the screen still shows the old pet:

1. Open Codex appearance/pet settings once to force a refresh, or
2. Restart Codex.

The persisted setting should be checked before assuming the spritesheet is wrong.

### Running Codex can overwrite a direct state-file edit

Codex stores `selected-avatar-id` in its persisted atom state under `.codex-global-state.json`, but the running app also keeps this state in memory. If a script edits `.codex-global-state.json` while Codex is already running, the app may later flush its old in-memory value back to disk and remove the new `custom:udon` selection.

The most reliable sequence is:

1. Quit Codex.
2. Run `./tools/install_udon_pet.sh`.
3. Start Codex again.

If Codex must stay open, run the installer, then immediately open Appearance/Pet settings or restart Codex if the overlay still shows the old pet.

Check whether Codex rewrote the value:

```bash
python3 - <<'PY'
import json
import os
from pathlib import Path

state_file = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / ".codex-global-state.json"
state = json.loads(state_file.read_text()).get("electron-persisted-atom-state", {})
print(state.get("selected-avatar-id"))
PY
```

### Manual copy is not enough

This command only installs the asset files:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/pets/udon"
cp codex-pets/udon/pet.json codex-pets/udon/spritesheet.webp "${CODEX_HOME:-$HOME/.codex}/pets/udon/"
```

It does not select Udon as the active pet. Prefer the installer unless you also update `.codex-global-state.json` yourself.

## Preview

![Udon contact sheet](codex-pets/udon/contact-sheet.png)

Selected animation previews:

![waving](codex-pets/udon/previews/waving.gif)
![jumping](codex-pets/udon/previews/jumping.gif)
![review](codex-pets/udon/previews/review.gif)

## Pet States

The spritesheet follows the Codex custom pet contract:

- Canvas: `1536x1872`
- Grid: `8` columns x `9` rows
- Cell: `192x208`
- Format: `spritesheet.webp`
- Manifest: `pet.json`

Rows:

1. `idle`
2. `running-right`
3. `running-left`
4. `waving`
5. `jumping`
6. `failed`
7. `waiting`
8. `running` / working
9. `review`

## Manual Install

From this repository root:

```bash
./tools/install_udon_pet.sh
```

Or copy manually:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/pets/udon"
cp codex-pets/udon/pet.json codex-pets/udon/spritesheet.webp "${CODEX_HOME:-$HOME/.codex}/pets/udon/"
```

If using manual copy, also set `selected-avatar-id` to `custom:udon` in `${CODEX_HOME:-$HOME/.codex}/.codex-global-state.json`, or choose `Udon` from Settings -> Appearance -> Pet. Then restart Codex if the avatar overlay does not refresh.

## Rebuild

The build script uses the checked-in source sheets under `codex-pets/udon/` and writes a regenerated atlas plus preview artifacts.

```bash
python3 tools/build_udon_pet.py
```

The script requires Pillow:

```bash
python3 -m pip install Pillow
```

## Files

- `codex-pets/udon/pet.json`: Codex pet manifest.
- `codex-pets/udon/spritesheet.webp`: production custom-pet spritesheet.
- `codex-pets/udon/contact-sheet.png`: visual QA sheet.
- `codex-pets/udon/previews/*.gif`: per-state animation previews.
- `codex-pets/udon/udon-*.png`: source/reference sheets used by the build script.
- `tools/build_udon_pet.py`: deterministic atlas/preview builder.
- `tools/install_udon_pet.sh`: local Codex install helper.
