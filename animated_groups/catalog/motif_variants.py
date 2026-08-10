"""Plain motif variants for the four curated catalog symmetries.

The original catalog scenes use petals, ribbons, elastic curves, and liquid
fills.  This module deliberately keeps the graphics elementary: ``discs`` are
tokens and ``bars`` are rigid blocks.  Both styles are projections of the
same exact analytic states in :mod:`animated_groups.catalog.patterns`, so the
spacetime-group identities do not depend on the artwork.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw

from animated_groups.rendering import (
    GifAudit,
    audit_gif,
    gif_duration_ms,
    save_looping_gif,
)

from .patterns import (
    PATTERNS,
    ElasticEdgeState,
    IrisPetalState,
    LiquidCellState,
    WaveSegmentState,
    elastic_d4_state,
    iris_c6_state,
    liquid_c2_state,
    wave_loom_c5_state,
)
from .render import compatible_frame_count


TAU = 2.0 * math.pi

CATALOG_VARIANT_KEYS = (
    "iris_c6_time_screw",
    "wave_loom_c5_relay",
    "elastic_d4_choreography",
    "liquid_c2_centered_lattice",
)
VARIANT_STYLES = ("discs", "bars")

VariantState = tuple[
    IrisPetalState | WaveSegmentState | ElasticEdgeState | LiquidCellState, ...
]

_STATE_FUNCTIONS: dict[str, Callable[[float], VariantState]] = {
    "iris_c6_time_screw": iris_c6_state,
    "wave_loom_c5_relay": wave_loom_c5_state,
    "elastic_d4_choreography": elastic_d4_state,
    "liquid_c2_centered_lattice": liquid_c2_state,
}

_PAPER = (246, 244, 239, 255)
_INK = (28, 34, 43, 255)
_MUTED = (167, 169, 166, 255)
_BLUE = (44, 112, 190, 255)
_RED = (205, 77, 70, 255)
_YELLOW = (229, 174, 52, 255)
_GREEN = (43, 142, 113, 255)


def catalog_variant_state(key: str, phase: float) -> VariantState:
    """Return the exact state used by both visual styles for ``key``."""

    try:
        state_function = _STATE_FUNCTIONS[key]
    except KeyError as error:
        choices = ", ".join(CATALOG_VARIANT_KEYS)
        raise ValueError(f"unknown catalog variant {key!r}; choose from {choices}") from error
    return state_function(phase)


def _mix(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
    amount: float,
) -> tuple[int, int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))


def _ellipse(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    radius: float,
    *,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] = _INK,
    width: int,
) -> None:
    x, y = center
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        fill=fill,
        outline=outline,
        width=width,
    )


def _oriented_block(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    along: tuple[float, float],
    length: float,
    breadth: float,
    *,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] = _INK,
    width: int,
) -> None:
    cross = (-along[1], along[0])
    half_length = length / 2.0
    half_breadth = breadth / 2.0
    points = [
        (
            center[0] + along[0] * half_length * length_sign
            + cross[0] * half_breadth * breadth_sign,
            center[1] + along[1] * half_length * length_sign
            + cross[1] * half_breadth * breadth_sign,
        )
        for length_sign, breadth_sign in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    ]
    draw.polygon(points, fill=fill)
    draw.line((*points, points[0]), fill=outline, width=width, joint="curve")


def _periodic_ellipse(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    radius: float,
    size: int,
    *,
    fill: tuple[int, int, int, int],
    width: int,
) -> None:
    for offset in (-size, 0, size):
        _ellipse(
            draw,
            (center[0] + offset, center[1]),
            radius,
            fill=fill,
            width=width,
        )


def _draw_iris_discs(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), _PAPER)
    draw = ImageDraw.Draw(image, "RGBA")
    center = (size / 2.0, size / 2.0)
    outline = max(1, round(size * 0.006))
    for state in iris_c6_state(phase):
        angle = TAU * state.slot / 6.0
        normal = (math.cos(angle), math.sin(angle))
        tangent = (-normal[1], normal[0])
        radial = state.radius * size * 0.54
        skew = state.tangent_skew * size * 0.50
        point = (
            center[0] + radial * normal[0] + skew * tangent[0],
            center[1] + radial * normal[1] + skew * tangent[1],
        )
        radius = size * (0.037 + 0.018 * state.tone)
        _ellipse(
            draw,
            point,
            radius,
            fill=_mix(_BLUE, _RED, state.tone),
            width=outline,
        )
    _ellipse(
        draw,
        center,
        size * 0.045,
        fill=_YELLOW,
        width=outline,
    )
    return image


def _draw_iris_bars(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), _PAPER)
    draw = ImageDraw.Draw(image, "RGBA")
    center = (size / 2.0, size / 2.0)
    outline = max(1, round(size * 0.006))
    inner_radius = size * 0.095
    for state in iris_c6_state(phase):
        angle = TAU * state.slot / 6.0
        normal = (math.cos(angle), math.sin(angle))
        tangent = (-normal[1], normal[0])
        outer_radius = state.radius * size * 0.55
        length = max(size * 0.08, outer_radius - inner_radius)
        center_radius = inner_radius + length / 2.0
        skew = state.tangent_skew * size * 0.42
        point = (
            center[0] + center_radius * normal[0] + skew * tangent[0],
            center[1] + center_radius * normal[1] + skew * tangent[1],
        )
        _oriented_block(
            draw,
            point,
            normal,
            length,
            size * (0.050 + 0.025 * state.tone),
            fill=_mix(_GREEN, _BLUE, state.tone),
            width=outline,
        )
    _ellipse(draw, center, size * 0.055, fill=_INK, outline=_INK, width=outline)
    return image


def _draw_wave_discs(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), _PAPER)
    draw = ImageDraw.Draw(image, "RGBA")
    outline = max(1, round(size * 0.006))
    guide = max(1, round(size * 0.003))
    cell = size / 5.0
    for slot in range(5):
        draw.line((slot * cell, 0, slot * cell, size), fill=_MUTED, width=guide)
    for state in wave_loom_c5_state(phase):
        x = (state.slot + state.shuttle) * cell
        y = size * (0.50 + 0.27 * state.first_control_y)
        radius = size * (0.030 + 0.018 * (0.5 + state.second_control_y))
        fill = _mix(_BLUE, _RED, 0.5 + state.first_control_y)
        _periodic_ellipse(
            draw,
            (x, y),
            radius,
            size,
            fill=fill,
            width=outline,
        )
    return image


def _draw_wave_bars(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), _PAPER)
    draw = ImageDraw.Draw(image, "RGBA")
    outline = max(1, round(size * 0.006))
    guide = max(1, round(size * 0.003))
    cell = size / 5.0
    for slot in range(5):
        draw.line((slot * cell, 0, slot * cell, size), fill=_MUTED, width=guide)
    for state in wave_loom_c5_state(phase):
        x = (state.slot + state.shuttle) * cell
        y = size * (0.50 + 0.18 * state.second_control_y)
        length = size * (0.15 + 0.18 * (0.5 + state.first_control_y))
        breadth = cell * 0.34
        fill = _mix(_YELLOW, _GREEN, 0.5 + state.second_control_y)
        for offset in (-size, 0, size):
            _oriented_block(
                draw,
                (x + offset, y),
                (0.0, 1.0),
                length,
                breadth,
                fill=fill,
                width=outline,
            )
    return image


def _elastic_geometry(
    state: ElasticEdgeState,
    size: int,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    angle = TAU * state.slot / 4.0
    normal = (math.cos(angle), math.sin(angle))
    tangent = (-normal[1], normal[0])
    center = (size / 2.0, size / 2.0)
    radial = size * (0.25 + 0.62 * state.normal_bulge)
    skew = size * 0.55 * state.tangent_skew
    point = (
        center[0] + radial * normal[0] + skew * tangent[0],
        center[1] + radial * normal[1] + skew * tangent[1],
    )
    return point, normal, tangent


def _draw_elastic_discs(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), _PAPER)
    draw = ImageDraw.Draw(image, "RGBA")
    outline = max(1, round(size * 0.006))
    for state in elastic_d4_state(phase):
        point, _, _ = _elastic_geometry(state, size)
        _ellipse(
            draw,
            point,
            size * (0.047 + 0.017 * state.tone),
            fill=_mix(_BLUE, _RED, state.tone),
            width=outline,
        )
    _ellipse(
        draw,
        (size / 2.0, size / 2.0),
        size * 0.025,
        fill=_INK,
        outline=_INK,
        width=outline,
    )
    return image


def _draw_elastic_bars(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), _PAPER)
    draw = ImageDraw.Draw(image, "RGBA")
    outline = max(1, round(size * 0.006))
    for state in elastic_d4_state(phase):
        point, _, tangent = _elastic_geometry(state, size)
        _oriented_block(
            draw,
            point,
            tangent,
            size * (0.17 + 0.09 * state.tone),
            size * 0.055,
            fill=_mix(_GREEN, _YELLOW, state.tone),
            width=outline,
        )
    return image


def _draw_lattice_guides(draw: ImageDraw.ImageDraw, size: int) -> None:
    width = max(1, round(size * 0.003))
    for coordinate in (0.0, size / 2.0):
        draw.line((coordinate, 0, coordinate, size), fill=_MUTED, width=width)
        draw.line((0, coordinate, size, coordinate), fill=_MUTED, width=width)


def _liquid_palette(orbit: int) -> tuple[int, int, int, int]:
    return _BLUE if orbit == 0 else _RED


def _draw_liquid_discs(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), _PAPER)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_lattice_guides(draw, size)
    outline = max(1, round(size * 0.006))
    cell = size / 2.0
    for state in liquid_c2_state(phase):
        center = (
            (state.column + 0.5) * cell + (state.bubble_x - 0.5) * cell * 0.34,
            (state.row + 0.5) * cell + (state.bubble_depth - 0.5) * cell * 0.34,
        )
        radius = cell * (0.105 + 0.075 * state.fill)
        _ellipse(
            draw,
            center,
            radius,
            fill=_liquid_palette(state.orbit),
            width=outline,
        )
        token_radius = radius * 0.28
        _ellipse(
            draw,
            center,
            token_radius,
            fill=_PAPER,
            width=max(1, outline // 2),
        )
    return image


def _draw_liquid_bars(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), _PAPER)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_lattice_guides(draw, size)
    outline = max(1, round(size * 0.006))
    cell = size / 2.0
    for state in liquid_c2_state(phase):
        angle = state.tilt * 2.2
        along = (math.sin(angle), math.cos(angle))
        center = (
            (state.column + 0.5) * cell + (state.bubble_x - 0.5) * cell * 0.24,
            (state.row + 0.5) * cell,
        )
        _oriented_block(
            draw,
            center,
            along,
            cell * (0.32 + 0.34 * state.fill),
            cell * 0.22,
            fill=_liquid_palette(state.orbit),
            width=outline,
        )
    return image


_DRAWERS: dict[tuple[str, str], Callable[[float, int], Image.Image]] = {
    ("iris_c6_time_screw", "discs"): _draw_iris_discs,
    ("iris_c6_time_screw", "bars"): _draw_iris_bars,
    ("wave_loom_c5_relay", "discs"): _draw_wave_discs,
    ("wave_loom_c5_relay", "bars"): _draw_wave_bars,
    ("elastic_d4_choreography", "discs"): _draw_elastic_discs,
    ("elastic_d4_choreography", "bars"): _draw_elastic_bars,
    ("liquid_c2_centered_lattice", "discs"): _draw_liquid_discs,
    ("liquid_c2_centered_lattice", "bars"): _draw_liquid_bars,
}


def _validate_render_request(
    key: str,
    style: str,
    frame_count: int,
    size: int,
    supersample: int,
) -> None:
    if key not in CATALOG_VARIANT_KEYS:
        choices = ", ".join(CATALOG_VARIANT_KEYS)
        raise ValueError(f"unknown catalog variant {key!r}; choose from {choices}")
    if style not in VARIANT_STYLES:
        choices = ", ".join(VARIANT_STYLES)
        raise ValueError(f"unknown motif style {style!r}; choose from {choices}")
    divisor = PATTERNS[key].phase_divisor
    if frame_count < 2 * divisor:
        raise ValueError(f"frame count must be at least twice the phase divisor ({2 * divisor})")
    if frame_count % divisor:
        raise ValueError(
            f"frame count {frame_count} must be divisible by phase divisor {divisor}"
        )
    if size < 32:
        raise ValueError("size must be at least 32 pixels")
    if supersample < 1:
        raise ValueError("supersample must be positive")


def render_catalog_variant_frames(
    key: str,
    style: str,
    frame_count: int = 60,
    size: int = 420,
    supersample: int = 2,
) -> list[Image.Image]:
    """Render one elementary-motif loop without duplicating phase one."""

    _validate_render_request(key, style, frame_count, size, supersample)
    drawer = _DRAWERS[(key, style)]
    working_size = size * supersample
    frames: list[Image.Image] = []
    for frame in range(frame_count):
        image = drawer(frame / frame_count, working_size)
        if supersample > 1:
            image = image.resize((size, size), Image.Resampling.LANCZOS)
        frames.append(image.convert("RGB"))
    return frames


def render_catalog_variant_gallery(
    output_dir: str | Path,
    target_frames: int = 60,
    fps: int = 20,
    size: int = 420,
    supersample: int = 2,
) -> tuple[GifAudit, ...]:
    """Write both motif styles for all four symmetries and audit the loops."""

    output = Path(output_dir)
    duration_ms = gif_duration_ms(fps)
    audits: list[GifAudit] = []
    for key in CATALOG_VARIANT_KEYS:
        frame_count = compatible_frame_count(target_frames, PATTERNS[key].phase_divisor)
        for style in VARIANT_STYLES:
            frames = render_catalog_variant_frames(
                key,
                style,
                frame_count=frame_count,
                size=size,
                supersample=supersample,
            )
            path = save_looping_gif(
                frames,
                output / f"{key}__{style}.gif",
                fps=fps,
            )
            audits.append(
                audit_gif(
                    path,
                    expected_frames=frame_count,
                    expected_duration_ms=duration_ms,
                )
            )
    return tuple(audits)


__all__ = [
    "CATALOG_VARIANT_KEYS",
    "VARIANT_STYLES",
    "catalog_variant_state",
    "render_catalog_variant_frames",
    "render_catalog_variant_gallery",
]
