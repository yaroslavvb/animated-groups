"""Pillow renderer and GIF loop auditing utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
import json
import math
import statistics
from typing import Callable, Iterable, Sequence

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageSequence

from .groups import (
    EXAMPLES,
    MotifState,
    diagonal_relay_states,
    dihedral_choreography_states,
    glide_time_reversal_states,
    mixed_time_glide_states,
    rotary_time_reversal_states,
    time_screw_states,
)


BACKGROUND_TOP = (8, 17, 32)
BACKGROUND_BOTTOM = (14, 26, 45)
GUIDE = (102, 127, 154, 72)
GUIDE_BRIGHT = (151, 174, 197, 118)
INK = (235, 244, 255, 235)
ACCENTS = (
    (50, 214, 190),   # turquoise
    (255, 105, 120),  # coral
    (255, 204, 102),  # amber
    (174, 116, 255),  # violet
    (74, 181, 255),
    (255, 139, 61),
)


@dataclass(frozen=True)
class GifAudit:
    path: str
    frame_count: int
    expected_frames: int
    loop: int | None
    durations_ms: tuple[int, ...]
    expected_duration_ms: int | None
    effective_fps: float
    dimensions: tuple[int, int]
    first_last_identical: bool
    seam_rms: float
    median_internal_rms: float
    seam_ratio: float
    passes: bool
    checks: tuple[str, ...]


def _lerp(a: int, b: int, amount: float) -> int:
    return round(a + (b - a) * amount)


def _background(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), BACKGROUND_TOP + (255,))
    draw = ImageDraw.Draw(image)
    for y in range(size):
        amount = y / max(1, size - 1)
        # A restrained vertical gradient remains compatible with rotations only
        # after a quarter-turn, so screw frames receive an added radial veil
        # below.  The actual gradient is deliberately subtle.
        color = tuple(_lerp(a, b, amount) for a, b in zip(BACKGROUND_TOP, BACKGROUND_BOTTOM))
        draw.line((0, y, size, y), fill=color + (255,))
    return image


def _radial_background(size: int) -> Image.Image:
    """A C-infinity background for the time-screw example."""

    mask = Image.radial_gradient("L").resize((size, size), Image.Resampling.BICUBIC)
    return ImageOps.colorize(mask, black=BACKGROUND_TOP, white=BACKGROUND_BOTTOM).convert("RGBA")


def _flat_background(size: int) -> Image.Image:
    """A translation-invariant background for doubly periodic scenes."""

    return Image.new("RGBA", (size, size), (9, 19, 35, 255))


def _rgba_layer(size: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return layer, ImageDraw.Draw(layer)


def _map_point(x: float, y: float, size: int) -> tuple[float, float]:
    # Pillow's mirror/transpose operations act around (size - 1) / 2.
    extent = size - 1
    return (0.5 * (x + 1.0) * extent, 0.5 * (y + 1.0) * extent)


def _map_periodic_x_point(x: float, y: float, size: int) -> tuple[float, float]:
    """Map the relay's x circle so one cell is exactly size/order pixels."""

    return (0.5 * (x + 1.0) * size % size, 0.5 * (y + 1.0) * (size - 1))


def _map_periodic_xy_point(x: float, y: float, size: int) -> tuple[float, float]:
    """Map both spatial coordinates to a square torus."""

    return (0.5 * (x + 1.0) * size % size, 0.5 * (y + 1.0) * size % size)


def _map_for_topology(
    x: float,
    y: float,
    size: int,
    topology: str,
) -> tuple[float, float]:
    if topology == "plane":
        return _map_point(x, y, size)
    if topology == "torus_x":
        return _map_periodic_x_point(x, y, size)
    if topology == "torus_xy":
        return _map_periodic_xy_point(x, y, size)
    raise ValueError(f"unknown drawing topology {topology!r}")


def _draw_glide_guides(image: Image.Image) -> None:
    size = image.width
    layer, draw = _rgba_layer(size)
    cx = (size - 1) / 2.0
    dash = max(5, round(size * 0.015))
    gap = dash
    width = max(1, round(size * 0.0035))
    y = size * 0.12
    while y < size * 0.88:
        draw.line((cx, y, cx, min(size * 0.88, y + dash)), fill=GUIDE_BRIGHT, width=width)
        y += dash + gap

    for x_center in (-0.43, 0.43):
        px, py = _map_point(x_center, 0.0, size)
        rx = size * 0.075
        ry = size * 0.105
        draw.ellipse((px - rx, py - ry, px + rx, py + ry), outline=GUIDE, width=width)

    # Two neutral frame brackets make the pair/coset structure legible while
    # remaining exactly mirror-related.
    inset = size * 0.08
    mid_gap = size * 0.055
    radius = round(size * 0.035)
    draw.rounded_rectangle(
        (inset, size * 0.20, cx - mid_gap, size * 0.80),
        radius=radius,
        outline=GUIDE,
        width=width,
    )
    draw.rounded_rectangle(
        (cx + mid_gap, size * 0.20, size - 1 - inset, size * 0.80),
        radius=radius,
        outline=GUIDE,
        width=width,
    )
    image.alpha_composite(layer)


def _draw_screw_guides(image: Image.Image, order: int) -> None:
    size = image.width
    layer, draw = _rgba_layer(size)
    center = (size - 1) / 2.0
    width = max(1, round(size * 0.0035))

    for radius in (size * 0.19, size * 0.255, size * 0.34):
        draw.ellipse(
            (center - radius, center - radius, center + radius, center + radius),
            outline=GUIDE if radius != size * 0.255 else GUIDE_BRIGHT,
            width=width,
        )
    for j in range(order):
        angle = 2.0 * math.pi * j / order
        inner = size * 0.10
        outer = size * 0.39
        draw.line(
            (
                center + inner * math.cos(angle),
                center + inner * math.sin(angle),
                center + outer * math.cos(angle),
                center + outer * math.sin(angle),
            ),
            fill=GUIDE,
            width=width,
        )
    draw.ellipse(
        (center - size * 0.042, center - size * 0.042, center + size * 0.042, center + size * 0.042),
        fill=(18, 35, 57, 255),
        outline=GUIDE_BRIGHT,
        width=width,
    )
    image.alpha_composite(layer)


def _draw_relay_guides(image: Image.Image, order: int) -> None:
    size = image.width
    layer, draw = _rgba_layer(size)
    width = max(1, round(size * 0.0035))
    cell_width = size / order

    # Each cell gets exactly the same neutral guide.  The left/right boundary
    # is understood periodically, like a three-site ring unwrapped into a row.
    for j in range(order):
        left = j * cell_width
        right = (j + 1) * cell_width
        draw.rounded_rectangle(
            (left + size * 0.018, size * 0.24, right - size * 0.018, size * 0.76),
            radius=round(size * 0.03),
            fill=(19, 37, 60, 130),
            outline=GUIDE,
            width=width,
        )
        cx = left + cell_width / 2.0
        cy = size / 2.0
        draw.ellipse(
            (cx - size * 0.065, cy - size * 0.17, cx + size * 0.065, cy + size * 0.17),
            outline=GUIDE_BRIGHT,
            width=width,
        )
    # Full-width rails have no distinguished gap, so a one-cell torus
    # translation preserves the complete neutral guide.
    rail_y = (size * 0.17, size * 0.83)
    for y in rail_y:
        draw.line((0, y, size - 1, y), fill=GUIDE, width=width)
        for j in range(order):
            cx = (j + 0.5) * cell_width
            r = size * 0.012
            draw.ellipse((cx - r, y - r, cx + r, y + r), fill=GUIDE_BRIGHT)
    image.alpha_composite(layer)


def _draw_mixed_glide_guides(image: Image.Image) -> None:
    """A 2x2 torus guide invariant under x-reflection + half-y shift."""

    size = image.width
    layer, draw = _rgba_layer(size)
    width = max(1, round(size * 0.0035))
    cell = size / 2.0
    gap = size * 0.022
    radius = round(size * 0.03)

    for row in range(2):
        for column in range(2):
            left = column * cell + gap
            top = row * cell + gap
            right = (column + 1) * cell - gap
            bottom = (row + 1) * cell - gap
            draw.rounded_rectangle(
                (left, top, right, bottom),
                radius=radius,
                fill=(19, 37, 60, 125),
                outline=GUIDE,
                width=width,
            )

    # The solid mirror axis survives the half-cell vertical translation.
    center = (size - 1) / 2.0
    draw.line((center, 0, center, size - 1), fill=GUIDE_BRIGHT, width=width)
    for y in (0, cell, size - 1):
        draw.line((0, y, size - 1, y), fill=GUIDE, width=width)

    for x, y in ((-0.42, -0.48), (0.42, 0.52)):
        cx, cy = _map_periodic_xy_point(x, y, size)
        rx = size * 0.072
        ry = size * 0.088
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=GUIDE_BRIGHT, width=width)
    image.alpha_composite(layer)


def _draw_rotary_reversal_guides(image: Image.Image) -> None:
    _draw_screw_guides(image, 4)
    size = image.width
    layer, draw = _rgba_layer(size)
    center = (size - 1) / 2.0
    width = max(1, round(size * 0.003))
    for radius in (size * 0.145, size * 0.305):
        points = [
            (center + radius * math.cos(math.pi / 4.0 + j * math.pi / 2.0),
             center + radius * math.sin(math.pi / 4.0 + j * math.pi / 2.0))
            for j in range(4)
        ]
        draw.line((*points, points[0]), fill=GUIDE, width=width, joint="curve")
    image.alpha_composite(layer)


def _draw_dihedral_guides(image: Image.Image) -> None:
    _draw_screw_guides(image, 3)
    size = image.width
    layer, draw = _rgba_layer(size)
    center = (size - 1) / 2.0
    width = max(1, round(size * 0.003))
    radius = size * 0.39
    # Three full reflection axes distinguish D3 from the cyclic C3 screw.
    for j in range(3):
        angle = j * math.pi / 3.0
        dx = radius * math.cos(angle)
        dy = radius * math.sin(angle)
        draw.line((center - dx, center - dy, center + dx, center + dy), fill=GUIDE, width=width)
    image.alpha_composite(layer)


def _transformed_points(
    points: Iterable[tuple[float, float]],
    center: tuple[float, float],
    radius: float,
    angle: float,
    chirality: int,
) -> list[tuple[float, float]]:
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    transformed: list[tuple[float, float]] = []
    for local_x, local_y in points:
        # Reflecting local y is the chirality switch.  Together with
        # angle -> pi-angle it makes a global x reflection exact.
        local_y *= chirality
        x = radius * (cos_a * local_x - sin_a * local_y)
        y = radius * (sin_a * local_x + cos_a * local_y)
        transformed.append((center[0] + x, center[1] + y))
    return transformed


def _draw_glows(
    image: Image.Image,
    states: Sequence[MotifState],
    *,
    topology: str = "plane",
) -> None:
    size = image.width
    glow_layer, glow_draw = _rgba_layer(size)
    for state in states:
        center = _map_for_topology(state.x, state.y, size, topology)
        radius = size * 0.085 * state.scale
        color = ACCENTS[state.color % len(ACCENTS)]
        glow_radius = radius * (0.95 + 0.15 * state.glow)
        alpha = round(36 + 38 * state.glow)
        glow_draw.ellipse(
            (
                center[0] - glow_radius,
                center[1] - glow_radius,
                center[0] + glow_radius,
                center[1] + glow_radius,
            ),
            fill=color + (alpha,),
        )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=max(2, round(size * 0.018))))
    image.alpha_composite(glow_layer)


def _draw_motif(image: Image.Image, state: MotifState, *, topology: str = "plane") -> None:
    size = image.width
    center = _map_for_topology(state.x, state.y, size, topology)
    radius = size * 0.085 * state.scale
    color = ACCENTS[state.color % len(ACCENTS)]

    # An asymmetric, chiral kite.  The notch and off-center eye make reflection
    # and rotation visible even when motion temporarily slows.
    if state.glyph == "kite":
        outline = (
            (-0.84, -0.24),
            (-0.28, -0.76),
            (0.30, -0.55),
            (0.88, -0.08),
            (0.30, 0.12),
            (0.58, 0.76),
            (-0.10, 0.48),
            (-0.67, 0.66),
            (-0.48, 0.08),
        )
        inner = (
            (-0.43, -0.19),
            (0.04, -0.43),
            (0.48, -0.10),
            (0.07, 0.05),
            (0.25, 0.40),
            (-0.16, 0.25),
        )
        eye_local = (0.27, -0.18)
        tail_local = (-0.82, 0.15)
    elif state.glyph == "dart":
        # Mirror-symmetric about local y=0, allowing a three-motif D3 orbit.
        outline = (
            (-0.86, -0.36),
            (0.04, -0.36),
            (0.04, -0.69),
            (0.88, 0.0),
            (0.04, 0.69),
            (0.04, 0.36),
            (-0.86, 0.36),
            (-0.55, 0.0),
        )
        inner = (
            (-0.45, -0.17),
            (0.12, -0.17),
            (0.52, 0.0),
            (0.12, 0.17),
            (-0.45, 0.17),
            (-0.28, 0.0),
        )
        eye_local = (0.25, 0.0)
        tail_local = (-0.72, 0.0)
    else:
        raise ValueError(f"unknown glyph {state.glyph!r}")
    outer_points = _transformed_points(outline, center, radius, state.angle, state.chirality)
    inner_points = _transformed_points(inner, center, radius, state.angle, state.chirality)

    draw = ImageDraw.Draw(image)
    outline_width = max(2, round(size * 0.006))
    draw.polygon(outer_points, fill=color + (255,), outline=INK[:3] + (255,), width=outline_width)
    darker = tuple(round(component * 0.36) for component in color)
    draw.polygon(inner_points, fill=darker + (255,))

    # Eye and trailing bead are locked to the same local pose, so they obey the
    # identical group action as the outer kite.
    eye = _transformed_points((eye_local,), center, radius, state.angle, state.chirality)[0]
    eye_radius = radius * 0.10
    draw.ellipse(
        (eye[0] - eye_radius, eye[1] - eye_radius, eye[0] + eye_radius, eye[1] + eye_radius),
        fill=(245, 251, 255, 255),
    )
    pupil_radius = eye_radius * 0.42
    draw.ellipse(
        (eye[0] - pupil_radius, eye[1] - pupil_radius, eye[0] + pupil_radius, eye[1] + pupil_radius),
        fill=(7, 14, 27, 255),
    )
    tail = _transformed_points((tail_local,), center, radius, state.angle, state.chirality)[0]
    tail_radius = radius * (0.075 + 0.035 * state.glow)
    draw.ellipse(
        (tail[0] - tail_radius, tail[1] - tail_radius, tail[0] + tail_radius, tail[1] + tail_radius),
        fill=(245, 251, 255, 255),
    )


@lru_cache(maxsize=16)
def _base_scene(example: str, render_size: int, order: int) -> Image.Image:
    if example == "time_screw":
        image = _radial_background(render_size)
        _draw_screw_guides(image, order)
    elif example == "time_glide":
        image = _background(render_size)
        _draw_glide_guides(image)
    elif example == "diagonal_relay":
        image = _background(render_size)
        _draw_relay_guides(image, order)
    elif example == "mixed_time_glide":
        image = _flat_background(render_size)
        _draw_mixed_glide_guides(image)
    elif example == "glide_time_reversal":
        image = _background(render_size)
        _draw_relay_guides(image, 2)
    elif example == "rotary_time_reversal":
        image = _radial_background(render_size)
        _draw_rotary_reversal_guides(image)
    elif example == "dihedral_choreography":
        image = _radial_background(render_size)
        _draw_dihedral_guides(image)
    else:
        choices = ", ".join(sorted(EXAMPLES))
        raise ValueError(f"unknown example {example!r}; choose from {choices}")
    return image


def render_frame(
    example: str,
    phase: float,
    *,
    size: int = 600,
    screw_order: int = 4,
    relay_order: int = 3,
    supersample: int = 2,
) -> Image.Image:
    """Render one RGB frame at normalized phase ``phase``."""

    if size < 240:
        raise ValueError("size must be at least 240 pixels")
    if supersample < 1:
        raise ValueError("supersample must be at least 1")

    render_size = size * supersample
    if example == "time_screw":
        image = _base_scene(example, render_size, screw_order).copy()
        states = time_screw_states(phase, screw_order)
    elif example == "time_glide":
        image = _base_scene(example, render_size, 2).copy()
        states = EXAMPLES[example].state_function(phase)
    elif example == "diagonal_relay":
        if size % relay_order:
            raise ValueError(f"relay size {size} must be divisible by relay order {relay_order}")
        image = _base_scene(example, render_size, relay_order).copy()
        states = diagonal_relay_states(phase, relay_order)
    elif example == "mixed_time_glide":
        if size % 2:
            raise ValueError("mixed time-glide size must be even")
        image = _base_scene(example, render_size, 2).copy()
        states = mixed_time_glide_states(phase)
    elif example == "glide_time_reversal":
        if size % 2:
            raise ValueError("glide time-reversal size must be even")
        image = _base_scene(example, render_size, 2).copy()
        states = glide_time_reversal_states(phase)
    elif example == "rotary_time_reversal":
        image = _base_scene(example, render_size, 4).copy()
        states = rotary_time_reversal_states(phase)
    elif example == "dihedral_choreography":
        image = _base_scene(example, render_size, 3).copy()
        states = dihedral_choreography_states(phase)
    else:
        choices = ", ".join(sorted(EXAMPLES))
        raise ValueError(f"unknown example {example!r}; choose from {choices}")

    topology = (
        "torus_xy"
        if example == "mixed_time_glide"
        else "torus_x"
        if example in {"diagonal_relay", "glide_time_reversal"}
        else "plane"
    )
    _draw_glows(image, states, topology=topology)
    for state in states:
        _draw_motif(image, state, topology=topology)

    if supersample > 1:
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image.convert("RGB")


def render_frames(
    example: str,
    *,
    frame_count: int = 60,
    size: int = 600,
    screw_order: int = 4,
    relay_order: int = 3,
    supersample: int = 2,
) -> list[Image.Image]:
    if example not in EXAMPLES:
        choices = ", ".join(sorted(EXAMPLES))
        raise ValueError(f"unknown example {example!r}; choose from {choices}")
    order = (
        screw_order
        if example == "time_screw"
        else relay_order
        if example == "diagonal_relay"
        else EXAMPLES[example].sampling_order
    )
    if frame_count < 2 * order:
        raise ValueError(f"frame count must be at least twice the group order ({2 * order})")
    if frame_count % order:
        raise ValueError(f"frame count {frame_count} must be divisible by group order {order}")
    return [
        render_frame(
            example,
            frame / frame_count,
            size=size,
            screw_order=screw_order,
            relay_order=relay_order,
            supersample=supersample,
        )
        for frame in range(frame_count)
    ]


def save_looping_gif(
    frames: Sequence[Image.Image],
    path: str | Path,
    *,
    fps: int = 20,
) -> Path:
    """Save frames with an infinite-loop extension and one shared palette."""

    if len(frames) < 2:
        raise ValueError("a looping animation needs at least two frames")
    dimensions = {frame.size for frame in frames}
    if len(dimensions) != 1:
        raise ValueError("all GIF frames must have identical dimensions")

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = gif_duration_ms(fps)

    palette_source = frames[0].quantize(colors=192, method=Image.Quantize.MEDIANCUT)
    paletted = [palette_source]
    paletted.extend(
        frame.quantize(palette=palette_source, dither=Image.Dither.NONE)
        for frame in frames[1:]
    )
    paletted[0].save(
        output,
        save_all=True,
        append_images=paletted[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
        comment=b"Periodic samples t=k/N; endpoint t=1 intentionally omitted.",
    )
    return output


def _rms_difference(first: Image.Image, second: Image.Image) -> float:
    difference = ImageChops.difference(first.convert("RGB"), second.convert("RGB"))
    histogram = difference.histogram()
    squared_sum = sum((index % 256) ** 2 * count for index, count in enumerate(histogram))
    samples = first.width * first.height * 3
    return math.sqrt(squared_sum / max(1, samples))


def gif_duration_ms(fps: int) -> int:
    """Return the nearest GIF-compatible (10 ms) delay for a target fps."""

    if not 1 <= fps <= 100:
        raise ValueError("fps must be between 1 and 100 for GIF output")
    centiseconds = max(1, math.floor(100.0 / fps + 0.5))
    return centiseconds * 10


def audit_gif(
    path: str | Path,
    *,
    expected_frames: int,
    expected_duration_ms: int | None = None,
) -> GifAudit:
    """Decode a GIF and verify both metadata and the visual seam."""

    gif_path = Path(path)
    with Image.open(gif_path) as image:
        loop = image.info.get("loop")
        decoded = [frame.convert("RGB").copy() for frame in ImageSequence.Iterator(image)]
        durations = []
        for index in range(image.n_frames):
            image.seek(index)
            durations.append(int(image.info.get("duration", 0)))

    transitions = [
        _rms_difference(decoded[index], decoded[index + 1])
        for index in range(len(decoded) - 1)
    ]
    seam = _rms_difference(decoded[-1], decoded[0])
    median_internal = statistics.median(transitions) if transitions else 0.0
    seam_ratio = seam / median_internal if median_internal > 0 else math.inf
    first_last_identical = ImageChops.difference(decoded[0], decoded[-1]).getbbox() is None

    checks: list[str] = []
    if len(decoded) != expected_frames:
        checks.append(f"decoded {len(decoded)} frames, expected {expected_frames}")
    if loop != 0:
        checks.append(f"loop metadata is {loop!r}, expected 0 (infinite)")
    if len(set(durations)) != 1 or not durations or durations[0] <= 0:
        checks.append(f"frame durations are not one uniform positive value: {durations}")
    if expected_duration_ms is not None and any(duration != expected_duration_ms for duration in durations):
        checks.append(
            f"encoded durations differ from expected GIF delay {expected_duration_ms} ms: {durations}"
        )
    if first_last_identical:
        checks.append("first and last frames are duplicates, which creates a pause")
    # A seam can naturally be a little faster than the median transition, but
    # should never be an outlier.  Collective phase-offset motion makes 1.8 a
    # conservative cutoff for these scenes.
    if not math.isfinite(seam_ratio) or seam_ratio > 1.8:
        checks.append(f"seam RMS ratio {seam_ratio:.3f} exceeds 1.8")

    return GifAudit(
        path=str(gif_path),
        frame_count=len(decoded),
        expected_frames=expected_frames,
        loop=loop,
        durations_ms=tuple(durations),
        expected_duration_ms=expected_duration_ms,
        effective_fps=1000.0 / durations[0] if durations and durations[0] else 0.0,
        dimensions=decoded[0].size,
        first_last_identical=first_last_identical,
        seam_rms=seam,
        median_internal_rms=median_internal,
        seam_ratio=seam_ratio,
        passes=not checks,
        checks=tuple(checks),
    )


def write_audit_report(audits: Sequence[GifAudit], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "all_pass": all(audit.passes for audit in audits),
        "gifs": [asdict(audit) for audit in audits],
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output
