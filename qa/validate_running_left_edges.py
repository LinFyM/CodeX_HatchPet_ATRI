#!/usr/bin/env python3
"""Reject detached sprite fragments in running-left animation frames."""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageOps


CELL_WIDTH = 192
CELL_HEIGHT = 208
RUNNING_LEFT_ROW = 2
MIN_FRAGMENT_PIXELS = 20
FRAME_7_ARTIFACT_ZONES = ((18, 39, 27, 80), (166, 40, 174, 77))


def connected_components(alpha: Image.Image) -> list[tuple[int, tuple[int, int, int, int]]]:
    pixels = alpha.load()
    visited: set[tuple[int, int]] = set()
    components: list[tuple[int, tuple[int, int, int, int]]] = []

    for y in range(alpha.height):
        for x in range(alpha.width):
            if pixels[x, y] <= 8 or (x, y) in visited:
                continue

            queue = deque([(x, y)])
            visited.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                point = queue.popleft()
                points.append(point)
                px, py = point
                for neighbor in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    nx, ny = neighbor
                    if (
                        0 <= nx < alpha.width
                        and 0 <= ny < alpha.height
                        and neighbor not in visited
                        and pixels[nx, ny] > 8
                    ):
                        visited.add(neighbor)
                        queue.append(neighbor)

            xs, ys = zip(*points)
            components.append((len(points), (min(xs), min(ys), max(xs), max(ys))))

    return sorted(components, reverse=True)


def main() -> int:
    spritesheet = Path(sys.argv[1] if len(sys.argv) > 1 else "pet/spritesheet.webp")
    image = Image.open(spritesheet).convert("RGBA")
    errors: list[str] = []

    for column in range(8):
        frame = image.crop(
            (
                column * CELL_WIDTH,
                RUNNING_LEFT_ROW * CELL_HEIGHT,
                (column + 1) * CELL_WIDTH,
                (RUNNING_LEFT_ROW + 1) * CELL_HEIGHT,
            )
        )
        components = connected_components(frame.getchannel("A"))
        for size, bbox in components[1:]:
            if size >= MIN_FRAGMENT_PIXELS:
                errors.append(f"running-left frame {column}: detached fragment size={size} bbox={bbox}")

        if column == 7:
            alpha = frame.getchannel("A")
            for zone in FRAME_7_ARTIFACT_ZONES:
                residue = sum(alpha.crop(zone).histogram()[1:])
                if residue:
                    errors.append(f"running-left frame 7: {residue} residual alpha pixels in artifact zone={zone}")

        running_right = image.crop(
            (
                column * CELL_WIDTH,
                CELL_HEIGHT,
                (column + 1) * CELL_WIDTH,
                2 * CELL_HEIGHT,
            )
        )
        if ImageChops.difference(frame, ImageOps.mirror(running_right)).getbbox() is not None:
            errors.append(f"running-left frame {column}: does not mirror running-right counterpart")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print("PASS running-left frames mirror running-right frames without detached fragments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
