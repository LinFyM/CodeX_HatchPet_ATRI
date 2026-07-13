#!/usr/bin/env python3
"""Validate the complete ATRI Codex v2 sprite atlas."""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageOps


CELL_WIDTH = 192
CELL_HEIGHT = 208
COLUMNS = 8
ROWS = 11
USED_FRAMES = (7, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8)
MAX_SECONDARY_COMPONENT_PIXELS = 20
MIN_CHARACTER_PIXELS = 5_000
MAX_RUN_EYE_X_RANGE = 1.5
MAX_MATCHED_GAIT_PHASE_Y_DELTA = 5.0
MIN_RUN_HORIZONTAL_MARGIN = 4
MIN_RUN_VERTICAL_MARGIN = 3


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
                px, py = queue.popleft()
                points.append((px, py))
                for nx, ny in (
                    (px - 1, py),
                    (px + 1, py),
                    (px, py - 1),
                    (px, py + 1),
                ):
                    if (
                        0 <= nx < alpha.width
                        and 0 <= ny < alpha.height
                        and pixels[nx, ny] > 8
                        and (nx, ny) not in visited
                    ):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            xs, ys = zip(*points)
            components.append((len(points), (min(xs), min(ys), max(xs), max(ys))))
    return sorted(components, reverse=True)


def frame(atlas: Image.Image, row: int, column: int) -> Image.Image:
    return atlas.crop(
        (
            column * CELL_WIDTH,
            row * CELL_HEIGHT,
            (column + 1) * CELL_WIDTH,
            (row + 1) * CELL_HEIGHT,
        )
    )


def run_eye_anchor(sprite: Image.Image) -> tuple[float, float]:
    """Locate ATRI's visible iris instead of treating wind-swept hair as an anchor."""

    candidates: set[tuple[int, int]] = set()
    for y in range(25, 100):
        for x in range(72, 180):
            red, green, blue, alpha = sprite.getpixel((x, y))
            if (
                alpha > 120
                and red > 70
                and red > green * 1.32
                and red > blue * 0.95
                and blue > green * 0.75
            ):
                candidates.add((x, y))

    components: list[list[tuple[int, int]]] = []
    while candidates:
        start = candidates.pop()
        queue = deque([start])
        points: list[tuple[int, int]] = []
        while queue:
            px, py = queue.popleft()
            points.append((px, py))
            for neighbor in (
                (px - 1, py),
                (px + 1, py),
                (px, py - 1),
                (px, py + 1),
            ):
                if neighbor in candidates:
                    candidates.remove(neighbor)
                    queue.append(neighbor)
        components.append(points)

    iris_candidates: list[list[tuple[int, int]]] = []
    for points in components:
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        width = max(xs) - min(xs) + 1
        height = max(ys) - min(ys) + 1
        center_y = sum(ys) / len(ys)
        if (
            20 <= len(points) <= 70
            and 4 <= width <= 8
            and 8 <= height <= 13
            and 50 <= center_y <= 90
        ):
            iris_candidates.append(points)

    if not iris_candidates:
        raise ValueError("running frame has no detectable ATRI iris anchor")
    iris = max(iris_candidates, key=len)
    return (
        sum(x for x, _ in iris) / len(iris),
        sum(y for _, y in iris) / len(iris),
    )


def pixel_difference_ratio(first: Image.Image, second: Image.Image) -> float:
    difference = ImageChops.difference(first, second)
    pixels = difference.load()
    differing = sum(
        1
        for y in range(difference.height)
        for x in range(difference.width)
        if any(channel > 12 for channel in pixels[x, y])
    )
    return differing / (difference.width * difference.height)


def main() -> int:
    atlas_path = Path(sys.argv[1] if len(sys.argv) > 1 else "pet/spritesheet.webp")
    atlas = Image.open(atlas_path).convert("RGBA")
    errors: list[str] = []

    expected_size = (COLUMNS * CELL_WIDTH, ROWS * CELL_HEIGHT)
    if atlas.size != expected_size:
        errors.append(f"atlas size {atlas.size} != {expected_size}")
        print("\n".join(errors), file=sys.stderr)
        return 1

    transparent_rgb_residue = 0
    atlas_pixels = atlas.load()
    for y in range(atlas.height):
        for x in range(atlas.width):
            red, green, blue, alpha = atlas_pixels[x, y]
            if alpha == 0 and (red or green or blue):
                transparent_rgb_residue += 1
    if transparent_rgb_residue:
        errors.append(f"transparent RGB residue pixels={transparent_rgb_residue}")

    for row, used_count in enumerate(USED_FRAMES):
        areas: list[int] = []
        for column in range(COLUMNS):
            sprite = frame(atlas, row, column)
            alpha = sprite.getchannel("A")
            area = sum(alpha.histogram()[1:])
            if column >= used_count:
                if area:
                    errors.append(f"row {row} column {column}: unused cell has {area} alpha pixels")
                continue
            areas.append(area)
            if area < MIN_CHARACTER_PIXELS:
                errors.append(f"row {row} column {column}: character area too small ({area})")
            components = connected_components(alpha)
            if not components:
                errors.append(f"row {row} column {column}: no connected character component")
                continue
            for size, bbox in components[1:]:
                if size > MAX_SECONDARY_COMPONENT_PIXELS:
                    errors.append(
                        f"row {row} column {column}: detached component size={size} bbox={bbox}"
                    )
        if areas and max(areas) / min(areas) > 1.7:
            errors.append(
                f"row {row}: frame area ratio too large ({max(areas) / min(areas):.2f})"
            )

    running_right = [frame(atlas, 1, column) for column in range(8)]
    running_left = [frame(atlas, 2, column) for column in range(8)]
    for column, (right, left) in enumerate(zip(running_right, running_left)):
        if ImageChops.difference(left, ImageOps.mirror(right)).getbbox() is not None:
            errors.append(f"running-left frame {column}: not an exact whole-frame mirror")

        bbox = right.getchannel("A").getbbox()
        if bbox is None:
            continue
        left_margin, top_margin = bbox[0], bbox[1]
        right_margin = CELL_WIDTH - bbox[2]
        bottom_margin = CELL_HEIGHT - bbox[3]
        if min(left_margin, right_margin) < MIN_RUN_HORIZONTAL_MARGIN:
            errors.append(
                f"running-right frame {column}: horizontal margin too small "
                f"({left_margin}px, {right_margin}px)"
            )
        if min(top_margin, bottom_margin) < MIN_RUN_VERTICAL_MARGIN:
            errors.append(
                f"running-right frame {column}: vertical margin too small "
                f"({top_margin}px, {bottom_margin}px)"
            )

    anchors = [run_eye_anchor(sprite) for sprite in running_right]
    eye_xs = [anchor[0] for anchor in anchors]
    if max(eye_xs) - min(eye_xs) > MAX_RUN_EYE_X_RANGE:
        errors.append(
            "running-right: rigid body drifts horizontally; "
            f"eye anchor range={max(eye_xs) - min(eye_xs):.2f}px"
        )

    # The second four frames repeat the same gait phases with the opposite leg.
    for first, second in zip(range(4), range(4, 8)):
        y_delta = abs(anchors[first][1] - anchors[second][1])
        if y_delta > MAX_MATCHED_GAIT_PHASE_Y_DELTA:
            errors.append(
                f"running-right phases {first}/{second}: mismatched body height "
                f"delta={y_delta:.2f}px"
            )

    # Contact -> down -> passing -> flight: the torso drops under load, then rises.
    for contact, down, passing, flight in ((0, 1, 2, 3), (4, 5, 6, 7)):
        contact_y, down_y, passing_y, flight_y = (
            anchors[index][1] for index in (contact, down, passing, flight)
        )
        if not 6 <= down_y - contact_y <= 20:
            errors.append(
                f"running-right {contact}->{down}: implausible load drop "
                f"{down_y - contact_y:.2f}px"
            )
        if not 8 <= down_y - passing_y <= 22:
            errors.append(
                f"running-right {down}->{passing}: implausible recovery rise "
                f"{down_y - passing_y:.2f}px"
            )
        if abs(passing_y - flight_y) > 3:
            errors.append(
                f"running-right {passing}->{flight}: abrupt flight height change "
                f"{abs(passing_y - flight_y):.2f}px"
            )

    for column in range(8):
        next_column = (column + 1) % 8
        difference_ratio = pixel_difference_ratio(
            running_right[column], running_right[next_column]
        )
        if not 0.08 <= difference_ratio <= 0.50:
            errors.append(
                f"running-right {column}->{next_column}: implausible frame difference "
                f"ratio={difference_ratio:.3f}"
            )

    jump_bottoms = []
    for column in range(USED_FRAMES[4]):
        bbox = frame(atlas, 4, column).getchannel("A").getbbox()
        if bbox is None:
            errors.append(f"jump frame {column}: empty")
            continue
        jump_bottoms.append(bbox[3])
    if len(jump_bottoms) == 5:
        crouch, launch, apex, descent, settle = jump_bottoms
        coherent_jump = (
            crouch >= 200
            and crouch - launch >= 4
            and launch - apex >= 20
            and descent - apex >= 20
            and descent >= 200
            and settle >= 200
        )
        if not coherent_jump:
            errors.append(
                "jump arc is not crouch/launch/apex/descent/settle: "
                f"bottoms={jump_bottoms}"
            )

    # Directions on the left half are whole-frame mirrors of their right-half
    # peers. A tiny registration-only translation is allowed because the
    # neutral/front frame has natural asymmetry; forcing identical cell x
    # coordinates makes the 337.5 -> 000 wrap visibly worse.
    for row_10_column, row_9_column in enumerate(range(7, 0, -1), start=1):
        left_look = frame(atlas, 10, row_10_column)
        mirrored_right = ImageOps.mirror(frame(atlas, 9, row_9_column))
        left_bbox = left_look.getchannel("A").getbbox()
        mirrored_bbox = mirrored_right.getchannel("A").getbbox()
        if left_bbox is None or mirrored_bbox is None:
            errors.append(
                f"look direction mirror pair contains an empty cell: {row_10_column}"
            )
            continue
        if (
            left_bbox[2] - left_bbox[0],
            left_bbox[3] - left_bbox[1],
        ) != (
            mirrored_bbox[2] - mirrored_bbox[0],
            mirrored_bbox[3] - mirrored_bbox[1],
        ):
            errors.append(
                f"look direction mirror geometry mismatch: row10 column {row_10_column}"
            )
            continue
        offset_x = left_bbox[0] - mirrored_bbox[0]
        offset_y = left_bbox[1] - mirrored_bbox[1]
        if abs(offset_x) > 3 or abs(offset_y) > 1:
            errors.append(
                "look direction mirror registration shift too large: "
                f"row10 column {row_10_column} offset=({offset_x}, {offset_y})"
            )
            continue
        translated = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
        translated.paste(mirrored_right, (offset_x, offset_y))
        if ImageChops.difference(left_look, translated).getbbox():
            errors.append(
                "look direction mirror mismatch: "
                f"row10 column {row_10_column} vs row9 column {row_9_column} "
                f"after offset ({offset_x}, {offset_y})"
            )

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(
        "PASS complete ATRI atlas: 8x11 layout, intact connected characters, "
        "stable rigid-body running loop, whole-frame gait/look mirrors, safe cell "
        "margins, and coherent jump arc"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
