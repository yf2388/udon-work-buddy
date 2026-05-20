from __future__ import annotations

import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PET_DIR = ROOT / "codex-pets" / "udon"
SOURCE = PET_DIR / "udon-source.png"
POSE_SHEET = PET_DIR / "udon-pose-sheet.png"
ACTION_STRIPS = {
    3: PET_DIR / "udon-waving-strip.png",
    4: PET_DIR / "udon-jumping-strip.png",
    8: PET_DIR / "udon-review-strip.png",
}

CELL_W = 192
CELL_H = 208
COLS = 8
ROWS = 9
ROW_NAMES = [
    "idle",
    "running-right",
    "running-left",
    "waving",
    "jumping",
    "failed",
    "waiting",
    "running",
    "review",
]
USED_FRAMES_BY_ROW = {
    0: 6,
    1: 8,
    2: 8,
    3: 4,
    4: 5,
    5: 8,
    6: 6,
    7: 6,
    8: 6,
}
ROW_DURATIONS = {
    "idle": [280, 110, 110, 140, 140, 320],
    "running-right": [120, 120, 120, 120, 120, 120, 120, 220],
    "running-left": [120, 120, 120, 120, 120, 120, 120, 220],
    "waving": [140, 140, 140, 280],
    "jumping": [140, 140, 140, 140, 280],
    "failed": [140, 140, 140, 140, 140, 140, 140, 240],
    "waiting": [150, 150, 150, 150, 150, 260],
    "running": [120, 120, 120, 120, 120, 220],
    "review": [150, 150, 150, 150, 150, 280],
}


def remove_light_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # Generated source uses an almost-white studio background. Keep the
            # dog and antialiased outline, fade only the outer field.
            whiteness = min(r, g, b)
            if whiteness > 246 and abs(r - g) < 8 and abs(g - b) < 8:
                pixels[x, y] = (r, g, b, 0)
            elif whiteness > 232 and abs(r - g) < 14 and abs(g - b) < 14:
                alpha = int(max(0, min(255, (246 - whiteness) * 18)))
                pixels[x, y] = (r, g, b, min(a, alpha))
    return rgba


def crop_subject(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value > 10 else 0).getbbox()
    if bbox is None:
        return image
    left, top, right, bottom = bbox
    pad = 18
    return image.crop(
        (
            max(0, left - pad),
            max(0, top - pad),
            min(image.width, right + pad),
            min(image.height, bottom + pad),
        )
    )


def isolate_primary_component(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    width, height = rgba.size
    data = alpha.tobytes()
    visited = bytearray(width * height)
    largest: list[int] = []

    for start, alpha_value in enumerate(data):
        if alpha_value <= 16 or visited[start]:
            continue
        stack = [start]
        visited[start] = 1
        component: list[int] = []
        while stack:
            current = stack.pop()
            component.append(current)
            x = current % width
            y = current // width
            for neighbor in (current - 1, current + 1, current - width, current + width):
                if neighbor < 0 or neighbor >= width * height or visited[neighbor] or data[neighbor] <= 16:
                    continue
                nx = neighbor % width
                ny = neighbor // width
                if abs(nx - x) + abs(ny - y) != 1:
                    continue
                visited[neighbor] = 1
                stack.append(neighbor)
        if len(component) > len(largest):
            largest = component

    if not largest:
        return rgba

    output = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    src = rgba.load()
    dst = output.load()
    for index in largest:
        x = index % width
        y = index // width
        dst[x, y] = src[x, y]
    return output


def pixel_sprite(subject: Image.Image, max_width: int = 178, max_height: int = 184) -> Image.Image:
    scale = min(max_width / subject.width, max_height / subject.height)
    size = (max(1, int(subject.width * scale)), max(1, int(subject.height * scale)))
    small = subject.resize(size, Image.Resampling.LANCZOS)
    # Quantize a little so it reads as the same mosaic/pixel style as Codex pets.
    indexed = small.convert("RGBA").quantize(colors=56, method=Image.Quantize.FASTOCTREE)
    return indexed.convert("RGBA")


def pose_cell(sheet: Image.Image, index: int) -> Image.Image:
    col = index % 3
    row = index // 3
    cell_w = sheet.width / 3
    cell_h = sheet.height / 3
    left = round(col * cell_w)
    top = round(row * cell_h)
    right = round((col + 1) * cell_w)
    bottom = round((row + 1) * cell_h)
    return sheet.crop((left, top, right, bottom))


def strip_slot(strip: Image.Image, index: int, count: int) -> Image.Image:
    slot_w = strip.width / count
    left = round(index * slot_w)
    right = round((index + 1) * slot_w)
    return strip.crop((left, 0, right, strip.height))


def load_action_overrides() -> dict[int, list[Image.Image]]:
    overrides: dict[int, list[Image.Image]] = {}
    for row, path in ACTION_STRIPS.items():
        if not path.is_file():
            continue
        strip = Image.open(path)
        count = USED_FRAMES_BY_ROW[row]
        overrides[row] = [
            pixel_sprite(
                crop_subject(
                    isolate_primary_component(
                        remove_light_background(strip_slot(strip, index, count))
                    )
                )
            )
            for index in range(count)
        ]
    return overrides


def load_pose_sprites() -> list[Image.Image]:
    if POSE_SHEET.is_file():
        sheet = Image.open(POSE_SHEET)
        cells = [
            pixel_sprite(
                crop_subject(
                    isolate_primary_component(
                        remove_light_background(pose_cell(sheet, index))
                    )
                )
            )
            for index in range(9)
        ]
        # The generated reference sheet is pose-oriented, not row-name bound.
        # Map it onto the Codex row contract, using mirrors where that preserves
        # stronger dog locomotion than a weak generated counterpart.
        return [
            cells[0],  # idle
            cells[1].transpose(Image.Transpose.FLIP_LEFT_RIGHT),  # running-right
            cells[1],  # running-left
            cells[3],  # waving
            cells[4],  # jumping
            cells[5],  # failed
            cells[6],  # waiting
            cells[7],  # running / active work
            cells[8],  # review
        ]

    source = Image.open(SOURCE)
    fallback = pixel_sprite(crop_subject(remove_light_background(source)))
    return [fallback for _ in range(ROWS)]


def paste_center(canvas: Image.Image, sprite: Image.Image, dx: int = 0, dy: int = 0) -> None:
    max_width = max(1, CELL_W - abs(dx) * 2 - 10)
    max_height = CELL_H - 10
    if sprite.width > max_width or sprite.height > max_height:
        scale = min(max_width / sprite.width, max_height / sprite.height)
        sprite = sprite.resize(
            (max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale))),
            Image.Resampling.NEAREST,
        )
    x = (CELL_W - sprite.width) // 2 + dx
    y = CELL_H - sprite.height - 12 + dy
    canvas.alpha_composite(sprite, (x, y))


def transform(sprite: Image.Image, *, sx: float = 1.0, sy: float = 1.0, angle: float = 0.0, mirror: bool = False) -> Image.Image:
    out = sprite
    if mirror:
        out = out.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if sx != 1.0 or sy != 1.0:
        out = out.resize((max(1, int(out.width * sx)), max(1, int(out.height * sy))), Image.Resampling.NEAREST)
    if angle:
        out = out.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    return out


def draw_pixel_ellipse(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: tuple[int, int, int, int]) -> None:
    draw.ellipse(xy, fill=fill)


def add_blink(canvas: Image.Image, frame: int, y: int = 72) -> None:
    if frame not in {3, 4}:
        return
    draw = ImageDraw.Draw(canvas)
    for x0 in (70, 116):
        draw.rounded_rectangle((x0, y, x0 + 14, y + 6), radius=2, fill=(20, 20, 20, 245))
        draw.line((x0 + 2, y + 6, x0 + 12, y + 6), fill=(238, 232, 215, 230), width=1)


def add_tongue(canvas: Image.Image, frame: int) -> None:
    if frame not in {2, 3, 4}:
        return
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((92, 115, 101, 126), radius=4, fill=(226, 104, 124, 235))
    draw.line((96, 116, 96, 123), fill=(170, 62, 82, 210), width=1)


def add_spark(canvas: Image.Image, frame: int) -> None:
    if frame not in {1, 5}:
        return
    draw = ImageDraw.Draw(canvas)
    cx = 132 if frame == 1 else 59
    cy = 68
    draw.line((cx, cy - 4, cx, cy + 4), fill=(255, 244, 143, 230), width=2)
    draw.line((cx - 4, cy, cx + 4, cy), fill=(255, 244, 143, 230), width=2)


def add_focus_dots(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    active = frame % 3
    for i in range(3):
        alpha = 225 if i == active else 95
        x = 126 + i * 8
        y = 124 - (2 if i == active else 0)
        draw.rounded_rectangle((x, y, x + 4, y + 4), radius=1, fill=(156, 199, 150, alpha))


def add_flower_wiggle(canvas: Image.Image, frame: int) -> None:
    if frame not in {1, 2, 4, 5}:
        return
    draw = ImageDraw.Draw(canvas)
    dx = -2 if frame in {1, 5} else 2
    draw.line((97, 51, 97 + dx, 45), fill=(94, 164, 61, 170), width=2)


def add_motion_lines(canvas: Image.Image, direction: int, frame: int) -> None:
    if frame % 2 == 0:
        return
    draw = ImageDraw.Draw(canvas)
    x = 32 if direction > 0 else 150
    for i, length in enumerate((16, 10)):
        y = 130 + i * 14
        draw.line((x, y, x - direction * length, y), fill=(91, 104, 98, 95), width=3)


def add_hop_shadow(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    widths = [78, 66, 44, 34, 58]
    alpha = [85, 60, 35, 25, 55][frame]
    width = widths[frame]
    draw.ellipse(
        ((CELL_W - width) // 2, 188, (CELL_W + width) // 2, 198),
        fill=(22, 27, 25, alpha),
    )


def add_wave_paw(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    lift = [0, -8, -15, -20, -15, -8, 0, -4][frame]
    # Left-side raised paw, in the same dark-fur/white-paw language as the sprite.
    arm = [(57, 135 + lift), (48, 121 + lift), (38, 112 + lift), (33, 119 + lift), (42, 137 + lift), (53, 146 + lift)]
    draw.polygon(arm, fill=(32, 33, 34, 245))
    draw.line(arm + [arm[0]], fill=(8, 9, 10, 255), width=3)
    draw_pixel_ellipse(draw, (29, 106 + lift, 43, 121 + lift), (247, 242, 227, 248))
    draw.arc((28, 105 + lift, 44, 122 + lift), 190, 520, fill=(9, 10, 11, 255), width=2)


def add_failed_blush(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((57, 143, 70, 149), radius=3, fill=(241, 121, 132, 120))
    draw.rounded_rectangle((121, 143, 134, 149), radius=3, fill=(241, 121, 132, 120))


def add_question_marks(canvas: Image.Image, frame: int) -> None:
    if frame not in {1, 4}:
        return
    draw = ImageDraw.Draw(canvas)
    x = 136 if frame == 1 else 49
    y = 75
    draw.arc((x, y, x + 12, y + 14), 210, 40, fill=(160, 198, 151, 220), width=2)
    draw.line((x + 6, y + 13, x + 6, y + 16), fill=(160, 198, 151, 220), width=2)
    draw.point((x + 6, y + 20), fill=(160, 198, 151, 220))


def add_tail_wag(canvas: Image.Image, frame: int) -> None:
    if frame not in {1, 2, 4, 5}:
        return
    draw = ImageDraw.Draw(canvas)
    x = 144
    y = 137
    offset = [-7, 7, -7, 7][[1, 2, 4, 5].index(frame)]
    draw.arc((x - 10, y - 28 + offset, x + 22, y + 12 + offset), 250, 40, fill=(26, 27, 28, 230), width=5)


def add_waiting_tail_swish(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    # Draw this before the body so the tail reads as attached behind Udon.
    tail_boxes = [
        (132, 121, 176, 165, 210, 310),
        (138, 112, 181, 155, 225, 330),
        (134, 117, 178, 161, 215, 320),
        (119, 112, 164, 157, 205, 305),
        (112, 121, 157, 166, 195, 295),
        (124, 118, 168, 162, 205, 310),
    ]
    x0, y0, x1, y1, start, end = tail_boxes[frame]
    draw.arc((x0, y0, x1, y1), start, end, fill=(8, 9, 10, 245), width=11)
    draw.arc((x0 + 2, y0 + 2, x1 - 3, y1 - 3), start, end, fill=(42, 42, 43, 245), width=7)
    draw.arc((x0 + 6, y0 + 7, x1 - 8, y1 - 8), start + 4, end - 3, fill=(185, 181, 170, 155), width=2)


def add_waiting_paw_tap(canvas: Image.Image, frame: int) -> None:
    if frame not in {1, 2, 4, 5}:
        return
    draw = ImageDraw.Draw(canvas)
    x = 63 if frame in {1, 2} else 118
    lift = -5 if frame in {2, 5} else -2
    draw_pixel_ellipse(draw, (x, 163 + lift, x + 24, 181 + lift), (246, 240, 224, 242))
    draw.arc((x - 1, 162 + lift, x + 25, 182 + lift), 180, 360, fill=(8, 9, 10, 235), width=2)


def add_front_run_shadow(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    widths = [92, 80, 68, 82, 94, 76]
    width = widths[frame]
    draw.ellipse(
        ((CELL_W - width) // 2, 188, (CELL_W + width) // 2, 199),
        fill=(18, 22, 20, 58),
    )


def add_front_run_tail(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    boxes = [
        (132, 118, 176, 162, 220, 335),
        (119, 110, 160, 151, 190, 305),
        (128, 113, 171, 156, 210, 325),
        (139, 112, 181, 154, 230, 345),
        (127, 119, 170, 162, 210, 325),
        (116, 116, 158, 159, 195, 310),
    ]
    x0, y0, x1, y1, start, end = boxes[frame]
    draw.arc((x0, y0, x1, y1), start, end, fill=(8, 9, 10, 235), width=9)
    draw.arc((x0 + 2, y0 + 2, x1 - 2, y1 - 2), start, end, fill=(44, 44, 45, 235), width=6)


def add_front_run_paws(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    # Alternating four-beat gait: front paws reach forward while rear paws tuck in.
    paw_sets = [
        [(55, 165, 22, 15), (118, 173, 24, 14), (72, 184, 20, 12), (105, 184, 20, 12)],
        [(48, 173, 23, 14), (124, 164, 23, 15), (69, 181, 20, 12), (108, 187, 20, 12)],
        [(59, 181, 22, 13), (113, 176, 22, 13), (65, 166, 20, 13), (114, 184, 20, 12)],
        [(70, 174, 22, 14), (102, 165, 24, 15), (58, 184, 20, 12), (119, 181, 20, 12)],
        [(55, 163, 23, 15), (119, 174, 23, 14), (73, 186, 20, 12), (104, 183, 20, 12)],
        [(47, 171, 22, 14), (126, 166, 23, 15), (68, 184, 20, 12), (110, 186, 20, 12)],
    ]
    for index, (x, y, w, h) in enumerate(paw_sets[frame]):
        fill = (248, 242, 226, 250) if index < 2 else (34, 34, 35, 235)
        draw_pixel_ellipse(draw, (x, y, x + w, y + h), fill)
        draw.arc((x - 1, y - 1, x + w + 1, y + h + 1), 180, 360, fill=(7, 8, 9, 235), width=2)
    for x, y in [(38, 176), (147, 176)]:
        if frame in {1, 3, 5}:
            draw.line((x, y, x - 10 if x < 96 else x + 10, y + 2), fill=(91, 104, 98, 75), width=2)


def add_side_run_shadow(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    widths = [92, 76, 86, 108, 88, 78]
    width = widths[frame]
    draw.ellipse(
        (44, 187, 44 + width, 199),
        fill=(18, 22, 20, 60),
    )


def add_side_run_paws(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    # Explicit gallop cycle. The generated dog body carries the face/harness;
    # these paws make the running beat readable even at pet-overlay size.
    paw_sets = [
        [(58, 171, 26, 13), (119, 168, 25, 13), (79, 185, 22, 11), (105, 186, 22, 11)],
        [(49, 181, 24, 12), (130, 177, 25, 12), (78, 166, 21, 12), (111, 166, 21, 12)],
        [(63, 187, 24, 11), (111, 187, 24, 11), (69, 171, 22, 12), (125, 169, 22, 12)],
        [(43, 169, 29, 13), (136, 170, 30, 13), (75, 184, 23, 11), (105, 184, 23, 11)],
        [(61, 174, 25, 13), (121, 181, 24, 12), (76, 166, 22, 12), (113, 188, 22, 10)],
        [(50, 183, 24, 12), (131, 176, 26, 12), (82, 170, 21, 12), (108, 168, 21, 12)],
    ]
    for index, (x, y, w, h) in enumerate(paw_sets[frame]):
        fill = (247, 241, 225, 250) if index in {0, 1} else (28, 28, 29, 235)
        draw_pixel_ellipse(draw, (x, y, x + w, y + h), fill)
        draw.arc((x - 1, y - 1, x + w + 1, y + h + 1), 180, 360, fill=(7, 8, 9, 235), width=2)


def add_side_run_tail(canvas: Image.Image, frame: int) -> None:
    draw = ImageDraw.Draw(canvas)
    boxes = [
        (123, 100, 171, 142, 210, 340),
        (124, 88, 176, 130, 215, 345),
        (122, 94, 173, 136, 210, 338),
        (127, 104, 176, 147, 218, 350),
        (123, 98, 172, 140, 212, 340),
        (126, 90, 176, 132, 218, 346),
    ]
    x0, y0, x1, y1, start, end = boxes[frame]
    draw.arc((x0, y0, x1, y1), start, end, fill=(8, 9, 10, 235), width=10)
    draw.arc((x0 + 2, y0 + 2, x1 - 2, y1 - 2), start, end, fill=(47, 47, 48, 235), width=6)


def add_speed_lines(canvas: Image.Image, frame: int) -> None:
    if frame in {0, 2, 4}:
        return
    draw = ImageDraw.Draw(canvas)
    for i, length in enumerate((22, 15, 9)):
        y = 119 + i * 18
        draw.line((29, y, 29 - length, y + 1), fill=(91, 104, 98, 95), width=3)


def add_dig_particles(canvas: Image.Image, frame: int) -> None:
    if frame not in {1, 2, 4}:
        return
    draw = ImageDraw.Draw(canvas)
    particles = [(67, 174), (74, 181), (83, 176)] if frame != 4 else [(101, 174), (110, 181), (118, 176)]
    for x, y in particles:
        draw.rectangle((x, y, x + 3, y + 3), fill=(107, 78, 51, 170))


def build_override_frame(row: int, frame: int, sprite: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    if row == 4:
        add_hop_shadow(canvas, min(frame, 4))
    paste_center(canvas, sprite)
    return canvas.resize((CELL_W // 2, CELL_H // 2), Image.Resampling.NEAREST).resize((CELL_W, CELL_H), Image.Resampling.NEAREST)


def build_running_from_jump_frame(frame: int, jump_sprites: list[Image.Image]) -> Image.Image:
    canvas = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    sequence = [0, 1, 2, 1, 4, 2]
    sprite = jump_sprites[sequence[frame]]
    add_side_run_shadow(canvas, frame)
    add_speed_lines(canvas, frame)
    # Reuse the stronger four-legged jumping poses, but pin them close to the
    # ground and stretch forward so they read as a run instead of a hop.
    sprite = transform(
        sprite,
        sx=[1.05, 1.10, 1.14, 1.16, 1.08, 1.12][frame],
        sy=[0.96, 0.93, 0.90, 0.88, 0.94, 0.91][frame],
        angle=[0, -2, -4, -5, 1, -3][frame],
    )
    paste_center(canvas, sprite, dx=[-4, 0, 4, 8, 1, 5][frame], dy=[9, 7, 9, 11, 8, 10][frame])
    add_side_run_paws(canvas, frame)
    add_focus_dots(canvas, frame)
    return canvas.resize((CELL_W // 2, CELL_H // 2), Image.Resampling.NEAREST).resize((CELL_W, CELL_H), Image.Resampling.NEAREST)


def build_frame(row_sprites: list[Image.Image], row: int, frame: int) -> Image.Image:
    canvas = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    phase = math.sin(frame / COLS * math.tau)
    base = row_sprites[row]

    if row == 0:  # idle: soft breathing and blink
        sprite = transform(base, sx=1.0 + 0.01 * phase, sy=1.0 - 0.01 * phase)
        paste_center(canvas, sprite, dy=int(2 * phase))
        add_tail_wag(canvas, frame)
        add_blink(canvas, frame, y=74)
        add_spark(canvas, frame)
    elif row == 1:  # running-right: playful trot
        sprite = transform(base, sx=1.0 + 0.05 * phase, sy=1.0 - 0.03 * phase, angle=-3 + 2 * phase)
        paste_center(canvas, sprite, dx=8 + int(8 * phase), dy=[0, -6, -2, 4, 0, -6, -2, 4][frame])
        add_motion_lines(canvas, direction=1, frame=frame)
    elif row == 2:  # running-left
        sprite = transform(base, sx=1.0 + 0.05 * phase, sy=1.0 - 0.03 * phase, angle=3 - 2 * phase)
        paste_center(canvas, sprite, dx=-8 - int(8 * phase), dy=[0, -6, -2, 4, 0, -6, -2, 4][frame])
        add_motion_lines(canvas, direction=-1, frame=frame)
    elif row == 3:  # waving: hello/attention-seeking
        sprite = transform(base, sx=1.0, sy=1.0, angle=[-3, 2, -2, 1][frame])
        paste_center(canvas, sprite, dx=2, dy=0)
    elif row == 4:  # jumping: compact mischievous hop
        add_hop_shadow(canvas, frame)
        jump = [0, -16, -38, -22, 0][frame]
        squash = 1.10 if frame in {0, 4} else 0.96
        stretch = 0.92 if frame in {0, 4} else 1.07
        sprite = transform(base, sx=squash, sy=stretch)
        paste_center(canvas, sprite, dy=jump)
    elif row == 5:  # failed: small sheepish tumble, still cute
        angle = [-2, -4, -6, -4, -2, 0, 1, 0][frame]
        sprite = transform(base, sx=1.02, sy=0.98, angle=angle)
        paste_center(canvas, sprite, dy=12 + [0, 1, 2, 1, 0, 0, -1, 0][frame])
        add_failed_blush(canvas)
    elif row == 6:  # waiting: curious head tilt and tongue peek
        add_waiting_tail_swish(canvas, frame)
        angle = [-3, -6, -3, 3, 6, 3][frame]
        sprite = transform(base, sx=1.0 + [0.0, -0.01, 0.0, 0.01, 0.0, -0.01][frame], sy=1.0, angle=angle)
        paste_center(canvas, sprite, dx=[0, -2, -1, 1, 2, 1][frame], dy=[1, 0, 1, 0, 1, 1][frame])
        add_waiting_paw_tap(canvas, frame)
        add_question_marks(canvas, frame)
    elif row == 7:  # running: side gallop with readable four-paw motion
        side = row_sprites[1]
        add_side_run_shadow(canvas, frame)
        add_side_run_tail(canvas, frame)
        bob = [4, -6, 0, -9, 4, -3][frame]
        stretch = [1.16, 1.08, 1.12, 1.22, 1.14, 1.09][frame]
        height = [0.86, 0.92, 0.88, 0.84, 0.87, 0.91][frame]
        sprite = transform(side, sx=stretch, sy=height, angle=[-5, -2, -4, -7, -5, -3][frame])
        paste_center(canvas, sprite, dx=[-3, 1, 4, 7, 2, -1][frame], dy=bob + 8)
        add_side_run_paws(canvas, frame)
        add_speed_lines(canvas, frame)
        add_focus_dots(canvas, frame)
    else:  # review: alert, bright-eyed, ready for attention
        sprite = transform(base, sx=1.0 + 0.02 * phase, sy=1.0, angle=[0, -2, -3, -2, 0, 1][frame])
        paste_center(canvas, sprite, dx=[0, -4, -8, -5, 0, 2][frame], dy=int(phase))
        add_spark(canvas, frame)

    # Pixel-lock overlays so the hand-drawn action accents match the atlas style.
    return canvas.resize((CELL_W // 2, CELL_H // 2), Image.Resampling.NEAREST).resize((CELL_W, CELL_H), Image.Resampling.NEAREST)


def checker(size: tuple[int, int], square: int = 16) -> Image.Image:
    image = Image.new("RGB", size, "#ffffff")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], square):
        for x in range(0, size[0], square):
            if (x // square + y // square) % 2:
                draw.rectangle((x, y, x + square - 1, y + square - 1), fill="#e8e8e8")
    return image


def frame_from_sheet(sheet: Image.Image, row: int, column: int) -> Image.Image:
    return sheet.crop(
        (
            column * CELL_W,
            row * CELL_H,
            (column + 1) * CELL_W,
            (row + 1) * CELL_H,
        )
    )


def composite_on_checker(frame: Image.Image, scale: float = 1.0) -> Image.Image:
    width = max(1, round(CELL_W * scale))
    height = max(1, round(CELL_H * scale))
    frame = frame.resize((width, height), Image.Resampling.NEAREST)
    background = checker((width, height), square=max(4, round(16 * scale)))
    background.paste(frame, (0, 0), frame)
    return background


def make_contact_sheet(sheet: Image.Image) -> Image.Image:
    scale = 0.58
    label_h = 24
    cell_w = round(CELL_W * scale)
    cell_h = round(CELL_H * scale)
    width = COLS * cell_w
    height = ROWS * (cell_h + label_h)
    contact = Image.new("RGB", (width, height), "#f7f7f7")
    draw = ImageDraw.Draw(contact)
    font = ImageFont.load_default()

    for row, state in enumerate(ROW_NAMES):
        y = row * (cell_h + label_h)
        draw.rectangle((0, y, width, y + label_h - 1), fill="#111111")
        draw.text((6, y + 6), f"row {row}: {state}", fill="#ffffff", font=font)
        draw.text((width - 86, y + 6), f"{USED_FRAMES_BY_ROW[row]} frames", fill="#ffffff", font=font)
        for column in range(COLS):
            frame = frame_from_sheet(sheet, row, column)
            preview = composite_on_checker(frame, scale=scale)
            x = column * cell_w
            contact.paste(preview, (x, y + label_h))
            outline = "#18a058" if column < USED_FRAMES_BY_ROW[row] else "#cc3344"
            draw.rectangle((x, y + label_h, x + cell_w - 1, y + label_h + cell_h - 1), outline=outline)
            draw.text((x + 4, y + label_h + 4), str(column), fill="#111111", font=font)
    return contact


def save_animation_previews(sheet: Image.Image) -> None:
    frames_root = PET_DIR / "frames"
    previews_root = PET_DIR / "previews"
    if frames_root.exists():
        shutil.rmtree(frames_root)
    if previews_root.exists():
        shutil.rmtree(previews_root)
    frames_root.mkdir(parents=True)
    previews_root.mkdir(parents=True)

    for row, state in enumerate(ROW_NAMES):
        state_dir = frames_root / state
        state_dir.mkdir()
        frames = []
        for column in range(USED_FRAMES_BY_ROW[row]):
            frame = frame_from_sheet(sheet, row, column)
            frame.save(state_dir / f"{column:02d}.png")
            frames.append(composite_on_checker(frame))
        frames[0].save(
            previews_root / f"{state}.gif",
            save_all=True,
            append_images=frames[1:],
            duration=ROW_DURATIONS[state],
            loop=0,
            disposal=2,
            optimize=False,
        )


def main() -> None:
    PET_DIR.mkdir(parents=True, exist_ok=True)
    row_sprites = load_pose_sprites()
    overrides = load_action_overrides()

    sheet = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (255, 255, 255, 0))
    for row in range(ROWS):
        for col in range(USED_FRAMES_BY_ROW[row]):
            if row == 7 and 4 in overrides:
                frame = build_running_from_jump_frame(col, overrides[4])
            elif row in overrides:
                frame = build_override_frame(row, col, overrides[row][col])
            else:
                frame = build_frame(row_sprites, row, col)
            sheet.alpha_composite(frame, (col * CELL_W, row * CELL_H))

    sheet.save(PET_DIR / "spritesheet.webp", "WEBP", lossless=True, quality=100, method=6)
    sheet.save(PET_DIR / "spritesheet.png")
    make_contact_sheet(sheet).save(PET_DIR / "preview.webp", "WEBP", lossless=True, quality=100, method=6)
    make_contact_sheet(sheet).save(PET_DIR / "contact-sheet.png")
    save_animation_previews(sheet)


if __name__ == "__main__":
    main()
