#!/usr/bin/env python3
"""Generate the cyclic-colouring to polar-space-group atlas.

The input is the checked-in 68-record clockwork/colouring correspondence.
For every planar operation ``(M, v, tau)`` this generator uses the height
lift

    (x, y, z) -> (M (x, y) + v, z + tau).

The resulting ordinary three-dimensional crystallographic groups are the 68
polar space-group types.  ``SPACE_GROUP_BY_ID`` is deliberately explicit:
the International Tables number, Hermann--Mauguin names, Hall symbol, and
setting choice are pinned data rather than a runtime spglib dependency.

This statement has a narrow scope.  The selected forward catalog consists of
regular cyclic colour actions.  General colour groups allow other permutation
actions and equivalences, so coloured wallpaper groups and all 230 space
groups are not in a global one-to-one correspondence.

Usage::

    python3 scripts/generate_space_group_correspondence.py
    python3 scripts/generate_space_group_correspondence.py --check
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from html import escape
import io
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATA = ROOT / "data" / "clockwork-coloring-correspondence.json"
DATA = ROOT / "data" / "space-group-correspondence.json"
PAGE = ROOT / "space-group-correspondence.html"
IMAGE_DIR = ROOT / "output" / "space-groups"

STYLE_SRC = "space-group-correspondence.css?v=nontrivial-atlas"
SCRIPT_SRC = "space-group-correspondence.js?v=polar-atlas"
SOURCE_SHA256 = "242a467001ac496aaf048ad2467886f79e5e6139630789ead537ef76bcae1330"
UCL_SPACE_GROUP_BASE = "http://img.chem.ucl.ac.uk/sgp/large"
UCL_PAGE_BY_NUMBER = {
    1: "001az1.htm",
    3: "003ay1.htm",
    4: "004ay1.htm",
    5: "005ay1.htm",
    6: "006ay1.htm",
    7: "007ay1.htm",
    8: "008ay1.htm",
    9: "009ay1.htm",
    **{number: f"{number:03d}az1.htm" for number in range(25, 47)},
    **{number: f"{number:03d}az1.htm" for number in range(75, 80)},
    80: "080a.htm",
    **{number: f"{number:03d}az1.htm" for number in range(99, 111)},
    **{number: f"{number:03d}az1.htm" for number in range(143, 147)},
    **{number: f"{number:03d}az1.htm" for number in range(156, 162)},
    **{number: f"{number:03d}az1.htm" for number in range(168, 174)},
    **{number: f"{number:03d}az1.htm" for number in range(183, 187)},
}

IMAGE_WIDTH = 720
IMAGE_HEIGHT = 480
ANTIALIAS = 2
DISPLAYED_GROUP_COUNT = 51
OMITTED_TRIVIAL_COUNT = 17
DISPLAYED_FAMILY_COUNT = 14
PALETTE = (
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#CC79A7",
    "#D55E00",
    "#56B4E9",
)

BASE_ORDER = (
    "p1", "p2", "pm", "pg", "cm", "pmm", "pmg", "pgg", "cmm",
    "p4", "p4m", "p4g", "p3", "p3m1", "p31m", "p6", "p6m",
)

ORBIFOLD_BY_BASE = {
    "p1": "◦",
    "p2": "2222",
    "pm": "**",
    "pg": "××",
    "cm": "*×",
    "pmm": "*2222",
    "pmg": "22*",
    "pgg": "22×",
    "cmm": "2*22",
    "p4": "442",
    "p4m": "*442",
    "p4g": "4*2",
    "p3": "333",
    "p3m1": "*333",
    "p31m": "3*3",
    "p6": "632",
    "p6m": "*632",
}

FAMILY_SUMMARIES = {
    "p1": "Translations lift to the triclinic polar type.",
    "p2": "Twofold planar rotations become rotations or screws along the height axis.",
    "pm": "A planar mirror lifts to a vertical mirror plane.",
    "pg": "A planar glide lifts to a vertical glide plane.",
    "cm": "The centred mirror family gives centred monoclinic lifts.",
    "pmm": "Two mirror directions lift through primitive, base-, body-, and face-centred orthorhombic settings.",
    "pmg": "Mirror/glide phase choices fill the polar orthorhombic series.",
    "pgg": "Two glide directions include the four-colour Fdd2 lift.",
    "cmm": "Centred planar mirrors lift to C- and I-centred orthorhombic groups.",
    "p4": "Fourfold colour phase becomes the pitch of a 4-fold screw axis.",
    "p4m": "Vertical mirror and glide planes accompany the tetragonal axis.",
    "p4g": "Glide variants lift to the polar tetragonal 4mm family.",
    "p3": "Threefold phases distinguish P3₁, P3₂, and the rhombohedral lift.",
    "p3m1": "The first trigonal mirror orientation lifts to P3m1 and P3c1.",
    "p31m": "The second mirror orientation also supplies the rhombohedral R3m/R3c pair.",
    "p6": "Sixfold cyclic phases become the complete P6 through P6₅ screw series.",
    "p6m": "Hexagonal mirrors and glides give the four polar 6mm space groups.",
}

# Pinned from spglib 2.6.0's International Tables database after applying the
# height lift to the checked-in operations.  Tuple fields are, in order:
# (IT number, Hermann--Mauguin short, HM full, Hall symbol, choice).
SPACE_GROUP_BY_ID: dict[str, tuple[int, str, str, str, str]] = {
    "g1": (1, "P1", "P 1", "P 1", ""),
    "g5": (3, "P2", "P 1 2 1", "P 2y", "b"),
    "g6": (4, "P2_1", "P 1 2_1 1", "P 2yb", "b"),
    "g7": (5, "C2", "C 1 2 1", "C 2y", "b1"),
    "g8": (8, "Cm", "C 1 m 1", "C -2y", "b1"),
    "g9": (9, "Cc", "C 1 c 1", "C -2yc", "b1"),
    "g10": (6, "Pm", "P 1 m 1", "P -2y", "b"),
    "g11": (7, "Pc", "P 1 c 1", "P -2yc", "b1"),
    "g54": (25, "Pmm2", "P m m 2", "P 2 -2", ""),
    "g55": (27, "Pcc2", "P c c 2", "P 2 -2c", ""),
    "g56": (28, "Pma2", "P m a 2", "P 2 -2a", ""),
    "g57": (30, "Pnc2", "P n c 2", "P 2 -2bc", ""),
    "g58": (32, "Pba2", "P b a 2", "P 2 -2ab", ""),
    "g59": (34, "Pnn2", "P n n 2", "P 2 -2n", ""),
    "g60": (26, "Pmc2_1", "P m c 2_1", "P 2c -2", ""),
    "g61": (29, "Pca2_1", "P c a 2_1", "P 2c -2ac", ""),
    "g62": (31, "Pmn2_1", "P m n 2_1", "P 2ac -2", ""),
    "g63": (33, "Pna2_1", "P n a 2_1", "P 2c -2n", ""),
    "g64": (38, "Amm2", "A m m 2", "A 2 -2", ""),
    "g65": (39, "Aem2", "A e m 2", "A 2 -2b", ""),
    "g66": (40, "Ama2", "A m a 2", "A 2 -2a", ""),
    "g67": (41, "Aea2", "A e a 2", "A 2 -2ab", ""),
    "g68": (35, "Cmm2", "C m m 2", "C 2 -2", ""),
    "g69": (37, "Ccc2", "C c c 2", "C 2 -2c", ""),
    "g70": (36, "Cmc2_1", "C m c 2_1", "C 2c -2", ""),
    "g71": (44, "Imm2", "I m m 2", "I 2 -2", ""),
    "g72": (45, "Iba2", "I b a 2", "I 2 -2c", ""),
    "g73": (46, "Ima2", "I m a 2", "I 2 -2a", ""),
    "g74": (42, "Fmm2", "F m m 2", "F 2 -2", ""),
    "g75": (43, "Fdd2", "F d d 2", "F 2 -2d", ""),
    "g94": (75, "P4", "P 4", "P 4", ""),
    "g95": (77, "P4_2", "P 4_2", "P 4c", ""),
    "g96": (76, "P4_1", "P 4_1", "P 4w", ""),
    "g97": (78, "P4_3", "P 4_3", "P 4cw", ""),
    "g98": (79, "I4", "I 4", "I 4", ""),
    "g99": (80, "I4_1", "I 4_1", "I 4bw", ""),
    "g128": (99, "P4mm", "P 4 m m", "P 4 -2", ""),
    "g129": (105, "P4_2mc", "P 4_2 m c", "P 4c -2", ""),
    "g130": (101, "P4_2cm", "P 4_2 c m", "P 4c -2c", ""),
    "g131": (103, "P4cc", "P 4 c c", "P 4 -2c", ""),
    "g132": (100, "P4bm", "P 4 b m", "P 4 -2ab", ""),
    "g133": (106, "P4_2bc", "P 4_2 b c", "P 4c -2ab", ""),
    "g134": (102, "P4_2nm", "P 4_2 n m", "P 4n -2n", ""),
    "g135": (104, "P4nc", "P 4 n c", "P 4 -2n", ""),
    "g136": (107, "I4mm", "I 4 m m", "I 4 -2", ""),
    "g137": (109, "I4_1md", "I 4_1 m d", "I 4bw -2", ""),
    "g138": (108, "I4cm", "I 4 c m", "I 4 -2c", ""),
    "g139": (110, "I4_1cd", "I 4_1 c d", "I 4bw -2c", ""),
    "g224": (143, "P3", "P 3", "P 3", ""),
    "g225": (145, "P3_2", "P 3_2", "P 32", ""),
    "g226": (144, "P3_1", "P 3_1", "P 31", ""),
    "g227": (146, "R3", "R 3", "R 3", "H"),
    "g230": (156, "P3m1", "P 3 m 1", "P 3 -2\"", ""),
    "g231": (158, "P3c1", "P 3 c 1", "P 3 -2\"c", ""),
    "g232": (157, "P31m", "P 3 1 m", "P 3 -2", ""),
    "g233": (159, "P31c", "P 3 1 c", "P 3 -2c", ""),
    "g234": (160, "R3m", "R 3 m", "R 3 -2\"", "H"),
    "g235": (161, "R3c", "R 3 c", "R 3 -2\"c", "H"),
    "g243": (168, "P6", "P 6", "P 6", ""),
    "g244": (171, "P6_2", "P 6_2", "P 62", ""),
    "g245": (172, "P6_4", "P 6_4", "P 64", ""),
    "g246": (173, "P6_3", "P 6_3", "P 6c", ""),
    "g247": (170, "P6_5", "P 6_5", "P 65", ""),
    "g248": (169, "P6_1", "P 6_1", "P 61", ""),
    "g268": (183, "P6mm", "P 6 m m", "P 6 -2", ""),
    "g269": (185, "P6_3cm", "P 6_3 c m", "P 6c -2", ""),
    "g270": (184, "P6cc", "P 6 c c", "P 6 -2c", ""),
    "g271": (186, "P6_3mc", "P 6_3 m c", "P 6c -2c", ""),
}

POLAR_IT_NUMBERS = frozenset(
    {1}
    | set(range(3, 10))
    | set(range(25, 47))
    | set(range(75, 81))
    | set(range(99, 111))
    | set(range(143, 147))
    | set(range(156, 162))
    | set(range(168, 174))
    | set(range(183, 187))
)

POINT_GROUP_BY_RANGE = (
    ({1}, "1"),
    (set(range(3, 6)), "2"),
    (set(range(6, 10)), "m"),
    (set(range(25, 47)), "mm2"),
    (set(range(75, 81)), "4"),
    (set(range(99, 111)), "4mm"),
    (set(range(143, 147)), "3"),
    (set(range(156, 162)), "3m"),
    (set(range(168, 174)), "6"),
    (set(range(183, 187)), "6mm"),
)

CRYSTAL_SYSTEM_BY_NUMBER = (
    (range(1, 3), "triclinic"),
    (range(3, 16), "monoclinic"),
    (range(16, 75), "orthorhombic"),
    (range(75, 143), "tetragonal"),
    (range(143, 168), "trigonal"),
    (range(168, 195), "hexagonal"),
)

SCOPE_CAVEAT = (
    "This 68-record forward regular-cyclic subset corresponds exactly to the "
    "68 polar three-dimensional space-group types. General coloured wallpaper "
    "groups are broader, and there is no one-to-one correspondence between all "
    "coloured wallpaper groups and all 230 space groups."
)


def _point_group(number: int) -> str:
    for numbers, label in POINT_GROUP_BY_RANGE:
        if number in numbers:
            return label
    raise ValueError(f"space-group number {number} is not in the polar set")


def _crystal_system(number: int) -> str:
    for numbers, label in CRYSTAL_SYSTEM_BY_NUMBER:
        if number in numbers:
            return label
    raise ValueError(f"space-group number {number} is outside the supported systems")


def _lift_operations(render: dict[str, Any]) -> list[dict[str, Any]]:
    lifted = []
    for operation in render["ops"]:
        matrix = operation["M"]
        lifted.append(
            {
                "R": [
                    [matrix[0][0], matrix[0][1], 0],
                    [matrix[1][0], matrix[1][1], 0],
                    [0, 0, 1],
                ],
                "t": [operation["v"][0], operation["v"][1], operation["tau"]],
            }
        )
    return lifted


def build_payload(source_path: Path = SOURCE_DATA) -> dict[str, Any]:
    raw = source_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if source_path.resolve() == SOURCE_DATA.resolve() and digest != SOURCE_SHA256:
        raise ValueError(
            "the pinned clockwork correspondence changed; audit it before updating "
            f"SOURCE_SHA256 (found {digest})"
        )
    source = json.loads(raw)
    source_groups = source.get("groups", [])
    source_ids = [group.get("id") for group in source_groups]
    if len(source_groups) != 68 or len(set(source_ids)) != 68:
        raise ValueError("the source must contain 68 uniquely identified records")
    if set(source_ids) != set(SPACE_GROUP_BY_ID):
        missing = sorted(set(SPACE_GROUP_BY_ID) - set(source_ids))
        extra = sorted(set(source_ids) - set(SPACE_GROUP_BY_ID))
        raise ValueError(f"source/mapping ID mismatch; missing={missing}, extra={extra}")

    records: list[dict[str, Any]] = []
    for source_record in source_groups:
        group_id = source_record["id"]
        number, hm_short, hm_full, hall, choice = SPACE_GROUP_BY_ID[group_id]
        ucl_page = UCL_PAGE_BY_NUMBER.get(number)
        if ucl_page is None:
            raise ValueError(f"missing UCL reference page for space group No. {number}")
        render = source_record["render"]
        lifted = _lift_operations(render)
        if len(lifted) != len(render["ops"]):
            raise AssertionError("every planar operation must receive one height lift")
        record = {
            "ordinal": source_record["ordinal"],
            "id": group_id,
            "symbol": source_record["symbol"],
            "parent": source_record["parent"],
            "kernel": source_record["kernel"],
            "tos_notation": source_record["tos_notation"],
            "clock_order": source_record["clock_order"],
            "cyclic_group": source_record["cyclic_group"],
            "phase_residues": source_record["phase_residues"],
            "phase_profile": source_record["phase_profile"],
            "catalog_url": source_record["catalog_url"],
            "image": source_record["image"],
            "image_alt": source_record["image_alt"],
            "render": render,
            "lift_formula": "(x, y, z) ↦ (M(x, y) + v, z + τ)",
            "lift_operations": lifted,
            "space_group": {
                "it_number": number,
                "hm_short": hm_short,
                "hm_full": hm_full,
                "hall": hall,
                "choice": choice,
                "crystal_system": _crystal_system(number),
                "point_group": _point_group(number),
                "polar_axis": (
                    "z (constructed lift coordinate; before conventional-setting "
                    "normalization)"
                ),
                "image": f"output/space-groups/{group_id}.webp",
                "image_alt": (
                    f"Axonometric unit-cell view of polar space group No. {number} "
                    f"{hm_short}, lifted from cyclic colouring {group_id}."
                ),
                "ucl_reference_url": f"{UCL_SPACE_GROUP_BASE}/{ucl_page}",
                "reference_preview_image": f"output/space-groups/{group_id}.webp",
                "reference_preview_note": (
                    "Locally cached project rendering; the linked UCL diagram is not "
                    "redistributed because its published licence prohibits Internet "
                    "distribution of copies."
                ),
            },
        }
        records.append(record)

    numbers = [record["space_group"]["it_number"] for record in records]
    if len(set(numbers)) != 68 or set(numbers) != POLAR_IT_NUMBERS:
        raise ValueError("the pinned map must be a bijection onto the 68 polar types")
    family_counts = Counter(record["parent"]["hm"] for record in records)
    if set(family_counts) != set(BASE_ORDER):
        raise ValueError("all 17 wallpaper families must occur")

    return {
        "meta": {
            "schema_version": 1,
            "title": "Cyclic colourings and polar space groups",
            "source": "data/clockwork-coloring-correspondence.json",
            "source_sha256": digest,
            "source_groups": 68,
            "wallpaper_families": 17,
            "space_group_types": 68,
            "displayed_nontrivial_groups": DISPLAYED_GROUP_COUNT,
            "displayed_wallpaper_families": DISPLAYED_FAMILY_COUNT,
            "omitted_trivial_products": OMITTED_TRIVIAL_COUNT,
            "space_group_numbering": "International Tables for Crystallography",
            "mapping_database": "Pinned spglib 2.6.0 space-group type results",
            "construction": "Embed (M, v, τ) as (diag(M, 1), (v, τ)); cyclic phase becomes fractional height along the new z coordinate.",
            "scope_caveat": SCOPE_CAVEAT,
            "image_size": [IMAGE_WIDTH, IMAGE_HEIGHT],
            "image_note": "Space-group plate hues repeat the cyclic phase palette only to trace the height lift; colour is not additional crystallographic structure in the 3D group.",
            "external_reference": "Jeremy K. Cockcroft, A Hypertext Book of Crystallographic Space Group Diagrams and Tables, UCL/Birkbeck College, 1997-1999.",
            "external_reference_index": f"{UCL_SPACE_GROUP_BASE}/sgp.htm",
            "external_reference_cache_policy": "The project does not redistribute UCL pages or images because their published end-user licence prohibits Internet distribution; hover cards reuse locally generated project plates.",
            "polar_it_numbers": sorted(POLAR_IT_NUMBERS),
            "family_counts": {base: family_counts[base] for base in BASE_ORDER},
        },
        "groups": records,
    }


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("meta", {}).get("scope_caveat") != SCOPE_CAVEAT:
        raise ValueError("scope caveat is missing or changed")
    groups = payload.get("groups", [])
    if len(groups) != 68:
        raise ValueError("expected 68 group records")
    ids = [group.get("id") for group in groups]
    if set(ids) != set(SPACE_GROUP_BY_ID) or len(ids) != len(set(ids)):
        raise ValueError("group IDs do not match the pinned mapping")
    numbers = []
    for group in groups:
        expected = SPACE_GROUP_BY_ID[group["id"]]
        actual = group["space_group"]
        fields = (
            actual["it_number"], actual["hm_short"], actual["hm_full"],
            actual["hall"], actual["choice"],
        )
        if fields != expected:
            raise ValueError(f"unpinned space-group metadata for {group['id']}")
        if group["parent"]["hm"] not in BASE_ORDER:
            raise ValueError(f"unknown wallpaper family for {group['id']}")
        if group["lift_operations"] != _lift_operations(group["render"]):
            raise ValueError(f"incorrect lifted operations for {group['id']}")
        numbers.append(actual["it_number"])
    if len(set(numbers)) != 68 or set(numbers) != POLAR_IT_NUMBERS:
        raise ValueError("space-group numbers are not the 68 polar types")


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    value = hex_colour.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _mix(colour: tuple[int, int, int], other: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round((1 - amount) * left + amount * right) for left, right in zip(colour, other))  # type: ignore[return-value]


def _fractional_site(record: dict[str, Any], operation: dict[str, Any]) -> tuple[float, float, float]:
    base_x, base_y = record["render"]["base"]
    matrix = operation["M"]
    x = matrix[0][0] * base_x + matrix[0][1] * base_y + operation["v"][0]
    y = matrix[1][0] * base_x + matrix[1][1] * base_y + operation["v"][1]
    # A small non-special height keeps the motif away from a cell face while
    # preserving every relative tau exactly.
    z = 0.083 + operation["tau"]
    return x % 1.0, y % 1.0, z % 1.0


def _projection(record: dict[str, Any]) -> tuple[Any, Any]:
    basis = record["render"]["basis"]
    a = (float(basis[0][0]), float(basis[0][1]))
    b = (float(basis[1][0]), float(basis[1][1]))
    longest = max(math.hypot(*a), math.hypot(*b), 1e-8)
    a = (a[0] / longest, a[1] / longest)
    b = (b[0] / longest, b[1] / longest)

    def raw(u: float, v: float, w: float) -> tuple[float, float]:
        x = u * a[0] + v * b[0]
        y = u * a[1] + v * b[1]
        return x - 0.62 * y, 0.31 * x + 0.50 * y - 1.08 * w

    corners = [raw(u, v, w) for u in (0.0, 1.0) for v in (0.0, 1.0) for w in (0.0, 1.0)]
    min_x = min(point[0] for point in corners)
    max_x = max(point[0] for point in corners)
    min_y = min(point[1] for point in corners)
    max_y = max(point[1] for point in corners)
    usable_width = IMAGE_WIDTH * ANTIALIAS - 132 * ANTIALIAS
    usable_height = IMAGE_HEIGHT * ANTIALIAS - 96 * ANTIALIAS
    scale = min(
        usable_width / max(max_x - min_x, 1e-8),
        usable_height / max(max_y - min_y, 1e-8),
    )
    offset_x = (IMAGE_WIDTH * ANTIALIAS - scale * (min_x + max_x)) / 2
    offset_y = (IMAGE_HEIGHT * ANTIALIAS - scale * (min_y + max_y)) / 2

    def project(u: float, v: float, w: float) -> tuple[float, float]:
        x, y = raw(u, v, w)
        return offset_x + scale * x, offset_y + scale * y

    return project, scale


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    fill: tuple[int, int, int],
    width: int,
    dash: float,
) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1e-8:
        return
    ux, uy = dx / length, dy / length
    position = 0.0
    while position < length:
        stop = min(position + dash, length)
        draw.line(
            (
                start[0] + position * ux, start[1] + position * uy,
                start[0] + stop * ux, start[1] + stop * uy,
            ),
            fill=fill,
            width=width,
        )
        position += 2 * dash


def render_space_group_plate(record: dict[str, Any]) -> bytes:
    width = IMAGE_WIDTH * ANTIALIAS
    height = IMAGE_HEIGHT * ANTIALIAS
    background = (247, 244, 236)
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    project, scale = _projection(record)

    # Back faces first.  The solid/dashed distinction makes the cell legible
    # without requiring WebGL or JavaScript.
    cell_edges = []
    for axis in range(3):
        for first in (0.0, 1.0):
            for second in (0.0, 1.0):
                low = [0.0, 0.0, 0.0]
                high = [0.0, 0.0, 0.0]
                low[axis] = 0.0
                high[axis] = 1.0
                other_axes = [index for index in range(3) if index != axis]
                low[other_axes[0]] = high[other_axes[0]] = first
                low[other_axes[1]] = high[other_axes[1]] = second
                cell_edges.append((tuple(low), tuple(high), sum(low) / 3))
    cell_edges.sort(key=lambda edge: edge[2])
    for start, end, depth in cell_edges:
        colour = (183, 191, 186) if depth < 0.34 else (85, 104, 97)
        line_width = max(2, round((1.0 if depth < 0.34 else 1.5) * ANTIALIAS))
        draw.line((*project(*start), *project(*end)), fill=colour, width=line_width)

    operations = record["render"]["ops"]
    site_rows = []
    for operation in operations:
        u, v, w = _fractional_site(record, operation)
        site_rows.append((project(u, v, w)[1], u, v, w, operation))
    site_rows.sort(reverse=True)

    motif_scale = 1.65 if len(operations) <= 2 else 1.30 if len(operations) <= 4 else 1.0
    motif = tuple(
        (motif_scale * x, motif_scale * y)
        for x, y in (
            (-0.060, -0.045), (0.055, -0.070), (0.025, -0.005),
            (0.073, 0.050), (-0.020, 0.037),
        )
    )
    guide_colour = (198, 204, 200)
    outline = (38, 51, 47)
    for _, u, v, w, operation in site_rows:
        centre = project(u, v, w)
        floor = project(u, v, 0.0)
        _draw_dashed_line(
            draw, floor, centre, guide_colour,
            max(1, ANTIALIAS), 3.2 * ANTIALIAS,
        )
        floor_radius = 2.4 * ANTIALIAS
        draw.ellipse(
            (floor[0] - floor_radius, floor[1] - floor_radius,
             floor[0] + floor_radius, floor[1] + floor_radius),
            fill=(132, 145, 139),
        )

        matrix = operation["M"]
        points = []
        for local_x, local_y in motif:
            du = matrix[0][0] * local_x + matrix[0][1] * local_y
            dv = matrix[1][0] * local_x + matrix[1][1] * local_y
            points.append(project(u + du, v + dv, w))
        phase = int(round(float(operation["tau"]) * record["clock_order"])) % record["clock_order"]
        base_colour = _rgb(PALETTE[phase])
        shadow_points = [(x + 3 * ANTIALIAS, y + 4 * ANTIALIAS) for x, y in points]
        draw.polygon(shadow_points, fill=_mix(outline, background, 0.60))
        draw.polygon(points, fill=base_colour)
        draw.line(points + [points[0]], fill=outline, width=max(2, ANTIALIAS), joint="curve")
        marker = points[1]
        marker_radius = max(2.0 * ANTIALIAS, 0.012 * scale)
        draw.ellipse(
            (marker[0] - marker_radius, marker[1] - marker_radius,
             marker[0] + marker_radius, marker[1] + marker_radius),
            fill=background,
            outline=outline,
            width=max(1, ANTIALIAS),
        )

    # A compact three-axis key at the lower left: the first two axes lie in the
    # base and the constructed z/height direction is vertical.  This is shown
    # before any change to the conventional crystallographic setting.
    axis_origin = (58 * ANTIALIAS, (IMAGE_HEIGHT - 42) * ANTIALIAS)
    axes = (
        ((105 * ANTIALIAS, (IMAGE_HEIGHT - 42) * ANTIALIAS), (193, 75, 61)),
        ((34 * ANTIALIAS, (IMAGE_HEIGHT - 69) * ANTIALIAS), (40, 137, 103)),
        ((58 * ANTIALIAS, (IMAGE_HEIGHT - 100) * ANTIALIAS), _rgb(PALETTE[0])),
    )
    for endpoint, colour in axes:
        draw.line((*axis_origin, *endpoint), fill=colour, width=3 * ANTIALIAS)
        dx, dy = endpoint[0] - axis_origin[0], endpoint[1] - axis_origin[1]
        length = max(math.hypot(dx, dy), 1e-8)
        ux, uy = dx / length, dy / length
        perpendicular = (-uy, ux)
        arrow = [
            endpoint,
            (endpoint[0] - 8 * ANTIALIAS * ux + 4 * ANTIALIAS * perpendicular[0],
             endpoint[1] - 8 * ANTIALIAS * uy + 4 * ANTIALIAS * perpendicular[1]),
            (endpoint[0] - 8 * ANTIALIAS * ux - 4 * ANTIALIAS * perpendicular[0],
             endpoint[1] - 8 * ANTIALIAS * uy - 4 * ANTIALIAS * perpendicular[1]),
        ]
        draw.polygon(arrow, fill=colour)

    image = image.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", lossless=True, method=6)
    return buffer.getvalue()


def _hm_html(symbol: str) -> str:
    escaped = escape(symbol)
    return re.sub(r"_([0-9]+)", r"<sub>\1</sub>", escaped)


def _phase_legend(record: dict[str, Any]) -> str:
    return "\n".join(
        "<li>"
        f"<span class=\"swatch\" style=\"--swatch: {escape(residue['color'])}\"></span>"
        f"<span>phase {escape(residue['phase'])} · height {escape(residue['phase'])} of one vertical period</span>"
        "</li>"
        for residue in record["phase_residues"]
    )


def _entry_html(record: dict[str, Any], family_ordinal: int, family_total: int) -> str:
    group_id = escape(record["id"])
    space_group = record["space_group"]
    number = space_group["it_number"]
    setting = space_group["choice"] or "standard"
    reference_url = escape(space_group["ucl_reference_url"])
    return f"""
          <article class="space-entry" id="{group_id}" data-space-tabpanel>
            <header class="entry-header">
              <p class="entry-number">{family_ordinal:02d} / {family_total:02d}</p>
              <div>
                <h3><span class="color-type">{escape(record['tos_notation'])}</span><span class="entry-arrow" aria-hidden="true">→</span><span class="space-symbol">{_hm_html(space_group['hm_short'])}</span> <span class="space-number">No. {number}</span><span class="group-id">{group_id}</span></h3>
                <p class="entry-identity">Forward record <a href="{escape(record['catalog_url'])}">{group_id}</a> · catalog symbol {escape(record['symbol'])}</p>
              </div>
              <div class="entry-badges" aria-label="Group classification">
                <span class="it-badge">IT {number}</span>
                <span>{escape(record['cyclic_group'])}</span>
                <span>{escape(space_group['point_group'])}</span>
              </div>
            </header>

            <div class="visual-sequence" aria-label="Colouring followed by its height lift">
              <figure class="colour-plate">
                <span class="visual-label">1 · coloured wallpaper group</span>
                <img src="{escape(record['image'])}" alt="{escape(record['image_alt'])}" width="720" height="420" loading="lazy" decoding="async">
                <figcaption>{escape(record['tos_notation'])} over wallpaper group {escape(record['parent']['hm'])}</figcaption>
              </figure>
              <span class="lift-arrow" aria-hidden="true">→</span>
              <figure class="space-group-viewer" data-space-viewer data-group-id="{group_id}">
                <span class="visual-label">2 · corresponding space group</span>
                <div class="space-stage" data-state="static">
                  <img data-space-static src="{escape(space_group['image'])}" alt="{escape(space_group['image_alt'])}" width="720" height="480" loading="lazy" decoding="async">
                  <canvas class="space-canvas" data-space-canvas width="720" height="480">Interactive unit-cell view of space group No. {number} {escape(space_group['hm_short'])}.</canvas>
                </div>
                <div class="space-controls" data-space-controls>
                  <button class="space-toggle" type="button" data-space-toggle aria-pressed="false" disabled><span data-space-toggle-label>Rotate</span></button>
                  <label class="visually-hidden" for="rotation-{group_id}">View angle</label>
                  <input class="space-slider" id="rotation-{group_id}" data-space-slider type="range" min="0" max="1" step="0.001" value="0.095" disabled>
                  <output class="space-output" data-space-output for="rotation-{group_id}">34°</output>
                </div>
                <figcaption>
                  <span>No. {number} {_hm_html(space_group['hm_short'])} · colour only traces inherited height</span>
                  <span class="space-reference">
                    <a class="space-reference-link" href="{reference_url}" target="_blank" rel="noopener" aria-describedby="ucl-credit">UCL diagram and tables</a>
                    <span class="space-reference-preview" role="tooltip">
                      <img src="{escape(space_group['reference_preview_image'])}" alt="" width="720" height="480" loading="lazy" decoding="async">
                      <span>Local project preview · open the UCL reference for its original diagram and tables</span>
                    </span>
                  </span>
                </figcaption>
              </figure>
            </div>

            <div class="correspondence-copy">
              <section class="lift-copy" aria-labelledby="{group_id}-construction">
                <h4 id="{group_id}-construction">Height lift</h4>
                <p>Each planar operation is lifted by <code>(x, y, z) ↦ (M(x, y) + v, z + τ)</code>. Thus a colour increment <em>j</em> modulo {record['clock_order']} becomes a translation of <em>j</em>/{record['clock_order']} along the new height direction. This constructed coordinate is shown before normalization to the listed conventional crystallographic setting.</p>
                <p>The plate repeats the colour palette to make those height levels easy to follow. Colour is not additional structure in the resulting ordinary 3D space group.</p>
              </section>
              <dl class="group-data" aria-label="Crystallographic identification">
                <div><dt>International Tables</dt><dd>No. {number}</dd></div>
                <div><dt>HM short</dt><dd>{_hm_html(space_group['hm_short'])}</dd></div>
                <div><dt>HM full</dt><dd>{_hm_html(space_group['hm_full'])}</dd></div>
                <div><dt>Hall</dt><dd><code>{escape(space_group['hall'])}</code></dd></div>
                <div><dt>Choice</dt><dd>{escape(setting)}</dd></div>
                <div><dt>Crystal class</dt><dd>{escape(space_group['crystal_system'])} · {escape(space_group['point_group'])}</dd></div>
                <div><dt>External reference</dt><dd><a href="{reference_url}" target="_blank" rel="noopener">UCL space-group page</a></dd></div>
              </dl>
            </div>
          </article>"""


def _trivial_product_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    space_group = record["space_group"]
    return (
        f'<aside class="trivial-product" id="{group_id}" data-trivial-product '
        f'aria-label="Trivial one-colour product {group_id} over wallpaper group '
        f'{escape(record["parent"]["hm"])}">'
        "<p><strong>Trivial one-colour product · C<sub>1</sub>.</strong> "
        f'The inherited lift {escape(record["tos_notation"])} ({group_id}) gives '
        f'No. {space_group["it_number"]} {_hm_html(space_group["hm_short"])}. '
        "It remains in the complete 68-record audit data, but is omitted from "
        "the directory, tabs, and paired visualizations above.</p>"
        "</aside>"
    )


def _family_html(
    base: str,
    rows: list[dict[str, Any]],
    trivial_record: dict[str, Any],
    family_index: int,
) -> str:
    tabs = "\n".join(
        f'<a id="tab-{escape(record["id"])}" href="#{escape(record["id"])}" '
        f'class="space-tab" data-space-tab data-panel-id="{escape(record["id"])}">'
        f'<span class="tab-signature">{escape(record["tos_notation"])}</span>'
        f'<span class="tab-meta">No. {record["space_group"]["it_number"]} '
        f'{_hm_html(record["space_group"]["hm_short"])}</span></a>'
        for record in rows
    )
    entries = "\n".join(
        _entry_html(record, index, len(rows)) for index, record in enumerate(rows, 1)
    )
    order_counts = Counter(record["clock_order"] for record in rows)
    census = (
        " · ".join(f"C{order}: {order_counts[order]}" for order in sorted(order_counts))
        if rows
        else "none"
    )
    lift_word = "lift" if len(rows) == 1 else "lifts"
    family_class = "wallpaper-family space-family" + (" is-empty" if not rows else "")
    if rows:
        contents = f"""
      <div class="space-tabs" data-space-tabs>
        <nav class="space-tabbar" data-space-tablist aria-label="Nontrivial cyclic lifts over wallpaper group {escape(base)}">
          {tabs}
        </nav>
        <div class="space-panels">
{entries}
        </div>
      </div>"""
    else:
        contents = """
      <div class="family-empty" role="note">
        <p><strong>No more-than-one-colour lift occurs.</strong> This wallpaper family contributes no entry to the 51-group visualization atlas; its C1 product is retained below only for audit completeness.</p>
      </div>"""
    return f"""
    <section class="{family_class}" id="wallpaper-{escape(base)}" data-wallpaper-family aria-labelledby="wallpaper-{escape(base)}-title">
      <header class="family-header">
        <p class="section-number">Wallpaper family {family_index:02d} / 17</p>
        <h2 id="wallpaper-{escape(base)}-title"><span class="family-hm">{escape(base)}</span> <span class="family-orbifold">{escape(ORBIFOLD_BY_BASE[base])}</span> <span class="family-count">{len(rows)} nontrivial {lift_word}</span></h2>
        <p class="family-summary">{escape(FAMILY_SUMMARIES[base])}</p>
        <p class="family-census">More-than-one-colour orders · {census}</p>
      </header>
{contents}
      {_trivial_product_html(trivial_record)}
    </section>"""


def _directory_family_html(base: str, rows: list[dict[str, Any]]) -> str:
    group_links = "\n".join(
        f'<a class="directory-group" href="#{escape(record["id"])}" data-directory-group="{escape(record["id"])}">'
        f'<span class="directory-signature">{escape(record["tos_notation"])}</span>'
        f'<span class="directory-space-group">No. {record["space_group"]["it_number"]} {_hm_html(record["space_group"]["hm_short"])}</span>'
        f'<span class="directory-group-id">{escape(record["id"])}</span></a>'
        for record in rows
    )
    return f"""
        <section class="directory-family">
          <h3><a class="directory-family-link" href="#wallpaper-{escape(base)}">{escape(base)} <span>{escape(ORBIFOLD_BY_BASE[base])} · {len(rows)} nontrivial {"type" if len(rows) == 1 else "types"}</span></a></h3>
          <div class="directory-groups">{group_links}</div>
        </section>"""


def page_html(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    all_groups = payload["groups"]
    displayed_groups = [record for record in all_groups if record["clock_order"] > 1]
    trivial_groups = [record for record in all_groups if record["clock_order"] == 1]
    if len(displayed_groups) != DISPLAYED_GROUP_COUNT:
        raise ValueError(f"expected {DISPLAYED_GROUP_COUNT} nontrivial display groups")
    if len(trivial_groups) != OMITTED_TRIVIAL_COUNT:
        raise ValueError(f"expected {OMITTED_TRIVIAL_COUNT} trivial products")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in displayed_groups:
        grouped[record["parent"]["hm"]].append(record)
    trivial_by_base = {record["parent"]["hm"]: record for record in trivial_groups}
    if set(trivial_by_base) != set(BASE_ORDER):
        raise ValueError("expected one trivial product for every wallpaper family")
    contributing_bases = [base for base in BASE_ORDER if grouped[base]]
    if len(contributing_bases) != DISPLAYED_FAMILY_COUNT:
        raise ValueError(f"expected {DISPLAYED_FAMILY_COUNT} contributing families")
    families = "\n".join(
        _family_html(base, grouped[base], trivial_by_base[base], index)
        for index, base in enumerate(BASE_ORDER, 1)
    )
    directory = "\n".join(
        _directory_family_html(base, grouped[base]) for base in contributing_bases
    ).strip()
    caveat = escape(payload["meta"]["scope_caveat"])
    digest = escape(payload["meta"]["source_sha256"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Paired visualizations of the 51 nontrivial cyclic wallpaper colourings and their polar space groups, with all 68 types retained in the audit data.">
  <meta name="theme-color" content="#ffffff">
  <title>Cyclic colourings and polar space groups</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="site-controls-v2.css">
  <link rel="stylesheet" href="{STYLE_SRC}">
</head>
<body>
  <a class="skip-link" href="#correspondences">Skip to correspondences</a>

  <header class="site-header">
    <div class="header-inner">
      <a class="site-name" href="./">Spacetime-group visualizations</a>
      <nav aria-label="Project links">
        <a href="./">Gallery</a>
        <a href="future-directions.html">Colours</a>
        <a href="clockwork-coloring-correspondence.html">Correspondence</a>
        <a href="space-group-correspondence.html" aria-current="page">Space groups</a>
        <a href="data/space-group-correspondence.json">Data</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>

  <main class="space-page">
    <section class="space-hero" aria-labelledby="page-title">
      <p class="section-number">51 displayed multi-colour lifts · 14 contributing families · 68-type audit</p>
      <h1 id="page-title">Cyclic colourings <span aria-hidden="true">↔</span> polar space groups</h1>
      <p class="lead">Treat the cyclic colour coordinate as height. This atlas gives paired visualizations for the 51 lifts with more than one colour; the 17 inherited C1 products appear only as grey audit notes.</p>
      <aside class="answer-card" role="note" aria-label="Scope of the correspondence">
        <p class="answer-title">Is it one-to-one?</p>
        <p class="answer-copy"><strong>For this selected subset, yes.</strong> {caveat}</p>
      </aside>
    </section>

    <section class="construction" aria-labelledby="construction-title">
      <div class="construction-copy">
        <p class="section-number">The construction</p>
        <h2 id="construction-title">Colour becomes a third coordinate</h2>
        <p>A regular cyclic colouring is encoded by a phase character. Lift the plane to horizontal slices of 3-space and read that phase as fractional height. Rotations become screws when they change colour; mirrors become glide planes when they carry a nonzero phase.</p>
      </div>
      <div class="construction-formula" aria-label="Height-lift formula">
        <p>For every planar operation</p>
        <code>(M, v, τ): (x, y, z) ↦ (M(x, y) + v, z + τ)</code>
      </div>
    </section>

    <nav class="atlas-directory" aria-labelledby="directory-title">
      <p class="section-number">51 displayed groups · 14 contributing families</p>
      <h2 id="directory-title">More-than-one-colour lifts</h2>
      <p class="directory-legend">Only C<sub>N</sub> lifts with N &gt; 1 appear here. Select a card to open its paired plane and space visualizations; all 17 wallpaper-family sections remain in the atlas below.</p>
      <div class="directory-families">
{directory}
      </div>
    </nav>

    <div class="space-atlas" id="correspondences">
{families}
    </div>

    <section class="sources" aria-labelledby="provenance-title">
      <p class="section-number">Audit trail</p>
      <h2 id="provenance-title">Pinned identifications and reproducible plates</h2>
      <p>The <a href="data/space-group-correspondence.json">complete 68-record JSON</a> stores every 3×3 lifted operation alongside International Tables numbers, short and full Hermann–Mauguin symbols, Hall symbols, and setting choices. This page gives full paired visualizations to the 51 records with N &gt; 1 and keeps the 17 C1 products as compact grey audit notes. The identifications are pinned from spglib 2.6.0 rather than recomputed in the browser. The source colouring data has SHA-256 <code>{digest}</code>.</p>
      <p>The 3D hues are a visual bridge back to cyclic phase; after lifting, the ordinary space group itself has no colour label. All static plates remain visible without JavaScript. When available, the local controller replaces them with a rotatable canvas derived from the same checked-in operations.</p>
      <p id="ucl-credit">Each displayed 3D group links to Jeremy K. Cockcroft’s <a href="{escape(payload['meta']['external_reference_index'])}" target="_blank" rel="noopener"><cite>A Hypertext Book of Crystallographic Space Group Diagrams and Tables</cite></a> at UCL/Birkbeck College. Hover or keyboard-focus shows a locally generated project plate as a quick preview. The original UCL HTML and GIF are not copied into this public repository because the source’s published licence prohibits Internet distribution of copies.</p>
      <ul>
        <li><a href="https://journals.iucr.org/j/issues/2018/05/00/in5013/index.html">IUCr: <cite>Crystallographic shelves: space-group hierarchy explained</cite></a> identifies the ten polar crystal classes and their 68 space-group types.</li>
        <li><a href="https://doi.org/10.1107/S0365110X57001966">A. L. Mackay, <cite>Extensions of space-group theory</cite></a> develops the colour/extra-coordinate relationship.</li>
        <li><a href="https://arxiv.org/abs/math/9911185">Conway, Delgado Friedrichs, Huson &amp; Thurston, <cite>On Three-Dimensional Space Groups</cite></a> organizes space groups as fibrations over plane crystallographic groups.</li>
      </ul>
      <pre><code>python3 scripts/generate_space_group_correspondence.py
python3 scripts/generate_space_group_correspondence.py --check</code></pre>
    </section>

    <footer>
      <p><a href="./">Visualization gallery</a> · <a href="clockwork-coloring-correspondence.html">Clockwork/colouring correspondence</a> · <a href="README.md">README</a> · <a href="https://github.com/yaroslavvb/animated-groups">GitHub source</a></p>
    </footer>
  </main>

  <script type="module" src="{SCRIPT_SRC}"></script>
</body>
</html>
"""


def data_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def expected_outputs(payload: dict[str, Any]) -> tuple[dict[Path, str], dict[Path, bytes]]:
    text_outputs = {DATA: data_text(payload), PAGE: page_html(payload)}
    binary_outputs = {
        IMAGE_DIR / f"{record['id']}.webp": render_space_group_plate(record)
        for record in payload["groups"]
    }
    return text_outputs, binary_outputs


def check_outputs(payload: dict[str, Any]) -> list[Path]:
    stale: list[Path] = []
    text_outputs, binary_outputs = expected_outputs(payload)
    for path, expected in text_outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            stale.append(path)
    for path, expected in binary_outputs.items():
        if not path.exists() or path.read_bytes() != expected:
            stale.append(path)
    expected_images = set(binary_outputs)
    if IMAGE_DIR.exists():
        stale.extend(
            path for path in IMAGE_DIR.glob("*.webp") if path not in expected_images
        )
    return sorted(set(stale))


def write_outputs(payload: dict[str, Any]) -> None:
    text_outputs, binary_outputs = expected_outputs(payload)
    for path, contents in text_outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    for path, contents in binary_outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-data", type=Path, default=SOURCE_DATA,
        help="read-only clockwork correspondence source",
    )
    parser.add_argument(
        "--check", action="store_true", help="fail if generated outputs are stale",
    )
    args = parser.parse_args(argv)

    payload = build_payload(args.source_data)
    validate_payload(payload)
    if args.check:
        stale = check_outputs(payload)
        if stale:
            for path in stale:
                try:
                    label = path.relative_to(ROOT)
                except ValueError:
                    label = path
                print(f"stale: {label}", file=sys.stderr)
            return 1
        print("space-group correspondence outputs are current")
        return 0

    write_outputs(payload)
    print(
        f"wrote {DATA.relative_to(ROOT)}, {PAGE.relative_to(ROOT)}, and "
        f"{len(payload['groups'])} plates in {IMAGE_DIR.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
