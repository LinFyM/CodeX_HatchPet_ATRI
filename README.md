# CodeX HatchPet ATRI

A Codex-compatible v2 animated desktop pet inspired by ATRI from *ATRI -My Dear Moments-*.
The rebuild is based on a documented character brief and one unified visual model. Every running
frame is a complete-body drawing; the left-running cycle mirrors each approved right-running frame
without reversing temporal order, so anatomy and leg shading turn together.

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

The [`qa/`](qa/) folder contains the character brief, action mechanics, v2 atlas validation,
chroma-despill report, direction semantics, blind direction validation, continuity measurements,
mirror finalization, and full visual review sheets.

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
- a true two-step run: contact/down/passing/flight, then the opposite leg
- exact whole-frame left/right running mirrors with preserved temporal order and leg shading
- face/torso registration with less than 1 px horizontal anchor drift across the run loop
- at least 5 px transparent clearance around every running frame edge
- coherent crouch/launch/apex/descent/settle jump physics
- 16-direction look loop with zero continuity warnings and mirror-safe shading
- no structural validation errors

## Character and rights notice

ATRI and *ATRI -My Dear Moments-* are properties of their respective rights holders. This repository is an unofficial, noncommercial fan project. It is not affiliated with or endorsed by Aniplex, Frontwing, Makura, or the official production committee.

The included pet artwork was generated specifically for this project from original prompts and
temporary visual references; it is not extracted from official artwork. Do not use it commercially or
represent it as official artwork.
