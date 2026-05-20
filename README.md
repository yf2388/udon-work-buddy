# Udon Work Buddy

Udon Work Buddy is a custom Codex/OpenPet-style desktop pet package based on Udon, a gray-black Shih Tzu. It includes a Codex-compatible 8x9 spritesheet, manifest, preview GIFs, and the local build script used to regenerate the pet atlas.

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

## Install

From this repository root:

```bash
./tools/install_udon_pet.sh
```

Or copy manually:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/pets/udon"
cp codex-pets/udon/pet.json codex-pets/udon/spritesheet.webp "${CODEX_HOME:-$HOME/.codex}/pets/udon/"
```

Then restart Codex if the pet list does not refresh, and choose `Udon` from Settings -> Appearance -> Pet.

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
