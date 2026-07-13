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
RUNNING_RIGHT_ROW = 1
MIN_FRAGMENT_PIXELS = 20
FRAME_7_ARTIFACT_ZONES = ((18, 39, 27, 80), (166, 40, 174, 77))
LOWER_LEG_START_Y = 175
MIRRORED_CENTROID_TOLERANCE = 8.0


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


def lower_leg_centroid_x(frame: Image.Image) -> float:
    """Return the horizontal centroid of opaque pixels below the skirt."""
    alpha = frame.getchannel("A")
    pixels = alpha.load()
    xs = [
        x
        for y in range(LOWER_LEG_START_Y, frame.height)
        for x in range(frame.width)
        if pixels[x, y] > 32
    ]
    if not xs:
        raise ValueError("running frame has no visible lower-leg pixels")
    return sum(xs) / len(xs)


def main() -> int:
    spritesheet = Path(sys.argv[1] if len(sys.argv) > 1 else "pet/spritesheet.webp")
    image = Image.open(spritesheet).convert("RGBA")
    errors: list[str] = []

    running_right_frames: list[Image.Image] = []
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
                RUNNING_RIGHT_ROW * CELL_HEIGHT,
                (column + 1) * CELL_WIDTH,
                (RUNNING_RIGHT_ROW + 1) * CELL_HEIGHT,
            )
        )
        running_right_frames.append(running_right)
        if ImageChops.difference(frame, ImageOps.mirror(running_right)).getbbox() is not None:
            errors.append(f"running-left frame {column}: does not mirror running-right counterpart")

    centroids = [lower_leg_centroid_x(frame) for frame in running_right_frames]
    mirrored_centroid_sum = CELL_WIDTH - 1
    for first_half_column in range(4):
        second_half_column = first_half_column + 4
        pair_sum = centroids[first_half_column] + centroids[second_half_column]
        if abs(pair_sum - mirrored_centroid_sum) > MIRRORED_CENTROID_TOLERANCE:
            errors.append(
                "running-right gait phases "
                f"{first_half_column}/{second_half_column}: lower-leg centroids are not opposing "
                f"({centroids[first_half_column]:.1f} + {centroids[second_half_column]:.1f} != "
                f"{mirrored_centroid_sum})"
            )

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(
        "PASS running frames alternate opposing leg phases; "
        "running-left mirrors running-right without detached fragments"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
