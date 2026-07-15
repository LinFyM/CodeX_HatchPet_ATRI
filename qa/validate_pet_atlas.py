#!/usr/bin/env python3
"""Validate structural, motion, palette, and mirror invariants of the ATRI pet."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageOps


CELL_WIDTH = 192
CELL_HEIGHT = 208
COLUMNS = 8
ROWS = 11
ATLAS_SIZE = (COLUMNS * CELL_WIDTH, ROWS * CELL_HEIGHT)
USED_FRAMES = (7, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8)
DEFAULT_ATLAS = Path("pet/spritesheet.webp")
REVIEW_MANIFEST = Path("qa/motion-review.json")
MIN_CHARACTER_PIXELS = 5_000
MAX_SECONDARY_COMPONENT_PIXELS = 20


def cell(atlas: Image.Image, row: int, column: int) -> Image.Image:
    return atlas.crop(
        (
            column * CELL_WIDTH,
            row * CELL_HEIGHT,
            (column + 1) * CELL_WIDTH,
            (row + 1) * CELL_HEIGHT,
        )
    )


def alpha_pixels(sprite: Image.Image, threshold: int = 8) -> int:
    return sum(sprite.getchannel("A").point(lambda value: 255 if value > threshold else 0).histogram()[255:])


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
                for neighbor in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    nx, ny = neighbor
                    if (
                        0 <= nx < alpha.width
                        and 0 <= ny < alpha.height
                        and pixels[nx, ny] > 8
                        and neighbor not in visited
                    ):
                        visited.add(neighbor)
                        queue.append(neighbor)
            xs, ys = zip(*points)
            components.append((len(points), (min(xs), min(ys), max(xs), max(ys))))
    return sorted(components, reverse=True)


def alpha_iou(first: Image.Image, second: Image.Image, crop: tuple[int, int, int, int] | None = None) -> float:
    if crop:
        first, second = first.crop(crop), second.crop(crop)
    first_mask = first.getchannel("A").point(lambda value: 255 if value > 32 else 0)
    second_mask = second.getchannel("A").point(lambda value: 255 if value > 32 else 0)
    intersection = ImageChops.darker(first_mask, second_mask).histogram()[255]
    union = ImageChops.lighter(first_mask, second_mask).histogram()[255]
    return intersection / union if union else 1.0


def alpha_centroid(sprite: Image.Image, crop: tuple[int, int, int, int]) -> tuple[float, float]:
    alpha = sprite.getchannel("A")
    x0, y0, x1, y1 = crop
    points = [
        (x, y)
        for y in range(y0, y1)
        for x in range(x0, x1)
        if alpha.getpixel((x, y)) > 32
    ]
    if not points:
        raise ValueError("alpha centroid crop is empty")
    return (
        sum(x for x, _ in points) / len(points),
        sum(y for _, y in points) / len(points),
    )


def warm_leg_points(sprite: Image.Image, y_min: int = 164) -> tuple[list[tuple[int, int]], int]:
    warm: list[tuple[int, int]] = []
    cold = 0
    for y in range(y_min, CELL_HEIGHT):
        for x in range(70, 151):
            red, green, blue, alpha = sprite.getpixel((x, y))
            if alpha <= 64:
                continue
            if red > 165 and green > 100 and blue > 75 and red - green > 7 and green - blue > 3:
                warm.append((x, y))
            if y >= 168 and red > 55 and blue > red + 8 and blue > green + 4:
                cold += 1
    return warm, cold


def changed_points(first: Image.Image, second: Image.Image, threshold: int = 8) -> list[tuple[int, int]]:
    difference = ImageChops.difference(first, second)
    return [
        (x, y)
        for y in range(CELL_HEIGHT)
        for x in range(CELL_WIDTH)
        if max(difference.getpixel((x, y))) > threshold
    ]


def validate_frame_structure(sprite: Image.Image, row: int, column: int) -> tuple[int, list[str]]:
    errors: list[str] = []
    area = alpha_pixels(sprite)
    if area < MIN_CHARACTER_PIXELS:
        errors.append(f"row {row} column {column}: character area too small ({area})")
    components = connected_components(sprite.getchannel("A"))
    if not components:
        errors.append(f"row {row} column {column}: no connected character component")
    for size, bbox in components[1:]:
        if size > MAX_SECONDARY_COMPONENT_PIXELS:
            errors.append(f"row {row} column {column}: detached component size={size} bbox={bbox}")
    return area, errors


def validate_row_structure(atlas: Image.Image, row: int, used_count: int) -> list[str]:
    errors: list[str] = []
    areas: list[int] = []
    for column in range(COLUMNS):
        sprite = cell(atlas, row, column)
        if column >= used_count:
            area = alpha_pixels(sprite)
            if area:
                errors.append(f"row {row} column {column}: unused cell has {area} alpha pixels")
            continue
        area, frame_errors = validate_frame_structure(sprite, row, column)
        areas.append(area)
        errors.extend(frame_errors)
    if areas and max(areas) / min(areas) > 1.7:
        errors.append(f"row {row}: frame area ratio too large ({max(areas) / min(areas):.2f})")
    return errors


def validate_structure(atlas: Image.Image) -> list[str]:
    errors: list[str] = []
    pixels = atlas.get_flattened_data() if hasattr(atlas, "get_flattened_data") else atlas.getdata()
    residue = sum(
        1
        for red, green, blue, alpha in pixels
        if alpha == 0 and (red or green or blue)
    )
    if residue:
        errors.append(f"transparent RGB residue pixels={residue}")
    for row, used_count in enumerate(USED_FRAMES):
        errors.extend(validate_row_structure(atlas, row, used_count))
    return errors


def eye_center(sprite: Image.Image) -> tuple[float, float]:
    """Locate the coral eyes without confusing them with the red necktie."""

    mask = Image.new("L", (CELL_WIDTH, CELL_HEIGHT), 0)
    pixels = mask.load()
    for y in range(31, 80):
        for x in range(71, 135):
            red, green, blue, alpha = sprite.getpixel((x, y))
            if alpha > 100 and red > 80 and red > green + 25 and blue > green + 3 and green < 145:
                pixels[x, y] = 255
    # The side-facing run model has one small visible eye after resampling into
    # a 192 px cell. The face-only crop keeps the red necktie out of this mask.
    components = [item for item in connected_components(mask) if item[0] >= 3]
    if not components:
        raise ValueError("no coral eye component")
    total = sum(size for size, _ in components)
    return (
        sum(size * (bbox[0] + bbox[2]) / 2 for size, bbox in components) / total,
        sum(size * (bbox[1] + bbox[3]) / 2 for size, bbox in components) / total,
    )


def eye_line(sprite: Image.Image) -> float:
    return eye_center(sprite)[1]


def validate_model_proportions(atlas: Image.Image) -> list[str]:
    """Keep every neutral action on one canonical chibi model scale."""

    rows = (0, 1, 3, 5, 6, 7, 8)
    depths: list[float] = []
    errors: list[str] = []
    for row in rows:
        sprite = cell(atlas, row, 0)
        bbox = sprite.getchannel("A").getbbox()
        try:
            depths.append(eye_line(sprite) - bbox[1])
        except (TypeError, ValueError):
            errors.append(f"row {row}: cannot locate eye line for model-scale check")
    if depths and max(depths) - min(depths) > 12:
        errors.append(f"cross-action head/body proportion drift: eye-depths={[round(value, 2) for value in depths]}")
    run_depths = []
    for column in range(8):
        sprite = cell(atlas, 1, column)
        bbox = sprite.getchannel("A").getbbox()
        try:
            run_depths.append(eye_line(sprite) - bbox[1])
        except (TypeError, ValueError):
            errors.append(f"running-right frame {column}: cannot locate eye line for model-scale check")
    if run_depths and max(run_depths) - min(run_depths) > 3:
        errors.append(f"running head/body proportion flickers: eye-depths={[round(value, 2) for value in run_depths]}")
    idle_height = cell(atlas, 0, 0).getchannel("A").getbbox()[3] - cell(atlas, 0, 0).getchannel("A").getbbox()[1]
    run_height = cell(atlas, 1, 0).getchannel("A").getbbox()[3] - cell(atlas, 1, 0).getchannel("A").getbbox()[1]
    if abs(idle_height - run_height) > 8:
        errors.append(f"running model height {run_height}px does not match idle {idle_height}px")
    return errors


def palette_artifact_mask(sprite: Image.Image) -> Image.Image:
    pixels = sprite.get_flattened_data() if hasattr(sprite, "get_flattened_data") else sprite.getdata()
    mask = Image.new("L", sprite.size)
    mask.putdata(
        [
            255
            if (
                (alpha > 8 and red > 220 and blue > 180 and green < 80 and abs(red - blue) < 100)
                or (alpha > 8 and blue > red + 8 and red > 95 and green < 125 and blue > 110)
            )
            else 0
            for red, green, blue, alpha in pixels
        ]
    )
    return mask


def validate_palette(atlas: Image.Image) -> list[str]:
    """Reject chroma-key pockets and sizeable purple hair-like regions."""

    errors: list[str] = []
    for row, used_count in enumerate(USED_FRAMES):
        for column in range(used_count):
            components = connected_components(palette_artifact_mask(cell(atlas, row, column)))
            if components and components[0][0] > 20:
                errors.append(
                    f"row {row} column {column}: purple/chroma artifact size={components[0][0]} bbox={components[0][1]}"
                )
    return errors


def validate_run_frame(index: int, right: Image.Image, left: Image.Image) -> list[str]:
    errors: list[str] = []
    if ImageChops.difference(left, ImageOps.mirror(right)).getbbox():
        errors.append(f"running-left frame {index}: not an exact whole-frame mirror")
    bbox = right.getchannel("A").getbbox()
    if bbox and min(bbox[0], CELL_WIDTH - bbox[2]) < 4:
        errors.append(f"running-right frame {index}: unsafe horizontal margin bbox={bbox}")
    if bbox and min(bbox[1], CELL_HEIGHT - bbox[3]) < 3:
        errors.append(f"running-right frame {index}: unsafe vertical margin bbox={bbox}")
    warm, cold = warm_leg_points(right)
    if len(warm) < 350:
        errors.append(f"running-right frame {index}: too little healthy warm leg skin ({len(warm)} px)")
    if cold:
        errors.append(f"running-right frame {index}: cool purple/blue leg pixels={cold}")
    if warm and max(x for x, _ in warm) - min(x for x, _ in warm) > 58:
        errors.append(f"running-right frame {index}: stride exceeds cute chibi limit")
    return errors


def component_centroid(mask: Image.Image, component: tuple[int, tuple[int, int, int, int]]) -> tuple[float, float]:
    _, (x0, y0, x1, y1) = component
    points = [
        (x, y)
        for y in range(y0, y1 + 1)
        for x in range(x0, x1 + 1)
        if mask.getpixel((x, y)) > 8
    ]
    return (
        sum(x for x, _ in points) / len(points),
        sum(y for _, y in points) / len(points),
    )


def run_cuff_centers(sprite: Image.Image) -> tuple[tuple[float, float], tuple[float, float]]:
    """Track the two teal cuffs, which remain visible at native pet size."""

    centers = []
    # One cuff stays on each side of the torso. Separate ROIs prevent the teal
    # sailor collar from being mistaken for an arm component.
    for x0, x1 in ((68, 113), (122, 151)):
        mask = Image.new("L", (CELL_WIDTH, CELL_HEIGHT), 0)
        pixels = mask.load()
        for y in range(75, 150):
            for x in range(x0, x1):
                red, green, blue, alpha = sprite.getpixel((x, y))
                if (
                    alpha > 40
                    and red < 185
                    and green > 55
                    and blue > 65
                    and green - red > 10
                    and blue - red > 14
                ):
                    pixels[x, y] = 255
        components = [item for item in connected_components(mask) if item[0] >= 20]
        if not components:
            raise ValueError("missing teal cuff component")
        centers.append(component_centroid(mask, components[0]))
    return centers[0], centers[1]


def displayed_distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    """Distance after a 192x208 source cell is rendered at 112x121 px."""

    return math.hypot(
        (second[0] - first[0]) * 112 / CELL_WIDTH,
        (second[1] - first[1]) * 121 / CELL_HEIGHT,
    )


def validate_cuff_track(label: str, track: list[tuple[float, float]]) -> list[str]:
    errors: list[str] = []
    full_range = max(math.dist(first, second) for first in track for second in track)
    opposite = math.dist(track[0], track[4])
    transitions = [displayed_distance(track[index], track[(index + 1) % 8]) for index in range(8)]
    if full_range < 10:
        errors.append(f"running-right: {label} arm is visually frozen (cuff range={full_range:.2f}px source)")
    if opposite < 10:
        errors.append(f"running-right: {label} arm does not reach an opposite half-cycle pose ({opposite:.2f}px source)")
    if max(transitions) > 6:
        errors.append(f"running-right: {label} arm jumps {max(transitions):.2f}px at native display size")
    if min(transitions) < 1:
        errors.append(f"running-right: {label} arm stalls between adjacent frames ({min(transitions):.2f}px native)")
    return errors


def validate_run_arms(right: list[Image.Image]) -> list[str]:
    try:
        pairs = [run_cuff_centers(sprite) for sprite in right]
    except ValueError as error:
        return [f"running-right: {error}"]
    tracks = [[pair[index] for pair in pairs] for index in range(2)]
    labels = ("rear", "front")
    errors = [error for label, track in zip(labels, tracks) for error in validate_cuff_track(label, track)]

    rear_vector = (tracks[0][4][0] - tracks[0][0][0], tracks[0][4][1] - tracks[0][0][1])
    front_vector = (tracks[1][4][0] - tracks[1][0][0], tracks[1][4][1] - tracks[1][0][1])
    denominator = math.hypot(*rear_vector) * math.hypot(*front_vector)
    alignment = sum(first * second for first, second in zip(rear_vector, front_vector)) / denominator if denominator else 1.0
    if alignment > 0.5:
        errors.append(f"running-right: arms move together instead of contralaterally (cosine={alignment:.2f})")
    return errors


def validate_run_loop(right: list[Image.Image]) -> list[str]:
    errors: list[str] = []
    try:
        anchors = [eye_center(sprite) for sprite in right]
    except ValueError as error:
        return [f"running-right: {error}"]
    xs, ys = [value[0] for value in anchors], [value[1] for value in anchors]
    x_range, y_range = max(xs) - min(xs), max(ys) - min(ys)
    if x_range > 3.5 or y_range > 4.0:
        errors.append(f"running-right: head/body anchor drifts x={x_range:.2f}px y={y_range:.2f}px")
    if y_range < 1.0:
        errors.append(f"running-right: upper body is visually frozen (eye y range={y_range:.2f}px)")
    return errors


def validate_run_phases(right: list[Image.Image]) -> list[str]:
    errors: list[str] = []
    for first, second in zip(range(4), range(4, 8)):
        lower_box = (70, 160, 150, CELL_HEIGHT)
        first_lower = right[first].crop(lower_box).getchannel("A")
        second_lower = right[second].crop(lower_box).getchannel("A")
        if ImageChops.difference(first_lower, second_lower).getbbox():
            errors.append(f"running-right phases {first}/{second}: opposite-step leg geometry mismatch")
        changes = changed_points(right[first], right[second])
        leg_changes = [(x, y) for x, y in changes if 70 <= x < 150 and y >= 160]
        if len(leg_changes) < 500:
            errors.append(f"running-right phases {first}/{second}: leg depth did not swap ({len(leg_changes)} px)")
    return errors


def validate_run(atlas: Image.Image) -> list[str]:
    right = [cell(atlas, 1, column) for column in range(8)]
    left = [cell(atlas, 2, column) for column in range(8)]
    errors = [error for index, frames in enumerate(zip(right, left)) for error in validate_run_frame(index, *frames)]
    return errors + validate_run_loop(right) + validate_run_arms(right) + validate_run_phases(right)


def validate_jump_arc(bottoms: list[int]) -> list[str]:
    crouch, launch, apex, descent, settle = bottoms
    checks = (
        crouch >= 202,
        190 <= launch <= 198,
        apex <= 165,
        launch - apex >= 28,
        194 <= descent <= 201,
        descent - apex >= 30,
        settle >= 202,
    )
    return [] if all(checks) else [f"jump arc is not crouch/launch/apex/descent/settle: bottoms={bottoms}"]


def validate_jump_apex(apex: Image.Image) -> list[str]:
    errors: list[str] = []
    apex_skin, apex_cold = warm_leg_points(apex, y_min=130)
    apex_skin = [(x, y) for x, y in apex_skin if x <= 125]
    if len(apex_skin) < 150:
        errors.append(f"jump apex: legs are missing/occluded ({len(apex_skin)} warm pixels)")
    if apex_skin:
        xs = [x for x, _ in apex_skin]
        if abs(sum(xs) / len(xs) - 96) > 18 or max(xs) - min(xs) > 55:
            errors.append("jump apex: tucked legs leave the pelvis envelope like a forward kick")
    if apex_cold:
        errors.append(f"jump apex: cool purple/blue leg pixels={apex_cold}")
    return errors


def validate_jump(atlas: Image.Image) -> list[str]:
    frames = [cell(atlas, 4, column) for column in range(5)]
    boxes = [sprite.getchannel("A").getbbox() for sprite in frames]
    if any(bbox is None for bbox in boxes):
        return ["jump: empty frame"]
    bottoms = [bbox[3] for bbox in boxes if bbox]
    errors = validate_jump_arc(bottoms) + validate_jump_apex(frames[2])
    if alpha_iou(frames[0], frames[4]) < 0.90:
        errors.append("jump landing does not return to the crouch footprint")
    return errors


def validate_state_continuity(atlas: Image.Image) -> list[str]:
    errors: list[str] = []
    thresholds = {0: 0.94, 3: 0.94, 5: 0.74, 6: 0.895, 7: 0.93, 8: 0.925}
    for row, minimum_iou in thresholds.items():
        count = USED_FRAMES[row]
        frames = [cell(atlas, row, column) for column in range(count)]
        bottoms = [sprite.getchannel("A").getbbox()[3] for sprite in frames]
        if len(set(bottoms)) != 1 or bottoms[0] != 204:
            errors.append(f"row {row}: planted baseline drifts {bottoms}")
        for index in range(count):
            overlap = alpha_iou(frames[index], frames[(index + 1) % count])
            if overlap < minimum_iou:
                errors.append(f"row {row} {index}->{(index + 1) % count}: alpha IoU {overlap:.3f} < {minimum_iou:.2f}")
    neutral_heights = [cell(atlas, row, 0).getchannel("A").getbbox()[3] - cell(atlas, row, 0).getchannel("A").getbbox()[1] for row in (0, 3, 5, 6, 7, 8)]
    if max(neutral_heights) - min(neutral_heights) > 4:
        errors.append(f"front-facing state scale drift: heights={neutral_heights}")
    return errors


def validate_look(atlas: Image.Image) -> list[str]:
    errors: list[str] = []
    for left_column, right_column in enumerate(range(7, 0, -1), start=1):
        left = cell(atlas, 10, left_column)
        mirrored = ImageOps.mirror(cell(atlas, 9, right_column))
        if ImageChops.difference(left, mirrored).getbbox():
            errors.append(f"look mirror mismatch: row10 column {left_column} vs row9 column {right_column}")
    ordered = [cell(atlas, 9, column) for column in range(8)] + [cell(atlas, 10, column) for column in range(8)]
    for index, (first, second) in enumerate(zip(ordered, ordered[1:] + ordered[:1])):
        first_box, second_box = first.getchannel("A").getbbox(), second.getchannel("A").getbbox()
        if first_box[3] != 204 or second_box[3] != 204:
            errors.append(f"look {index}->{(index + 1) % 16}: baseline drift")
        full_overlap = alpha_iou(first, second)
        lower_overlap = alpha_iou(first, second, (0, 120, CELL_WIDTH, CELL_HEIGHT))
        if full_overlap < 0.84 or lower_overlap < 0.82:
            errors.append(
                f"look {index}->{(index + 1) % 16}: discontinuity full={full_overlap:.3f} lower={lower_overlap:.3f}"
            )
        areas = alpha_pixels(first), alpha_pixels(second)
        if max(areas) / min(areas) > 1.11:
            errors.append(f"look {index}->{(index + 1) % 16}: scale jump areas={areas}")
        centers = alpha_centroid(first, (20, 0, 175, 208)), alpha_centroid(second, (20, 0, 175, 208))
        if abs(centers[0][0] - centers[1][0]) > 4 or abs(centers[0][1] - centers[1][1]) > 4:
            errors.append(f"look {index}->{(index + 1) % 16}: center jump {centers}")
    down_center = alpha_centroid(ordered[8], (20, 0, 175, 208))[0]
    if abs(down_center - CELL_WIDTH / 2) > 4:
        errors.append(f"look 180: straight-down frame is off-center ({down_center:.2f})")
    return errors


def validate_review_binding(atlas_path: Path) -> list[str]:
    if atlas_path.resolve() != DEFAULT_ATLAS.resolve():
        return []
    if not REVIEW_MANIFEST.exists():
        return [f"missing manual review manifest: {REVIEW_MANIFEST}"]
    review = json.loads(REVIEW_MANIFEST.read_text())
    digest = hashlib.sha256(atlas_path.read_bytes()).hexdigest()
    errors = [] if review.get("atlasSha256") == digest else ["manual review manifest SHA does not match atlas"]
    required = {"idle", "run-right", "run-left", "wave", "jump", "failed", "waiting", "task", "review", "look-16"}
    reviewed = set(review.get("reviewedActions", []))
    if not required <= reviewed:
        errors.append(f"manual review manifest misses actions={sorted(required - reviewed)}")
    return errors


def main() -> int:
    atlas_path = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ATLAS)
    atlas = Image.open(atlas_path).convert("RGBA")
    if atlas.size != ATLAS_SIZE:
        print(f"atlas size {atlas.size} != {ATLAS_SIZE}", file=sys.stderr)
        return 1
    errors = []
    for validator in (
        validate_structure,
        validate_palette,
        validate_model_proportions,
        validate_run,
        validate_jump,
        validate_state_continuity,
        validate_look,
    ):
        errors.extend(validator(atlas))
    errors.extend(validate_review_binding(atlas_path))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("PASS ATRI atlas: unified proportions/palette, visible contralateral arm swing, compact alternating gait, intact anatomy, physical jump, exact mirrors, and continuous 16-way look")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
