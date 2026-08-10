"""Procedural art recipes for the systematic spacetime-group catalog.

The legacy examples deliberately use one repeated asymmetric glyph.  This
module instead supplies four independent scene grammars.  Each recipe is
defined from analytic, periodic state first and rasterized second, which keeps
the group identities testable without relying on anti-aliased pixel equality.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Callable, Mapping, Sequence, TypeVar

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


TAU = 2.0 * math.pi


@dataclass(frozen=True)
class PatternSpec:
    """Public metadata for one fixed catalog illustration recipe."""

    key: str
    filename: str
    title: str
    catalog_selector: dict[str, object]
    phase_divisor: int


PATTERNS: dict[str, PatternSpec] = {
    "iris_c6_time_screw": PatternSpec(
        key="iris_c6_time_screw",
        filename="iris_c6_time_screw.gif",
        title="C6 kinetic-iris time screw",
        catalog_selector={
            "family": "cyclic",
            "order": 6,
            "spatial_action": "rotation",
            "temporal_action": "phase_translation",
        },
        phase_divisor=6,
    ),
    "wave_loom_c5_relay": PatternSpec(
        key="wave_loom_c5_relay",
        filename="wave_loom_c5_relay.gif",
        title="C5 torus wave-loom relay",
        catalog_selector={
            "family": "cyclic",
            "order": 5,
            "spatial_action": "translation",
            "temporal_action": "phase_translation",
        },
        phase_divisor=5,
    ),
    "elastic_d4_choreography": PatternSpec(
        key="elastic_d4_choreography",
        filename="elastic_d4_choreography.gif",
        title="D4 elastic-square choreography",
        catalog_selector={
            "family": "dihedral",
            "order": 4,
            "spatial_action": "rotation_and_reflection",
            "temporal_action": "phase_translation_and_reversal",
        },
        phase_divisor=4,
    ),
    "liquid_c2_centered_lattice": PatternSpec(
        key="liquid_c2_centered_lattice",
        filename="liquid_c2_centered_lattice.gif",
        title="C2 centered-lattice liquid cells",
        catalog_selector={
            "family": "cyclic",
            "order": 2,
            "spatial_action": "centered_translation",
            "temporal_action": "phase_translation",
        },
        phase_divisor=2,
    ),
}


def _phase(value: float) -> float:
    """Canonicalize a phase so phases zero and one share analytic data."""

    return round(value % 1.0, 12)


@dataclass(frozen=True)
class IrisPetalState:
    slot: int
    phase: float
    radius: float
    tangent_skew: float
    half_width: float
    tone: float


@dataclass(frozen=True)
class WaveSegmentState:
    slot: int
    phase: float
    first_control_y: float
    second_control_y: float
    shuttle: float


@dataclass(frozen=True)
class ElasticEdgeState:
    slot: int
    phase: float
    normal_bulge: float
    tangent_skew: float
    tone: float


@dataclass(frozen=True)
class LiquidCellState:
    row: int
    column: int
    orbit: int
    phase: float
    fill: float
    tilt: float
    bubble_x: float
    bubble_depth: float


def iris_c6_state(phase: float) -> tuple[IrisPetalState, ...]:
    """Six petals satisfying rotation + one-sixth-period translation."""

    petals: list[IrisPetalState] = []
    for slot in range(6):
        local = _phase(phase - slot / 6.0)
        angle = TAU * local
        # Radius and width are even under local phase reversal.  Tangential
        # skew is odd, so a mirror can be coupled to playback reversal too.
        radius = 0.55 + 0.105 * math.cos(angle) + 0.018 * math.cos(2.0 * angle)
        tangent_skew = 0.060 * math.sin(angle) + 0.014 * math.sin(2.0 * angle)
        half_width = 0.105 + 0.022 * math.cos(angle)
        tone = 0.5 + 0.5 * math.cos(angle)
        petals.append(
            IrisPetalState(slot, local, radius, tangent_skew, half_width, tone)
        )
    return tuple(petals)


def wave_loom_c5_state(phase: float) -> tuple[WaveSegmentState, ...]:
    """Five connected torus segments with a discrete phase relay."""

    segments: list[WaveSegmentState] = []
    for slot in range(5):
        local = _phase(phase - slot / 5.0)
        angle = TAU * local
        # Generic harmonics deliberately avoid a continuous traveling-wave
        # symmetry; only the one-cell/one-fifth-period relay is imposed.
        first = 0.25 * math.sin(angle) + 0.055 * math.sin(2.0 * angle + 0.37)
        second = -0.22 * math.cos(angle - 0.21) + 0.045 * math.sin(3.0 * angle)
        shuttle = 0.5 + 0.23 * math.sin(angle + 0.58)
        segments.append(WaveSegmentState(slot, local, first, second, shuttle))
    return tuple(segments)


def elastic_d4_state(phase: float) -> tuple[ElasticEdgeState, ...]:
    """Four square edges carrying a D4-compatible phase choreography."""

    edges: list[ElasticEdgeState] = []
    for slot in range(4):
        local = _phase(phase - slot / 4.0)
        angle = TAU * local
        # The normal displacement is even and tangential displacement odd.
        # Reflection maps edge j to -j and therefore implements t -> -t.
        normal = 0.060 + 0.050 * math.cos(angle) + 0.012 * math.cos(2.0 * angle)
        tangent = 0.078 * math.sin(angle) + 0.018 * math.sin(2.0 * angle)
        tone = 0.5 + 0.5 * math.cos(angle)
        edges.append(ElasticEdgeState(slot, local, normal, tangent, tone))
    return tuple(edges)


def liquid_c2_state(phase: float) -> tuple[LiquidCellState, ...]:
    """A 2x2 torus whose diagonal half-shift is tied to half a period.

    Translating both row and column by one preserves ``orbit=column-row`` but
    flips row parity.  The row-parity phase offset is consequently the desired
    nonsymmorphic centered-lattice phase.
    """

    cells: list[LiquidCellState] = []
    for row in range(2):
        for column in range(2):
            orbit = (column - row) % 2
            local = _phase(phase - row / 2.0)
            angle = TAU * local
            style_shift = 0.31 * orbit
            fill = 0.52 + 0.205 * math.sin(angle) + 0.050 * math.sin(
                2.0 * angle + style_shift
            )
            tilt = 0.075 * math.cos(angle + 0.18 * orbit) + 0.018 * math.sin(
                2.0 * angle
            )
            bubble_x = 0.5 + 0.19 * math.cos(angle + 0.7 * orbit)
            bubble_depth = 0.50 + 0.12 * math.sin(angle - 0.4 * orbit)
            cells.append(
                LiquidCellState(
                    row,
                    column,
                    orbit,
                    local,
                    fill,
                    tilt,
                    bubble_x,
                    bubble_depth,
                )
            )
    return tuple(cells)


_SlotState = TypeVar("_SlotState", IrisPetalState, WaveSegmentState, ElasticEdgeState)


def advance_slots(states: Sequence[_SlotState], order: int) -> tuple[_SlotState, ...]:
    """Apply the spatial generator to cyclic slot-indexed analytic states."""

    advanced = [replace(state, slot=(state.slot + 1) % order) for state in states]
    return tuple(sorted(advanced, key=lambda state: state.slot))


def reflect_elastic_d4(
    states: Sequence[ElasticEdgeState],
) -> tuple[ElasticEdgeState, ...]:
    """Reflect y -> -y: edge j -> -j and local tangent -> -tangent."""

    reflected = [
        replace(
            state,
            slot=(-state.slot) % 4,
            phase=_phase(-state.phase),
            tangent_skew=-state.tangent_skew,
        )
        for state in states
    ]
    return tuple(sorted(reflected, key=lambda state: state.slot))


def centered_liquid_step(
    states: Sequence[LiquidCellState],
) -> tuple[LiquidCellState, ...]:
    """Translate the liquid torus by half a cell in x and y."""

    moved = [
        replace(state, row=(state.row + 1) % 2, column=(state.column + 1) % 2)
        for state in states
    ]
    return tuple(sorted(moved, key=lambda state: (state.row, state.column)))


def _mix(first: tuple[int, int, int], second: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))


def _radial_background(size: int, inner: str, outer: str) -> Image.Image:
    mask = Image.radial_gradient("L").resize((size, size), Image.Resampling.BICUBIC)
    return ImageOps.colorize(mask, black=inner, white=outer).convert("RGBA")


def _vertical_background(
    size: int,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    image = Image.new("RGBA", (size, size), top + (255,))
    draw = ImageDraw.Draw(image)
    for y in range(size):
        amount = y / max(1, size - 1)
        draw.line((0, y, size - 1, y), fill=_mix(top, bottom, amount) + (255,))
    return image


def _map_centered(point: tuple[float, float], size: int) -> tuple[float, float]:
    extent = size - 1
    return ((point[0] + 1.0) * 0.5 * extent, (point[1] + 1.0) * 0.5 * extent)


def _polar_point(radial: float, tangent: float, angle: float) -> tuple[float, float]:
    normal = (math.cos(angle), math.sin(angle))
    side = (-normal[1], normal[0])
    return (
        radial * normal[0] + tangent * side[0],
        radial * normal[1] + tangent * side[1],
    )


def _quadratic(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    steps: int = 40,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(steps + 1):
        amount = index / steps
        back = 1.0 - amount
        points.append(
            (
                back * back * start[0]
                + 2.0 * back * amount * control[0]
                + amount * amount * end[0],
                back * back * start[1]
                + 2.0 * back * amount * control[1]
                + amount * amount * end[1],
            )
        )
    return points


def _cubic(
    start: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
    end: tuple[float, float],
    steps: int = 36,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(steps + 1):
        amount = index / steps
        back = 1.0 - amount
        points.append(
            (
                back**3 * start[0]
                + 3.0 * back * back * amount * first[0]
                + 3.0 * back * amount * amount * second[0]
                + amount**3 * end[0],
                back**3 * start[1]
                + 3.0 * back * back * amount * first[1]
                + 3.0 * back * amount * amount * second[1]
                + amount**3 * end[1],
            )
        )
    return points


def _draw_iris(phase: float, size: int) -> Image.Image:
    image = _radial_background(size, "#17204a", "#070b21")
    draw = ImageDraw.Draw(image, "RGBA")
    center = (size - 1) / 2.0
    guide = (157, 178, 235, 45)
    guide_width = max(1, round(size * 0.003))
    for radius in (0.18, 0.36, 0.62):
        pixels = radius * size / 2.0
        draw.ellipse(
            (center - pixels, center - pixels, center + pixels, center + pixels),
            outline=guide,
            width=guide_width,
        )
    for slot in range(6):
        angle = TAU * slot / 6.0
        inner = _map_centered(_polar_point(0.12, 0.0, angle), size)
        outer = _map_centered(_polar_point(0.72, 0.0, angle), size)
        draw.line((*inner, *outer), fill=guide, width=guide_width)

    states = iris_c6_state(phase)
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow, "RGBA")
    polygons: list[tuple[IrisPetalState, list[tuple[float, float]]]] = []
    for state in states:
        angle = TAU * state.slot / 6.0
        local = (
            (0.115, -0.045),
            (0.285, -state.half_width),
            (state.radius, state.tangent_skew),
            (0.285, state.half_width),
            (0.115, 0.045),
        )
        points = [_map_centered(_polar_point(r, tangent, angle), size) for r, tangent in local]
        polygons.append((state, points))
        shadow_draw.polygon(points, fill=(68, 214, 255, 88))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, round(size * 0.022))))
    image.alpha_composite(shadow)

    draw = ImageDraw.Draw(image, "RGBA")
    outline_width = max(2, round(size * 0.006))
    for state, points in polygons:
        color = _mix((91, 226, 209), (242, 113, 255), state.tone)
        draw.polygon(points, fill=color + (245,), outline=(244, 248, 255, 225), width=outline_width)
        angle = TAU * state.slot / 6.0
        tip = _map_centered(_polar_point(state.radius, state.tangent_skew, angle), size)
        bead = size * (0.010 + 0.004 * state.tone)
        draw.ellipse(
            (tip[0] - bead, tip[1] - bead, tip[0] + bead, tip[1] + bead),
            fill=(249, 252, 255, 255),
        )
    hub = size * 0.073
    draw.ellipse(
        (center - hub, center - hub, center + hub, center + hub),
        fill=(17, 28, 68, 255),
        outline=(223, 235, 255, 220),
        width=outline_width,
    )
    draw.ellipse(
        (center - hub * 0.32, center - hub * 0.32, center + hub * 0.32, center + hub * 0.32),
        fill=(255, 205, 91, 255),
    )
    return image


def _draw_periodic_polyline(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    size: int,
    *,
    fill: tuple[int, int, int, int],
    width: int,
) -> None:
    for offset in (-size, 0, size):
        draw.line(
            [(x + offset, y) for x, y in points],
            fill=fill,
            width=width,
            joint="curve",
        )


def _draw_wave_loom(phase: float, size: int) -> Image.Image:
    image = _vertical_background(size, (7, 30, 43), (13, 54, 63))
    draw = ImageDraw.Draw(image, "RGBA")
    cell = size / 5.0
    guide_width = max(1, round(size * 0.003))
    for slot in range(5):
        left = slot * cell
        draw.rounded_rectangle(
            (left + size * 0.010, size * 0.16, left + cell - size * 0.010, size * 0.84),
            radius=round(size * 0.018),
            outline=(154, 219, 211, 48),
            width=guide_width,
        )
    for y in (0.39, 0.50, 0.61):
        py = y * (size - 1)
        draw.line((0, py, size - 1, py), fill=(188, 232, 224, 42), width=guide_width)

    primary_curves: list[tuple[WaveSegmentState, list[tuple[float, float]]]] = []
    secondary_curves: list[tuple[WaveSegmentState, list[tuple[float, float]]]] = []
    for state in wave_loom_c5_state(phase):
        left = state.slot / 5.0
        right = (state.slot + 1) / 5.0
        primary = _cubic(
            (left, -0.22),
            (left + 0.31 / 5.0, -0.22 + 0.62 * state.first_control_y),
            (right - 0.31 / 5.0, -0.22 + 0.62 * state.second_control_y),
            (right, -0.22),
        )
        secondary = _cubic(
            (left, 0.22),
            (left + 0.31 / 5.0, 0.22 - 0.58 * state.second_control_y),
            (right - 0.31 / 5.0, 0.22 - 0.58 * state.first_control_y),
            (right, 0.22),
        )
        map_curve = lambda curve: [
            (x * size, 0.5 * (y + 1.0) * (size - 1)) for x, y in curve
        ]
        primary_curves.append((state, map_curve(primary)))
        secondary_curves.append((state, map_curve(secondary)))

    under_width = max(5, round(size * 0.038))
    ribbon_width = max(3, round(size * 0.021))
    for _, points in primary_curves + secondary_curves:
        _draw_periodic_polyline(
            draw,
            points,
            size,
            fill=(1, 17, 25, 210),
            width=under_width,
        )
    for _, points in primary_curves:
        _draw_periodic_polyline(
            draw,
            points,
            size,
            fill=(63, 225, 207, 255),
            width=ribbon_width,
        )
    for _, points in secondary_curves:
        _draw_periodic_polyline(
            draw,
            points,
            size,
            fill=(255, 188, 78, 255),
            width=ribbon_width,
        )

    # Neutral eyelets conceal joins and make the five-cell translation clear.
    node_radius = size * 0.012
    for slot in range(5):
        for y in (-0.22, 0.22):
            x = slot * cell
            py = 0.5 * (y + 1.0) * (size - 1)
            for wrap_x in (x, x + size if slot == 0 else x):
                draw.ellipse(
                    (
                        wrap_x - node_radius,
                        py - node_radius,
                        wrap_x + node_radius,
                        py + node_radius,
                    ),
                    fill=(231, 245, 239, 255),
                    outline=(4, 30, 37, 255),
                    width=max(1, round(size * 0.004)),
                )
    return image


def _draw_elastic_square(phase: float, size: int) -> Image.Image:
    image = _radial_background(size, "#351c43", "#0d0a1d")
    draw = ImageDraw.Draw(image, "RGBA")
    guide_width = max(1, round(size * 0.003))
    for radius in (0.27, 0.48, 0.68):
        corners = [
            _map_centered((radius * math.cos(math.pi / 4.0 + j * math.pi / 2.0),
                           radius * math.sin(math.pi / 4.0 + j * math.pi / 2.0)), size)
            for j in range(4)
        ]
        draw.line((*corners, corners[0]), fill=(228, 196, 244, 42), width=guide_width, joint="curve")
    center = (size - 1) / 2.0
    draw.line((0.15 * size, center, 0.85 * size, center), fill=(228, 196, 244, 38), width=guide_width)
    draw.line((center, 0.15 * size, center, 0.85 * size), fill=(228, 196, 244, 38), width=guide_width)

    curves: list[tuple[ElasticEdgeState, list[tuple[float, float]]]] = []
    radius = 0.47
    half_side = 0.47
    for state in elastic_d4_state(phase):
        angle = TAU * state.slot / 4.0
        normal = (math.cos(angle), math.sin(angle))
        tangent = (-normal[1], normal[0])
        side_center = (radius * normal[0], radius * normal[1])
        start = (
            side_center[0] - half_side * tangent[0],
            side_center[1] - half_side * tangent[1],
        )
        end = (
            side_center[0] + half_side * tangent[0],
            side_center[1] + half_side * tangent[1],
        )
        control = (
            side_center[0]
            + state.normal_bulge * normal[0]
            + state.tangent_skew * tangent[0],
            side_center[1]
            + state.normal_bulge * normal[1]
            + state.tangent_skew * tangent[1],
        )
        curves.append((state, [_map_centered(point, size) for point in _quadratic(start, control, end)]))

    under_width = max(7, round(size * 0.052))
    edge_width = max(4, round(size * 0.029))
    for _, points in curves:
        draw.line(points, fill=(7, 5, 18, 230), width=under_width, joint="curve")
    for state, points in curves:
        color = _mix((80, 205, 255), (255, 107, 128), state.tone)
        draw.line(points, fill=color + (255,), width=edge_width, joint="curve")
        highlight = max(1, round(size * 0.004))
        draw.line(points, fill=(250, 241, 255, 105), width=highlight, joint="curve")

    node_radius = size * 0.034
    for x, y in ((radius, half_side), (-radius, half_side), (-radius, -half_side), (radius, -half_side)):
        px, py = _map_centered((x, y), size)
        draw.ellipse(
            (px - node_radius, py - node_radius, px + node_radius, py + node_radius),
            fill=(37, 22, 54, 255),
            outline=(245, 230, 255, 235),
            width=max(2, round(size * 0.006)),
        )
        inner = node_radius * 0.35
        draw.ellipse((px - inner, py - inner, px + inner, py + inner), fill=(255, 205, 91, 255))
    return image


def _draw_liquid_cells(phase: float, size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (238, 229, 205, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    cell = size / 2.0
    guide_width = max(1, round(size * 0.004))
    # On the torus both the zero boundary and the half-cell boundary belong to
    # the repeated guide.  A diagonal half-translation swaps the two lines.
    for coordinate in (0, cell):
        draw.line(
            (coordinate, 0, coordinate, size - 1),
            fill=(69, 68, 80, 55),
            width=guide_width,
        )
        draw.line(
            (0, coordinate, size - 1, coordinate),
            fill=(69, 68, 80, 55),
            width=guide_width,
        )
    palettes = ((29, 150, 154), (218, 91, 105))

    for state in liquid_c2_state(phase):
        left = state.column * cell + size * 0.035
        right = (state.column + 1) * cell - size * 0.035
        top = state.row * cell + size * 0.035
        bottom = (state.row + 1) * cell - size * 0.035
        radius = round(size * 0.040)

        shadow_box = (left + size * 0.010, top + size * 0.012, right + size * 0.010, bottom + size * 0.012)
        draw.rounded_rectangle(shadow_box, radius=radius, fill=(71, 60, 70, 40))
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=radius,
            fill=(251, 247, 234, 255),
            outline=(64, 60, 69, 185),
            width=guide_width,
        )

        inset = size * 0.015
        inner_box = (left + inset, top + inset, right - inset, bottom - inset)
        cell_mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(cell_mask).rounded_rectangle(inner_box, radius=max(1, radius - round(inset)), fill=255)
        liquid_mask = Image.new("L", (size, size), 0)
        liquid_draw = ImageDraw.Draw(liquid_mask)
        inner_left, inner_top, inner_right, inner_bottom = inner_box
        inner_width = inner_right - inner_left
        inner_height = inner_bottom - inner_top
        surface: list[tuple[float, float]] = []
        for index in range(25):
            amount = index / 24.0
            x = inner_left + amount * inner_width
            base = inner_bottom - state.fill * inner_height
            slope = state.tilt * inner_height * (amount - 0.5)
            ripple = 0.018 * inner_height * math.sin(TAU * amount + TAU * state.phase)
            surface.append((x, base + slope + ripple))
        liquid_draw.polygon(
            (*surface, (inner_right, inner_bottom), (inner_left, inner_bottom)),
            fill=255,
        )
        liquid_mask = ImageChops.multiply(cell_mask, liquid_mask)
        color = palettes[state.orbit]
        fill_layer = Image.new("RGBA", image.size, color + (242,))
        image.paste(fill_layer, (0, 0), liquid_mask)

        # The surface line is clipped by the same rounded cell mask.
        surface_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        surface_draw = ImageDraw.Draw(surface_layer, "RGBA")
        surface_draw.line(
            surface,
            fill=_mix(color, (255, 255, 255), 0.55) + (245,),
            width=max(2, round(size * 0.008)),
            joint="curve",
        )
        surface_layer.putalpha(ImageChops.multiply(surface_layer.getchannel("A"), cell_mask))
        image.alpha_composite(surface_layer)

        bubble_x = inner_left + state.bubble_x * inner_width
        local_surface = inner_bottom - state.fill * inner_height
        bubble_y = local_surface + state.bubble_depth * max(size * 0.030, inner_bottom - local_surface)
        bubble_radius = size * (0.014 + 0.003 * state.orbit)
        draw = ImageDraw.Draw(image, "RGBA")
        draw.ellipse(
            (
                bubble_x - bubble_radius,
                bubble_y - bubble_radius,
                bubble_x + bubble_radius,
                bubble_y + bubble_radius,
            ),
            fill=(251, 247, 234, 205),
            outline=(255, 255, 255, 210),
            width=max(1, round(size * 0.003)),
        )

        # A fixed orbit-specific paper notch prevents an accidental pure
        # half-cell horizontal or vertical translation.
        notch_x = left + (0.22 if state.orbit == 0 else 0.78) * (right - left)
        notch_y = top + size * 0.028
        notch = size * 0.018
        draw.ellipse(
            (notch_x - notch, notch_y - notch, notch_x + notch, notch_y + notch),
            fill=(238, 229, 205, 255),
            outline=(64, 60, 69, 145),
            width=max(1, round(size * 0.003)),
        )
    return image


_RENDERERS: Mapping[str, Callable[[float, int], Image.Image]] = {
    "iris_c6_time_screw": _draw_iris,
    "wave_loom_c5_relay": _draw_wave_loom,
    "elastic_d4_choreography": _draw_elastic_square,
    "liquid_c2_centered_lattice": _draw_liquid_cells,
}


def render_pattern_image(
    key: str,
    phase: float,
    *,
    size: int = 600,
    supersample: int = 2,
) -> Image.Image:
    """Render one RGB catalog frame from a normalized periodic phase."""

    if key not in PATTERNS:
        choices = ", ".join(PATTERNS)
        raise ValueError(f"unknown catalog pattern {key!r}; choose from {choices}")
    if size < 120:
        raise ValueError("size must be at least 120 pixels")
    if supersample < 1:
        raise ValueError("supersample must be at least 1")
    render_size = size * supersample
    image = _RENDERERS[key](_phase(phase), render_size)
    if supersample > 1:
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image.convert("RGB")


__all__ = [
    "PATTERNS",
    "PatternSpec",
    "IrisPetalState",
    "WaveSegmentState",
    "ElasticEdgeState",
    "LiquidCellState",
    "iris_c6_state",
    "wave_loom_c5_state",
    "elastic_d4_state",
    "liquid_c2_state",
    "advance_slots",
    "reflect_elastic_d4",
    "centered_liquid_step",
    "render_pattern_image",
]
