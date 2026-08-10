"""Alternative motifs for the seven original spacetime-symmetry scenes.

The state functions in :mod:`animated_groups.groups` remain the source of
truth.  This module changes only how those states are drawn: ``discs`` uses
ringed rotors with orientation ticks, while ``bars`` uses headed capsules.
Neither style uses a trail, so time-reversing examples remain visually
unbiased.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .groups import EXAMPLES, MotifState
from .rendering import GifAudit, audit_gif, gif_duration_ms, save_looping_gif


BACKGROUND = (10, 18, 31)
BACKGROUND_LIGHT = (19, 32, 49)
PANEL = (23, 39, 59, 150)
GUIDE = (132, 150, 168, 76)
GUIDE_BRIGHT = (177, 192, 207, 116)
INK = (239, 244, 249)
ACCENTS = (
    (42, 205, 180),
    (240, 103, 116),
    (238, 190, 79),
    (153, 111, 222),
    (68, 155, 219),
    (232, 132, 64),
)

VARIANT_STYLES = ("discs", "bars")


@dataclass(frozen=True)
class LegacyExample:
    """Rendering metadata for one established mathematical state model."""

    key: str
    title: str
    divisor: int
    topology: str
    state_function: Callable[[float], tuple[MotifState, ...]]


_LEGACY_KEYS = (
    "time_glide",
    "time_screw",
    "diagonal_relay",
    "mixed_time_glide",
    "glide_time_reversal",
    "rotary_time_reversal",
    "dihedral_choreography",
)

_TOPOLOGIES = {
    "time_glide": "plane",
    "time_screw": "plane",
    "diagonal_relay": "torus_x",
    "mixed_time_glide": "torus_xy",
    "glide_time_reversal": "torus_x",
    "rotary_time_reversal": "plane",
    "dihedral_choreography": "plane",
}

# A read-only, insertion-ordered registry keeps the public gallery order stable.
LEGACY_EXAMPLES: Mapping[str, LegacyExample] = MappingProxyType(
    {
        key: LegacyExample(
            key=key,
            title=EXAMPLES[key].title,
            divisor=EXAMPLES[key].sampling_order,
            topology=_TOPOLOGIES[key],
            state_function=EXAMPLES[key].state_function,
        )
        for key in _LEGACY_KEYS
    }
)


def _lerp(first: int, second: int, amount: float) -> int:
    return round(first + (second - first) * amount)


def _vertical_background(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), BACKGROUND + (255,))
    draw = ImageDraw.Draw(image)
    for y in range(size):
        amount = y / max(1, size - 1)
        color = tuple(_lerp(a, b, amount) for a, b in zip(BACKGROUND, BACKGROUND_LIGHT))
        draw.line((0, y, size - 1, y), fill=color + (255,))
    return image


def _radial_background(size: int) -> Image.Image:
    gradient = Image.radial_gradient("L").resize((size, size), Image.Resampling.BICUBIC)
    return ImageOps.colorize(gradient, black=BACKGROUND, white=BACKGROUND_LIGHT).convert("RGBA")


def _line_width(size: int, fraction: float = 0.004) -> int:
    return max(1, round(size * fraction))


def _draw_radial_guides(image: Image.Image, order: int, *, axes: bool = False) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    size = image.width
    center = (size - 1) / 2.0
    width = _line_width(size)
    for radius in (0.19 * size, 0.30 * size):
        draw.ellipse(
            (center - radius, center - radius, center + radius, center + radius),
            outline=GUIDE_BRIGHT if radius > 0.2 * size else GUIDE,
            width=width,
        )
    ray_count = order if not axes else order * 2
    ray_length = 0.39 * size
    for j in range(ray_count):
        angle = 2.0 * math.pi * j / ray_count
        if axes:
            start = (center, center)
        else:
            start = (
                center + 0.10 * size * math.cos(angle),
                center + 0.10 * size * math.sin(angle),
            )
        end = (
            center + ray_length * math.cos(angle),
            center + ray_length * math.sin(angle),
        )
        draw.line((*start, *end), fill=GUIDE, width=width)


def _draw_repeating_cells(image: Image.Image, order: int) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    size = image.width
    width = _line_width(size)
    cell = size / order
    for j in range(order):
        left = j * cell
        right = (j + 1) * cell
        inset = 0.018 * size
        draw.rounded_rectangle(
            (left + inset, 0.25 * size, right - inset, 0.75 * size),
            radius=round(0.025 * size),
            fill=PANEL,
            outline=GUIDE,
            width=width,
        )
    for y in (0.18 * size, 0.82 * size):
        draw.line((0, y, size - 1, y), fill=GUIDE, width=width)


def _draw_base_guides(image: Image.Image, example: str) -> None:
    size = image.width
    draw = ImageDraw.Draw(image, "RGBA")
    width = _line_width(size)
    center = (size - 1) / 2.0

    if example == "time_glide":
        draw.line((center, 0.13 * size, center, 0.87 * size), fill=GUIDE_BRIGHT, width=width)
        for x in (0.285 * size, 0.715 * size):
            radius = 0.105 * size
            draw.ellipse(
                (x - radius, center - radius, x + radius, center + radius),
                outline=GUIDE,
                width=width,
            )
    elif example == "time_screw":
        _draw_radial_guides(image, 4)
    elif example == "diagonal_relay":
        _draw_repeating_cells(image, 3)
    elif example == "mixed_time_glide":
        cell = size / 2.0
        for row in range(2):
            for column in range(2):
                inset = 0.02 * size
                draw.rounded_rectangle(
                    (
                        column * cell + inset,
                        row * cell + inset,
                        (column + 1) * cell - inset,
                        (row + 1) * cell - inset,
                    ),
                    radius=round(0.025 * size),
                    fill=PANEL,
                    outline=GUIDE,
                    width=width,
                )
        draw.line((center, 0, center, size - 1), fill=GUIDE_BRIGHT, width=width)
        # The middle horizontal boundary and the top/bottom torus seam are one
        # orbit under the half-cell y translation.
        for y in (0, center, size - 1):
            draw.line((0, y, size - 1, y), fill=GUIDE, width=width)
    elif example == "glide_time_reversal":
        _draw_repeating_cells(image, 2)
    elif example == "rotary_time_reversal":
        _draw_radial_guides(image, 4)
    elif example == "dihedral_choreography":
        _draw_radial_guides(image, 3, axes=True)
    else:  # Guard the private helper as well as the public entry point.
        raise ValueError(f"unknown legacy example {example!r}")


@lru_cache(maxsize=32)
def _base_scene(example: str, size: int) -> Image.Image:
    metadata = LEGACY_EXAMPLES[example]
    if metadata.topology.startswith("torus"):
        image = Image.new("RGBA", (size, size), BACKGROUND + (255,))
    elif example in {"time_screw", "rotary_time_reversal", "dihedral_choreography"}:
        image = _radial_background(size)
    else:
        image = _vertical_background(size)
    _draw_base_guides(image, example)
    return image


def _map_center(state: MotifState, size: int, topology: str) -> tuple[float, float]:
    if topology == "plane":
        extent = size - 1
        return (0.5 * (state.x + 1.0) * extent, 0.5 * (state.y + 1.0) * extent)
    if topology == "torus_x":
        return (0.5 * (state.x + 1.0) * size % size, 0.5 * (state.y + 1.0) * (size - 1))
    if topology == "torus_xy":
        return (0.5 * (state.x + 1.0) * size % size, 0.5 * (state.y + 1.0) * size % size)
    raise ValueError(f"unknown topology {topology!r}")


def _periodic_centers(
    center: tuple[float, float],
    size: int,
    topology: str,
    radius: float,
) -> tuple[tuple[float, float], ...]:
    x_offsets = (-size, 0, size) if topology in {"torus_x", "torus_xy"} else (0,)
    y_offsets = (-size, 0, size) if topology == "torus_xy" else (0,)
    centers = []
    for x_offset in x_offsets:
        for y_offset in y_offsets:
            shifted = (center[0] + x_offset, center[1] + y_offset)
            if (
                -radius <= shifted[0] <= size - 1 + radius
                and -radius <= shifted[1] <= size - 1 + radius
            ):
                centers.append(shifted)
    return tuple(centers)


def _point_along(
    center: tuple[float, float],
    distance: float,
    angle: float,
) -> tuple[float, float]:
    return (
        center[0] + distance * math.cos(angle),
        center[1] + distance * math.sin(angle),
    )


def _draw_glow_shape(
    draw: ImageDraw.ImageDraw,
    state: MotifState,
    center: tuple[float, float],
    radius: float,
) -> None:
    color = ACCENTS[state.color % len(ACCENTS)]
    glow_radius = radius * (1.28 + 0.16 * state.glow)
    draw.ellipse(
        (
            center[0] - glow_radius,
            center[1] - glow_radius,
            center[0] + glow_radius,
            center[1] + glow_radius,
        ),
        fill=color + (round(28 + 28 * state.glow),),
    )
def _draw_disc(image: Image.Image, state: MotifState, center: tuple[float, float], radius: float) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    color = ACCENTS[state.color % len(ACCENTS)]
    outline_width = _line_width(image.width, 0.006)
    inner_width = _line_width(image.width, 0.014)

    draw.ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=(13, 25, 40, 255),
        outline=INK + (255,),
        width=outline_width,
    )
    ring_radius = 0.68 * radius
    draw.ellipse(
        (
            center[0] - ring_radius,
            center[1] - ring_radius,
            center[0] + ring_radius,
            center[1] + ring_radius,
        ),
        outline=color + (255,),
        width=inner_width,
    )
    tick_start = _point_along(center, 0.20 * radius, state.angle)
    tick_end = _point_along(center, 0.84 * radius, state.angle)
    draw.line((*tick_start, *tick_end), fill=INK + (255,), width=outline_width * 2)
    tip_radius = 0.12 * radius
    draw.ellipse(
        (
            tick_end[0] - tip_radius,
            tick_end[1] - tip_radius,
            tick_end[0] + tip_radius,
            tick_end[1] + tip_radius,
        ),
        fill=color + (255,),
    )
    hub = 0.17 * radius
    draw.ellipse(
        (center[0] - hub, center[1] - hub, center[0] + hub, center[1] + hub),
        fill=INK + (255,),
    )


def _capsule_polygon(
    center: tuple[float, float],
    angle: float,
    half_length: float,
    half_width: float,
) -> tuple[tuple[float, float], ...]:
    tangent = (math.cos(angle), math.sin(angle))
    normal = (-tangent[1], tangent[0])
    return tuple(
        (
            center[0] + along * tangent[0] + across * normal[0],
            center[1] + along * tangent[1] + across * normal[1],
        )
        for along, across in (
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width),
        )
    )


def _draw_bar(image: Image.Image, state: MotifState, center: tuple[float, float], radius: float) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    color = ACCENTS[state.color % len(ACCENTS)]
    half_length = 1.18 * radius
    half_width = 0.34 * radius
    outline = _line_width(image.width, 0.007)
    head = _point_along(center, half_length, state.angle)
    tail = _point_along(center, -half_length, state.angle)

    polygon = _capsule_polygon(center, state.angle, half_length, half_width)
    draw.polygon(polygon, fill=color + (255,), outline=INK + (255,), width=outline)
    for endpoint in (head, tail):
        draw.ellipse(
            (
                endpoint[0] - half_width,
                endpoint[1] - half_width,
                endpoint[0] + half_width,
                endpoint[1] + half_width,
            ),
            fill=color + (255,),
            outline=INK + (255,),
            width=outline,
        )

    # A bright head and dark tail make the bar directed without introducing a
    # temporal arrow.  Both decorations transform with the instantaneous pose.
    cap_radius = 0.19 * radius
    draw.ellipse(
        (
            head[0] - cap_radius,
            head[1] - cap_radius,
            head[0] + cap_radius,
            head[1] + cap_radius,
        ),
        fill=INK + (255,),
    )
    draw.ellipse(
        (
            tail[0] - cap_radius,
            tail[1] - cap_radius,
            tail[0] + cap_radius,
            tail[1] + cap_radius,
        ),
        fill=(12, 23, 37, 255),
    )


def _render_frame(
    example: str,
    style: str,
    phase: float,
    *,
    size: int,
    supersample: int,
) -> Image.Image:
    metadata = LEGACY_EXAMPLES[example]
    render_size = size * supersample
    image = _base_scene(example, render_size).copy()
    states = metadata.state_function(phase)
    base_radius = render_size * (0.061 if style == "bars" else 0.068)

    positioned: list[tuple[MotifState, float, tuple[tuple[float, float], ...]]] = []
    for state in states:
        radius = base_radius * state.scale
        center = _map_center(state, render_size, metadata.topology)
        copies = _periodic_centers(center, render_size, metadata.topology, 1.8 * radius)
        positioned.append((state, radius, copies))

    # Blur one shared glow layer per frame.  This is equivalent to compositing
    # the individual additive-looking halos and keeps a full gallery render
    # comfortably fast at the default 2x supersampling resolution.
    glow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    for state, radius, copies in positioned:
        for copy in copies:
            _draw_glow_shape(glow_draw, state, copy, radius)
    glow_layer = glow_layer.filter(
        ImageFilter.GaussianBlur(max(2, round(render_size * 0.014)))
    )
    image.alpha_composite(glow_layer)

    for state, radius, copies in positioned:
        for copy in copies:
            if style == "discs":
                _draw_disc(image, state, copy, radius)
            else:
                _draw_bar(image, state, copy, radius)

    if supersample > 1:
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image.convert("RGB")


def _validate_request(example: str, style: str, frame_count: int, size: int, supersample: int) -> None:
    if example not in LEGACY_EXAMPLES:
        choices = ", ".join(LEGACY_EXAMPLES)
        raise ValueError(f"unknown legacy example {example!r}; choose from {choices}")
    if style not in VARIANT_STYLES:
        choices = ", ".join(VARIANT_STYLES)
        raise ValueError(f"unknown motif style {style!r}; choose from {choices}")
    divisor = LEGACY_EXAMPLES[example].divisor
    if frame_count < 2 * divisor:
        raise ValueError(f"frame count must be at least twice the sampling divisor ({2 * divisor})")
    if frame_count % divisor:
        raise ValueError(f"frame count {frame_count} must be divisible by sampling divisor {divisor}")
    if size < 96:
        raise ValueError("size must be at least 96 pixels")
    if supersample < 1:
        raise ValueError("supersample must be at least 1")


def render_legacy_variant_frames(
    example: str,
    style: str,
    frame_count: int = 60,
    size: int = 420,
    supersample: int = 2,
) -> list[Image.Image]:
    """Render one exact-period legacy example, omitting the duplicate endpoint."""

    _validate_request(example, style, frame_count, size, supersample)
    return [
        _render_frame(
            example,
            style,
            frame / frame_count,
            size=size,
            supersample=supersample,
        )
        for frame in range(frame_count)
    ]


def _frame_count_for_target(target_frames: int, divisor: int) -> int:
    minimum = max(target_frames, 2 * divisor)
    return ((minimum + divisor - 1) // divisor) * divisor


def render_legacy_variant_gallery(
    output_dir: str | Path,
    target_frames: int = 60,
    fps: int = 20,
    size: int = 420,
    supersample: int = 2,
) -> tuple[GifAudit, ...]:
    """Write all fourteen legacy/style combinations and return their audits."""

    if target_frames < 1:
        raise ValueError("target_frames must be positive")
    # Validate timing before the comparatively expensive frame rendering.
    duration = gif_duration_ms(fps)
    destination = Path(output_dir)
    audits: list[GifAudit] = []
    for example, metadata in LEGACY_EXAMPLES.items():
        frame_count = _frame_count_for_target(target_frames, metadata.divisor)
        for style in VARIANT_STYLES:
            frames = render_legacy_variant_frames(
                example,
                style,
                frame_count=frame_count,
                size=size,
                supersample=supersample,
            )
            path = destination / f"{example}__{style}.gif"
            save_looping_gif(frames, path, fps=fps)
            audits.append(
                audit_gif(
                    path,
                    expected_frames=frame_count,
                    expected_duration_ms=duration,
                )
            )
    return tuple(audits)


__all__ = (
    "LEGACY_EXAMPLES",
    "LegacyExample",
    "VARIANT_STYLES",
    "render_legacy_variant_frames",
    "render_legacy_variant_gallery",
)
