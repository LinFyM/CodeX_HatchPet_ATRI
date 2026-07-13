#!/usr/bin/env python3
"""Enforce final-cell mirrors after atlas geometry registration.

The upstream atlas assembler normalizes every look cell around its lower-body
center. That is useful for arbitrary source art, but it can translate an
already mirrored left-facing frame by a pixel or two. This finalization step
runs after registration and before chroma despill. Running frames stay at the
same cell coordinates; look frames retain the assembler's small registration
translation while body, limbs, shading, hair, and antialiased edges remain an
exact whole-frame mirror under that translation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_SIZE = (1536, 2288)


def cell_box(row: int, column: int) -> tuple[int, int, int, int]:
    return (
        column * CELL_WIDTH,
        row * CELL_HEIGHT,
        (column + 1) * CELL_WIDTH,
        (row + 1) * CELL_HEIGHT,
    )


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0 and (red or green or blue):
                pixels[x, y] = (0, 0, 0, 0)
    return rgba


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with Image.open(args.input) as opened:
        atlas = opened.convert("RGBA")
    if atlas.size != ATLAS_SIZE:
        raise SystemExit(f"expected atlas {ATLAS_SIZE}, got {atlas.size}")

    # Running-left uses the same temporal order as running-right. The app
    # changes screen velocity, so reversing the strip would break cadence.
    for column in range(8):
        right = atlas.crop(cell_box(1, column))
        atlas.paste(ImageOps.mirror(right), cell_box(2, column))

    # 202.5..337.5 degrees mirror 157.5..22.5 degrees respectively. Preserve
    # the registered left frame's bbox position: a small whole-frame shift is
    # intentional here because it smooths the asymmetric 337.5 -> 000 wrap.
    for left_column, right_column in enumerate(range(7, 0, -1), start=1):
        registered_left = atlas.crop(cell_box(10, left_column))
        right = atlas.crop(cell_box(9, right_column))
        mirrored = ImageOps.mirror(right)
        registered_bbox = registered_left.getchannel("A").getbbox()
        mirrored_bbox = mirrored.getchannel("A").getbbox()
        if registered_bbox is None or mirrored_bbox is None:
            raise SystemExit("look mirror pair contains an empty frame")
        if (
            registered_bbox[2] - registered_bbox[0],
            registered_bbox[3] - registered_bbox[1],
        ) != (
            mirrored_bbox[2] - mirrored_bbox[0],
            mirrored_bbox[3] - mirrored_bbox[1],
        ):
            raise SystemExit("look mirror pair geometry changed during registration")
        offset = (
            registered_bbox[0] - mirrored_bbox[0],
            registered_bbox[1] - mirrored_bbox[1],
        )
        translated = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
        translated.paste(mirrored, offset)
        atlas.paste(translated, cell_box(10, left_column))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    clear_transparent_rgb(atlas).save(args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
