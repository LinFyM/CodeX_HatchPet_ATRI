# CodeX HatchPet ATRI

A Codex-compatible v2 animated desktop pet inspired by ATRI from *ATRI -My Dear Moments-*.

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

The [`qa/`](qa/) folder contains the v2 atlas validation, chroma-despill report, direction semantics, blind direction validation, continuity measurements, and visual review sheets.

Deterministic validation confirms:

- atlas dimensions: `1536 × 2288`
- layout: 8 columns × 11 rows
- sprite contract: v2
- transparent RGB residue: 0 pixels
- no structural validation errors

## Character and rights notice

ATRI and *ATRI -My Dear Moments-* are properties of their respective rights holders. This repository is an unofficial, noncommercial fan project. It is not affiliated with or endorsed by Aniplex, Frontwing, Makura, or the official production committee.

The included pet artwork was generated for this project from a user-provided visual reference. Do not use it commercially or represent it as official artwork.

