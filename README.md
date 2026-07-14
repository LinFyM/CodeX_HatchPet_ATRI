# CodeX HatchPet ATRI

A Codex-compatible v2 animated desktop pet inspired by ATRI from *ATRI -My Dear Moments-*.
The current atlas uses one consistent chibi model and warm ash-silver palette across all actions.
The run uses an animated upper body and a compact contact/load/pass/flight cycle; the left cycle is
an exact whole-frame mirror, so body direction, anatomy, and warm near/far-leg shading turn together.

![ATRI animation contact sheet](qa/contact-sheet-extended.png)

## Package

The installable pet is in [`pet/`](pet/):

- `pet.json` declares `spriteVersionNumber: 2`.
- `spritesheet.webp` is a transparent `1536 × 2288` atlas using `192 × 208` cells.
- Rows 0–8 contain the nine standard Codex animation states.
- Rows 9–10 contain 16 clockwise look directions.

## Install

Copy the package into your Codex pet directory:

```bash
mkdir -p ~/.codex/pets/atri
cp pet/pet.json ~/.codex/pets/atri/pet.json
cp pet/spritesheet.webp ~/.codex/pets/atri/spritesheet.webp
```

Restart Codex if the pet does not appear immediately.

## Validation

The [`qa/`](qa/) folder contains the character brief, action mechanics, v2 atlas validator,
chroma/alpha report, direction semantics, continuity measurements, full visual review sheets, and a
manual motion-review manifest bound to the exact atlas SHA-256.

Run the complete structural validator with:

```bash
python3 qa/validate_pet_atlas.py pet/spritesheet.webp
```

Deterministic validation confirms:

- atlas dimensions: `1536 × 2288`
- layout: 8 columns × 11 rows
- sprite contract: v2
- transparent RGB residue: 0 pixels
- complete connected character anatomy in every used frame
- a canonical cross-action head/body scale with a dedicated proportion regression gate
- no large purple, fuchsia, or chroma-key component in any used frame
- a compact two-step jog: contact/load/pass/short-flight, then the same lower-body geometry with the
  anatomical near/far legs exchanged while the upper body continues moving
- exact whole-frame left/right running mirrors with preserved temporal order and leg shading
- neutral-action eye-depth range of `8.853 px`; idle/run contact heights of `198/194 px`
- run torso motion of `0.980 px` horizontally and `2.260 px` vertically
- adjacent run silhouette IoU of `0.848–0.895` and a maximum warm-leg span of `57 px`
- zero cool purple/blue pixels in every running-leg region
- coherent crouch/launch/vertical-tuck-apex/descent/landing-absorption physics
- exact unshifted look mirrors and a continuous clockwise 16-direction loop
- SHA-bound native-size and enlarged frame-strip review of every action
- no structural validation errors

## Character and rights notice

ATRI and *ATRI -My Dear Moments-* are properties of their respective rights holders. This repository is an unofficial, noncommercial fan project. It is not affiliated with or endorsed by Aniplex, Frontwing, Makura, or the official production committee.

The included pet artwork was generated specifically for this project from original prompts and
temporary visual references; it is not extracted from official artwork. Do not use it commercially or
represent it as official artwork.
