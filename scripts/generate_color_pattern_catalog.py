#!/usr/bin/env python3
"""Generate the periodic colour-pattern type catalog for one to three colours.

The finite objects in this catalog are Gruenbaum--Shephard colour-pattern
*types*, not individual motif drawings.  Literal periodic patterns have
infinitely many geometric realizations.  The 2- and 3-colour records below
are transcribed from Figures 8.2.2, 8.2.3, 8.3.5, and 8.3.6 of Chapter 8 of
Tilings and Patterns.  Chaim Goodman--Strauss's coloured-orbifold names come
from Tables 11.1 and 12.1 of The Symmetries of Things.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html import escape
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

from chaim_short_signatures import (
    THREE_FOLD_SHORT_SIGNATURE_BY_TYPE,
    TWO_FOLD_SHORT_SIGNATURE_BY_TYPE,
)
from color_pattern_book_excerpt_specs import (
    decorate_payload,
    validate_excerpt_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "color-pattern-catalog.html"
DATA = ROOT / "data" / "color-pattern-catalog.json"

PALETTE = ("#0072B2", "#E69F00", "#009E73")


WALLPAPERS: tuple[dict[str, Any], ...] = (
    {"id": "p1", "hm": "p1", "orbifold": "◦", "summary": "Translations only.", "ordinary": ("PP1",)},
    {"id": "p2", "hm": "p2", "orbifold": "2222", "summary": "Four order-2 cone points.", "ordinary": ("PP7", "PP8")},
    {"id": "pm", "hm": "pm", "orbifold": "**", "summary": "Two mirror boundaries.", "ordinary": ("PP3", "PP4")},
    {"id": "pg", "hm": "pg", "orbifold": "××", "summary": "Two crosscaps; glide reflections, no mirrors.", "ordinary": ("PP2",)},
    {"id": "cm", "hm": "cm", "orbifold": "*×", "summary": "One mirror boundary and one crosscap.", "ordinary": ("PP5", "PP6")},
    {"id": "pmm", "hm": "pmm", "orbifold": "*2222", "summary": "Four order-2 mirror corners.", "ordinary": ("PP14", "PP15", "PP16")},
    {"id": "pmg", "hm": "pmg", "orbifold": "22*", "summary": "Two order-2 cone points and one mirror boundary.", "ordinary": ("PP11", "PP12", "PP13")},
    {"id": "pgg", "hm": "pgg", "orbifold": "22×", "summary": "Two order-2 cone points and one crosscap.", "ordinary": ("PP9", "PP10")},
    {"id": "cmm", "hm": "cmm", "orbifold": "2*22", "summary": "One order-2 cone point and two order-2 mirror corners.", "ordinary": ("PP17", "PP18", "PP19", "PP20")},
    {"id": "p4", "hm": "p4", "orbifold": "442", "summary": "Order-4, order-4, and order-2 cone points.", "ordinary": ("PP30", "PP31", "PP32")},
    {"id": "p4m", "hm": "p4m", "orbifold": "*442", "summary": "Order-4, order-4, and order-2 mirror corners.", "ordinary": ("PP37", "PP38", "PP39", "PP40", "PP41")},
    {"id": "p4g", "hm": "p4g", "orbifold": "4*2", "summary": "One order-4 cone point and one order-2 mirror corner.", "ordinary": ("PP33", "PP34", "PP35", "PP36")},
    {"id": "p3", "hm": "p3", "orbifold": "333", "summary": "Three order-3 cone points.", "ordinary": ("PP21", "PP22")},
    {"id": "p3m1", "hm": "p3m1", "orbifold": "*333", "summary": "Three order-3 mirror corners.", "ordinary": ("PP27", "PP28", "PP29")},
    {"id": "p31m", "hm": "p31m", "orbifold": "3*3", "summary": "One order-3 cone point and one order-3 mirror corner.", "ordinary": ("PP23", "PP24", "PP25", "PP26")},
    {"id": "p6", "hm": "p6", "orbifold": "632", "summary": "Order-6, order-3, and order-2 cone points.", "ordinary": ("PP42", "PP43", "PP44", "PP45")},
    {"id": "p6m", "hm": "p6m", "orbifold": "*632", "summary": "Order-6, order-3, and order-2 mirror corners.", "ordinary": ("PP46", "PP47", "PP48", "PP49", "PP50", "PP51")},
)


# Order within each parent is the Gruenbaum--Shephard p...[k]_i order.  The
# entries themselves are the G/K names from ToS Table 11.1.  The crosswalk
# is checked against the alternative symbols in G&S Table 8.2.2 (and the
# explicit comparison in Schaffer, Dichromatic Dances, Figure 10); it is not
# the row order of ToS Table 11.1.  The sole non-unique pair is kept as two
# explicit variants.
TWO_COLOUR_TYPES: dict[str, tuple[str, ...]] = {
    "p1": ("◦/◦",),
    "p2": ("2222/◦", "2222/2222"),
    "pm": ("**/××", "**/*×", "**/** (1)", "**/◦", "**/** (2)"),
    "pg": ("××/◦", "××/××"),
    "cm": ("*×/◦", "*×/××", "*×/**"),
    "pmm": ("*2222/*2222", "*2222/**", "*2222/2*22", "*2222/22*", "*2222/2222"),
    "pmg": ("22*/22*", "22*/××", "22*/22×", "22*/**", "22*/2222"),
    "pgg": ("22×/××", "22×/2222"),
    "cmm": ("2*22/22×", "2*22/*×", "2*22/22*", "2*22/2222", "2*22/*2222"),
    "p4": ("442/442", "442/2222"),
    "p4m": ("*442/4*2", "*442/442", "*442/2*22", "*442/*2222", "*442/*442"),
    "p4g": ("4*2/442", "4*2/2*22", "4*2/22×"),
    "p3": (),
    "p3m1": ("*333/333",),
    "p31m": ("3*3/333",),
    "p6": ("632/333",),
    "p6m": ("*632/3*3", "*632/*333", "*632/632"),
}


# Explicit raised 3 distinguishes ToS's threefold notation from the
# superficially similar twofold G/K notation.  A double slash means H != K
# and image S3; a single slash means H = K and image C3.
THREE_COLOUR_TYPES: dict[str, tuple[str, ...]] = {
    "p1": ("◦³/◦",),
    "p2": ("2222³//◦",),
    "pm": ("**³//◦", "**³/**"),
    "pg": ("××³/××", "××³//◦"),
    "cm": ("*×³/*×", "*×³//◦"),
    "pmm": ("*2222³//**",),
    "pmg": ("22*³//××", "22*³//**"),
    "pgg": ("22×³//××",),
    "cmm": ("2*22³//*×",),
    "p4": (),
    "p4m": (),
    "p4g": (),
    "p3": ("333³/◦", "333³/333"),
    "p3m1": ("*333³//◦", "*333³//333"),
    "p31m": ("3*3³//◦", "3*3³/*333"),
    "p6": ("632³/2222", "632³//333"),
    "p6m": ("*632³//2222", "*632³//*333"),
}


# For an S3 colour action, H is the index-3 stabilizer of one chosen colour
# and K is the index-6 all-colours kernel.  ToS abbreviates G³/H/K to G³//K,
# so H must be restored from the index-3 wallpaper-subgroup classification.
NONREGULAR_THREE_STABILIZER: dict[str, str] = {
    "2222³//◦": "2222",
    "**³//◦": "**",
    "××³//◦": "××",
    "*×³//◦": "*×",
    "*2222³//**": "*2222",
    "22*³//××": "22*",
    "22*³//**": "22*",
    "22×³//××": "22×",
    "2*22³//*×": "2*22",
    "*333³//◦": "*×",
    "*333³//333": "3*3",
    "3*3³//◦": "*×",
    "632³//333": "632",
    "*632³//2222": "2*22",
    "*632³//*333": "*632",
}


def gkey(parent: str, colours: int, index: int) -> tuple[str, int, int]:
    return parent, colours, index


# Each tuple is (parent, G&S colour-group index, G&S colour-pattern symbol).
# One primitive pattern type occurs for every colour group.
PRIMITIVE_TWO: tuple[tuple[str, int, str], ...] = tuple(
    (parent, index, label)
    for parent, prefix in (
        ("p1", "PP1"), ("pg", "PP2"), ("pm", "PP3"), ("cm", "PP5"),
        ("p2", "PP7"), ("pgg", "PP9"), ("pmg", "PP11"),
        ("pmm", "PP14"), ("cmm", "PP17"), ("p31m", "PP23"),
        ("p3m1", "PP27"), ("p4", "PP30"), ("p4g", "PP33"),
        ("p4m", "PP37"), ("p6", "PP42"), ("p6m", "PP46"),
    )
    for index in range(1, len(TWO_COLOUR_TYPES[parent]) + 1)
    for label in (f"{prefix}[2]" + (f"_{index}" if len(TWO_COLOUR_TYPES[parent]) > 1 else ""),)
)


NONPRIMITIVE_TWO: tuple[tuple[str, int, str], ...] = (
    ("pm", 2, "PP4[2]_2"), ("pm", 3, "PP4[2]_3"), ("pm", 5, "PP4[2]_5"),
    ("cm", 3, "PP6[2]_3"), ("p2", 2, "PP8[2]_2"), ("pgg", 2, "PP10[2]_2"),
    ("pmg", 1, "PP12[2]_1"), ("pmg", 1, "PP13[2]_1"),
    ("pmg", 3, "PP12[2]_3"), ("pmg", 5, "PP12[2]_5"), ("pmg", 4, "PP13[2]_4"),
    ("pmm", 1, "PP15[2]_1"), ("pmm", 1, "PP15[2]_1*"),
    ("pmm", 2, "PP15[2]_2"), ("pmm", 3, "PP15[2]_3"),
    ("pmm", 3, "PP16[2]_3"), ("pmm", 4, "PP15[2]_4"),
    ("pmm", 1, "PP16[2]_1"),
    ("cmm", 3, "PP18[2]_3"), ("cmm", 3, "PP19[2]_3"),
    ("cmm", 4, "PP18[2]_4"), ("cmm", 2, "PP19[2]_2"),
    ("cmm", 5, "PP19[2]_5"), ("cmm", 5, "PP20[2]_5"),
    ("p31m", 1, "PP24[2]"),
    ("p4", 2, "PP31[2]_2"), ("p4", 1, "PP32[2]_1"),
    ("p4g", 1, "PP34[2]_1"), ("p4g", 2, "PP35[2]_2"), ("p4g", 2, "PP36[2]_2"),
    ("p4m", 1, "PP38[2]_1"), ("p4m", 4, "PP38[2]_4"),
    ("p4m", 4, "PP40[2]_4"), ("p4m", 5, "PP38[2]_5"),
    ("p4m", 5, "PP39[2]_5"), ("p4m", 5, "PP41[2]_5"),
    ("p4m", 3, "PP39[2]_3"), ("p6", 1, "PP44[2]"),
    ("p6m", 1, "PP47[2]_1"), ("p6m", 2, "PP48A[2]_2"),
    ("p6m", 2, "PP48B[2]_2"), ("p6m", 2, "PP50[2]_2"),
)


PRIMITIVE_THREE: tuple[tuple[str, int, str], ...] = tuple(
    (parent, index, label)
    for parent, prefix in (
        ("p1", "PP1"), ("pg", "PP2"), ("pm", "PP3"), ("cm", "PP5"),
        ("p2", "PP7"), ("pgg", "PP9"), ("pmg", "PP11"),
        ("pmm", "PP14"), ("cmm", "PP17"), ("p3", "PP21"),
        ("p31m", "PP23"), ("p3m1", "PP27"), ("p6", "PP42"),
        ("p6m", "PP46"),
    )
    for index in range(1, len(THREE_COLOUR_TYPES[parent]) + 1)
    for label in (f"{prefix}[3]" + (f"_{index}" if len(THREE_COLOUR_TYPES[parent]) > 1 else ""),)
)


NONPRIMITIVE_THREE: tuple[tuple[str, int, str], ...] = (
    ("pm", 1, "PP4[3]_1"), ("pm", 2, "PP4[3]_2"),
    ("cm", 1, "PP6[3]_1"), ("cm", 2, "PP6[3]_2"),
    ("p2", 1, "PP8[3]"), ("pgg", 1, "PP10[3]"),
    ("pmg", 1, "PP12[3]_1"), ("pmg", 1, "PP13[3]_1"),
    ("pmg", 2, "PP12[3]_2"), ("pmg", 2, "PP13[3]_2"),
    ("pmm", 1, "PP15[3]"), ("pmm", 1, "PP15[3]*"), ("pmm", 1, "PP16[3]"),
    ("cmm", 1, "PP18[3]"), ("cmm", 1, "PP19[3]"),
    ("cmm", 1, "PP19[3]*"), ("cmm", 1, "PP20[3]"),
    ("p3", 2, "PP22[3]_2"),
    ("p31m", 1, "PP25[3]_1"), ("p31m", 2, "PP25[3]_2"), ("p31m", 2, "PP26[3]_2"),
    ("p3m1", 1, "PP28[3]_1"), ("p3m1", 2, "PP28[3]_2"), ("p3m1", 2, "PP29[3]_2"),
    ("p6", 1, "PP43[3]_1"), ("p6", 2, "PP43[3]_2"), ("p6", 2, "PP45[3]_2"),
    ("p6m", 1, "PP47[3]_1"), ("p6m", 1, "PP48A[3]_1"),
    ("p6m", 1, "PP48B[3]_1"), ("p6m", 1, "PP49[3]_1"),
    ("p6m", 2, "PP47[3]_2"), ("p6m", 2, "PP48A[3]_2"),
    ("p6m", 2, "PP48B[3]_2"), ("p6m", 2, "PP49[3]_2"),
    ("p6m", 2, "PP51[3]_2"),
)


SOURCE_PAGE_BLOCKS = {
    (2, True): ((408, 3), (409, 9), (410, 9), (411, 9), (412, 9), (413, 7)),
    (2, False): ((426, 6), (427, 9), (428, 9), (429, 9), (430, 9)),
    (3, True): ((414, 6), (415, 9), (416, 8)),
    (3, False): ((431, 6), (432, 9), (433, 9), (434, 9), (435, 3)),
}


def source_pages(colours: int, primitive: bool) -> tuple[int, ...]:
    return tuple(
        page
        for page, count in SOURCE_PAGE_BLOCKS[(colours, primitive)]
        for _ in range(count)
    )


ORIENTED_FORMS = {
    "333³/◦": (
        "Two opposite cyclic orientations (the P3₁/P3₂ clockwork pair) define one plane colour type after colour relabelling."
    ),
    "632³/2222": (
        "Two opposite cyclic orientations (the P6₂/P6₄ clockwork pair) define one plane colour type after colour relabelling."
    ),
}


def slug(text: str) -> str:
    replacements = {
        "◦": "o", "×": "x", "*": "s", "³": "3", "/": "-",
        " ": "-", "(": "", ")": "", "[": "", "]": "", "_": "-",
    }
    out = "".join(replacements.get(ch, ch.lower()) for ch in text)
    return "-".join(filter(None, out.split("-")))


def legacy_group_symbol(hm: str, colours: int, index: int, count: int) -> str:
    suffix = f"_{index}" if count > 1 else ""
    return f"{hm}[{colours}]{suffix}"


def kernel_from_notation(notation: str) -> str:
    return notation.split("//", 1)[-1].split("/", 1)[-1].split(" ", 1)[0]


def build_groups() -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for wallpaper in WALLPAPERS:
        parent = wallpaper["id"]
        one_id = f"cg-{parent}-1-1"
        groups.append({
            "id": one_id,
            "wallpaper_id": parent,
            "number_of_colours": 1,
            "index_within_parent": 1,
            "chaim_notation": wallpaper["orbifold"],
            "chaim_short_signature": wallpaper["orbifold"],
            "gs_symbol": wallpaper["hm"],
            "colour_image": "C1",
            "regular": True,
            "colour_stabilizer_H": wallpaper["orbifold"],
            "all_colours_kernel_K": wallpaper["orbifold"],
            "notation_variant": None,
            "related_forms": [],
            "sources": [
                {"work": "Tilings and Patterns", "chapter": 5, "note": "ordinary one-colour PP baseline"},
            ],
        })
        for colours, mapping in ((2, TWO_COLOUR_TYPES), (3, THREE_COLOUR_TYPES)):
            entries = mapping[parent]
            for index, notation in enumerate(entries, start=1):
                group_id = f"cg-{parent}-{colours}-{index}"
                regular = colours == 2 or "//" not in notation
                display_notation = notation
                variant = None
                if notation.endswith(" (1)") or notation.endswith(" (2)"):
                    variant = notation[-2]
                    display_notation = notation[:-4]
                short_signatures = (
                    TWO_FOLD_SHORT_SIGNATURE_BY_TYPE
                    if colours == 2
                    else THREE_FOLD_SHORT_SIGNATURE_BY_TYPE
                )
                try:
                    short_signature = short_signatures[notation]
                except KeyError as error:
                    raise ValueError(
                        f"missing Chaim short signature for {notation}"
                    ) from error
                groups.append({
                    "id": group_id,
                    "wallpaper_id": parent,
                    "number_of_colours": colours,
                    "index_within_parent": index,
                    "chaim_notation": display_notation,
                    "chaim_short_signature": short_signature,
                    "gs_symbol": legacy_group_symbol(wallpaper["hm"], colours, index, len(entries)),
                    "colour_image": "C2" if colours == 2 else ("C3" if regular else "S3"),
                    "regular": regular,
                    "colour_stabilizer_H": (
                        kernel_from_notation(display_notation)
                        if regular
                        else NONREGULAR_THREE_STABILIZER[display_notation]
                    ),
                    "all_colours_kernel_K": kernel_from_notation(display_notation),
                    "notation_variant": variant,
                    "related_forms": [ORIENTED_FORMS[display_notation]] if display_notation in ORIENTED_FORMS else [],
                    "sources": [
                        {
                            "work": "Tilings and Patterns",
                            "table": "8.2.2" if colours == 2 else "8.2.3",
                            "printed_pages": "417–418" if colours == 2 else "419",
                        },
                        {
                            "work": "The Symmetries of Things",
                            "table": "11.1" if colours == 2 else "12.1",
                            "printed_pages": "140–141" if colours == 2 else "156",
                        },
                    ],
                })
    return groups


def pattern_id(colours: int, ordinal: int, symbol: str) -> str:
    return f"cp-{colours}-{ordinal:03d}-{slug(symbol)}"


def underlying_symbol(colour_symbol: str) -> str:
    # The coloured label is the canonical identifier.  The PP stem is a
    # concise perfect-representative label; it is not asserted to cover every
    # non-perfect realization of the same colour-pattern type.
    return colour_symbol.split("[", 1)[0].removesuffix("A").removesuffix("B")


def build_patterns(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group_lookup = {
        gkey(group["wallpaper_id"], group["number_of_colours"], group["index_within_parent"]): group
        for group in groups
    }
    patterns: list[dict[str, Any]] = []

    # The ordinary PP1--PP51 baseline is shown muted and last in every family.
    ordinary_ordinal = 0
    for wallpaper in WALLPAPERS:
        group = group_lookup[gkey(wallpaper["id"], 1, 1)]
        for index, symbol in enumerate(wallpaper["ordinary"]):
            ordinary_ordinal += 1
            patterns.append({
                "id": pattern_id(1, ordinary_ordinal, symbol),
                "colour_group_id": group["id"],
                "wallpaper_id": wallpaper["id"],
                "number_of_colours": 1,
                "gs_pattern_type": symbol,
                "underlying_pattern_type": symbol,
                "underlying_pattern_is_primitive": index == 0,
                "representative_is_perfect": True,
                "source": {"work": "Tilings and Patterns", "chapter": 5},
            })

    for colours, primitive_rows, nonprimitive_rows, source_primitive, source_nonprimitive in (
        (2, PRIMITIVE_TWO, NONPRIMITIVE_TWO, "Figure 8.2.2, pp. 408–413", "Figure 8.3.5, pp. 426–430"),
        (3, PRIMITIVE_THREE, NONPRIMITIVE_THREE, "Figure 8.2.3, pp. 414–416", "Figure 8.3.6, pp. 431–435"),
    ):
        ordinal = 0
        for primitive, rows, source in (
            (True, primitive_rows, source_primitive),
            (False, nonprimitive_rows, source_nonprimitive),
        ):
            pages = source_pages(colours, primitive)
            if len(pages) != len(rows):
                raise ValueError(
                    f"source-page census mismatch for {colours} colours, "
                    f"primitive={primitive}: {len(pages)} != {len(rows)}"
                )
            for (parent, group_index, symbol), printed_page in zip(rows, pages):
                ordinal += 1
                group = group_lookup[gkey(parent, colours, group_index)]
                record = {
                    "id": pattern_id(colours, ordinal, symbol),
                    "colour_group_id": group["id"],
                    "wallpaper_id": parent,
                    "number_of_colours": colours,
                    "gs_pattern_type": symbol,
                    "underlying_pattern_type": underlying_symbol(symbol),
                    "underlying_pattern_is_primitive": primitive,
                    "representative_is_perfect": True,
                    "source": {
                        "work": "Tilings and Patterns",
                        "chapter": 8,
                        "figure": source,
                        "printed_page": printed_page,
                    },
                }
                if colours == 3 and primitive and parent == "p31m" and group_index == 2:
                    record["source_note"] = (
                        "Figure 8.2.3 prints the colour-group subscript 3 here; "
                        "Table 8.2.3's two-group census uses the canonical subscript 2."
                    )
                patterns.append(record)
    return patterns


def validate_payload(payload: dict[str, Any]) -> None:
    wallpapers = payload["wallpaper_groups"]
    groups = payload["colour_groups"]
    patterns = payload["pattern_types"]
    if len(wallpapers) != 17:
        raise ValueError(f"expected 17 wallpaper groups, got {len(wallpapers)}")
    group_counts = Counter(g["number_of_colours"] for g in groups)
    if group_counts != Counter({1: 17, 2: 46, 3: 23}):
        raise ValueError(f"bad colour-group census: {group_counts}")
    if any(not group.get("chaim_short_signature") for group in groups):
        raise ValueError("every colour group needs a Chaim short signature")
    pattern_counts = Counter(p["number_of_colours"] for p in patterns)
    if pattern_counts != Counter({1: 51, 2: 88, 3: 59}):
        raise ValueError(f"bad pattern-type census: {pattern_counts}")
    primitive_counts = Counter(
        p["number_of_colours"] for p in patterns if p["underlying_pattern_is_primitive"]
    )
    if primitive_counts != Counter({1: 17, 2: 46, 3: 23}):
        raise ValueError(f"bad primitive census: {primitive_counts}")
    image_counts = Counter(g["colour_image"] for g in groups if g["number_of_colours"] == 3)
    if image_counts != Counter({"C3": 8, "S3": 15}):
        raise ValueError(f"bad three-colour action census: {image_counts}")
    wallpaper_orbifolds = {wallpaper["orbifold"] for wallpaper in wallpapers}
    if any(group["colour_stabilizer_H"] not in wallpaper_orbifolds for group in groups):
        raise ValueError("every chosen-colour stabilizer H must be a wallpaper orbifold")
    if any(group["all_colours_kernel_K"] not in wallpaper_orbifolds for group in groups):
        raise ValueError("every all-colours kernel K must be a wallpaper orbifold")
    nonregular = {
        group["chaim_notation"]: group["colour_stabilizer_H"]
        for group in groups
        if group["number_of_colours"] == 3 and not group["regular"]
    }
    if nonregular != NONREGULAR_THREE_STABILIZER:
        raise ValueError(f"bad nonregular three-colour stabilizers: {nonregular}")
    wallpaper_ids = {w["id"] for w in wallpapers}
    group_ids = {g["id"] for g in groups}
    pattern_ids = {p["id"] for p in patterns}
    if len(group_ids) != len(groups) or len(pattern_ids) != len(patterns):
        raise ValueError("duplicate group or pattern ID")
    for group in groups:
        if group["wallpaper_id"] not in wallpaper_ids:
            raise ValueError(f"orphan group: {group['id']}")
    group_by_id = {g["id"]: g for g in groups}
    for pattern in patterns:
        group = group_by_id.get(pattern["colour_group_id"])
        if group is None or group["wallpaper_id"] != pattern["wallpaper_id"]:
            raise ValueError(f"orphan or cross-family pattern: {pattern['id']}")
        if group["number_of_colours"] != pattern["number_of_colours"]:
            raise ValueError(f"colour mismatch: {pattern['id']}")

    expected_by_parent = {
        "p1": (1, 1), "p2": (2, 1), "pm": (5, 2), "pg": (2, 2),
        "cm": (3, 2), "pmm": (5, 1), "pmg": (5, 2), "pgg": (2, 1),
        "cmm": (5, 1), "p4": (2, 0), "p4m": (5, 0), "p4g": (3, 0),
        "p3": (0, 2), "p3m1": (1, 2), "p31m": (1, 2), "p6": (1, 2),
        "p6m": (3, 2),
    }
    for parent, expected in expected_by_parent.items():
        got = tuple(
            sum(g["wallpaper_id"] == parent and g["number_of_colours"] == k for g in groups)
            for k in (2, 3)
        )
        if got != expected:
            raise ValueError(f"bad parent census for {parent}: {got} != {expected}")


def build_payload() -> dict[str, Any]:
    groups = build_groups()
    patterns = build_patterns(groups)
    payload = {
        "meta": {
            "title": "Periodic colour-pattern catalog",
            "scope": "perfect periodic colour-pattern representatives with one, two, or three colours",
            "warning": "The finite classification is of colour-pattern types; literal motif geometries have infinitely many realizations.",
            "counts": {
                "wallpaper_groups": 17,
                "colour_groups": {"1": 17, "2": 46, "3": 23, "total": 86},
                "pattern_types": {"1": 51, "2": 88, "3": 59, "total": 198, "nontrivially_coloured": 147},
                "three_colour_actions": {"C3_regular": 8, "S3_nonregular": 15},
            },
            "definitions": {
                "pattern": "P*=(P,chi): a periodic monomotif pattern P together with a colour assignment chi on motif copies.",
                "chromatic": "The colour-symmetry group acts transitively on the colours.",
                "perfect": "Every symmetry of the uncoloured pattern induces a colour permutation.",
                "colour_pattern_type": "After colour relabelling: the same colour group, coloured-motif stabilizer/induced group, and coloured-motif-transitive subgroups.",
            },
            "sources": [
                {"work": "Tilings and Patterns", "authors": "Branko Grünbaum and G. C. Shephard", "chapter": 8, "printed_pages": "401–470"},
                {"work": "The Symmetries of Things", "authors": "John H. Conway, Heidi Burgiel, and Chaim Goodman-Strauss", "tables": "11.1 and 12.1"},
                {
                    "work": "Dichromatic Dances",
                    "author": "Karl Schaffer",
                    "year": 2017,
                    "figure": "10",
                    "role": "independent two-colour index/orbifold crosswalk",
                    "url": "https://archive.bridgesmathart.org/2017/bridges2017-291.pdf",
                },
                {
                    "work": "Coloured Plane Groups",
                    "authors": "K. Jarratt and R. L. E. Schwarzenberger",
                    "year": 1980,
                    "role": "index-3 chosen-colour subgroups and three-colour kernel cross-check",
                    "url": "https://www.york.ac.uk/depts/maths/histstat/symmetry/coloured.pdf",
                },
                {
                    "work": "The Symmetries of Things: Errors",
                    "role": "official errata consulted for Table 12.1",
                    "url": "https://www.mit.edu/~hlb/Symmetries_of_Things/SoTerrors.html",
                },
            ],
        },
        "wallpaper_groups": [dict(wallpaper) for wallpaper in WALLPAPERS],
        "colour_groups": groups,
        "pattern_types": patterns,
    }
    decorate_payload(payload)
    validate_payload(payload)
    validate_excerpt_metadata(payload)
    return payload


def palette_html(colours: int) -> str:
    palette = ("#b8b9b7",) if colours == 1 else PALETTE[:colours]
    return "".join(
        f'<span style="--swatch:{escape(colour)}"></span>' for colour in palette
    )


def typeset_symbol(symbol: str) -> str:
    subscripts = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    symbol = re.sub(r"_(\d+)", lambda match: match.group(1).translate(subscripts), symbol)
    return symbol.replace("*", "∗")


SUPERSCRIPT_TO_ASCII = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def short_signature_html(signature: str) -> str:
    """Render Chaim's raised orders or named permutations semantically."""

    output: list[str] = []
    digit_run: list[str] = []

    def flush_digits() -> None:
        if digit_run:
            output.append(f"<sup>{''.join(digit_run)}</sup>")
            digit_run.clear()

    index = 0
    while index < len(signature):
        character = signature[index]
        if character in "⁰¹²³⁴⁵⁶⁷⁸⁹":
            digit_run.append(character.translate(SUPERSCRIPT_TO_ASCII))
            index += 1
            continue
        flush_digits()
        if character == "^":
            if index + 1 >= len(signature) or signature[index + 1] != "(":
                raise ValueError(f"bad named superscript in {signature!r}")
            end = signature.find(")", index + 2)
            if end < 0:
                raise ValueError(f"unterminated named superscript in {signature!r}")
            output.append(f"<sup>{escape(signature[index + 1:end + 1])}</sup>")
            index = end + 1
            continue
        if character == "*":
            output.append('<span class="orbifold-star">∗</span>')
        else:
            output.append(escape(character))
        index += 1
    flush_digits()
    return "".join(output)


def short_signature_text(signature: str) -> str:
    """Plain-text form for an accessible tab label."""

    return signature.replace("^", "").replace("*", "∗")


def group_tab_html(group: dict[str, Any], *, selected: bool) -> str:
    full_type = group["chaim_notation"]
    if group["notation_variant"]:
        full_type += f" form {group['notation_variant']}"
    aria_label = (
        f"Chaim short colour signature {short_signature_text(group['chaim_short_signature'])}; "
        f"colour type {full_type}; Grünbaum–Shephard {group['gs_symbol']}"
    )
    return (
        f'<a class="colour-group-tab{(" is-trivial" if group["number_of_colours"] == 1 else "")}" '
        f'id="tab-{escape(group["id"])}" href="#{escape(group["id"])}" role="tab" '
        f'aria-controls="panel-{escape(group["id"])}" '
        f'aria-label="{escape(aria_label)}" '
        f'aria-selected="{str(selected).lower()}" tabindex="{0 if selected else -1}" '
        f'data-group-id="{escape(group["id"])}">'
        f'<span class="tab-name tab-signature" aria-hidden="true">{short_signature_html(group["chaim_short_signature"])}</span>'
        f'<span class="tab-palette" aria-hidden="true">{palette_html(group["number_of_colours"])}</span>'
        '</a>'
    )


def build_html(payload: dict[str, Any]) -> str:
    groups_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pattern_counts_by_group = Counter(p["colour_group_id"] for p in payload["pattern_types"])
    for group in payload["colour_groups"]:
        groups_by_parent[group["wallpaper_id"]].append(group)
    for entries in groups_by_parent.values():
        entries.sort(key=lambda g: (g["number_of_colours"] == 1, g["number_of_colours"], g["index_within_parent"]))

    directory_rows: list[str] = []
    family_sections: list[str] = []
    for wallpaper in payload["wallpaper_groups"]:
        entries = groups_by_parent[wallpaper["id"]]
        nontrivial_groups = [g for g in entries if g["number_of_colours"] > 1]
        patterns_here = sum(pattern_counts_by_group[g["id"]] for g in entries if g["number_of_colours"] > 1)
        directory_rows.append(
            f'<a class="directory-family" href="#wallpaper-{escape(wallpaper["id"])}" data-directory-wallpaper-id="{escape(wallpaper["id"])}">'
            f'<strong>{escape(typeset_symbol(wallpaper["orbifold"]))}</strong>'
            f'<span>{len(nontrivial_groups)} nontrivial groups · {patterns_here} coloured types</span></a>'
        )
        tabs = "\n".join(
            group_tab_html(group, selected=index == 0)
            for index, group in enumerate(entries)
        )
        family_sections.append(f'''    <section class="wallpaper-family" id="wallpaper-{escape(wallpaper["id"])}" data-wallpaper-id="{escape(wallpaper["id"])}" aria-labelledby="wallpaper-{escape(wallpaper["id"])}-title">
      <header class="family-header">
        <h2 id="wallpaper-{escape(wallpaper["id"])}-title"><span class="family-orbifold">{escape(typeset_symbol(wallpaper["orbifold"]))}</span><span class="family-hm">{escape(wallpaper["hm"])}</span></h2>
        <p>{escape(wallpaper["summary"])}</p>
      </header>
      <nav class="colour-group-tabs" role="tablist" aria-label="Colour groups over {escape(wallpaper["orbifold"])}">
{tabs}
      </nav>
      <div class="colour-group-panel" data-group-panel aria-live="polite"></div>
    </section>''')

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A 17-family catalog of the 46 two-colour and 23 three-colour plane groups, with all 147 nontrivially coloured Grünbaum–Shephard periodic colour-pattern types.">
  <meta name="theme-color" content="#ffffff">
  <title>Periodic colour-pattern catalog</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="site-controls-v2.css">
  <link rel="stylesheet" href="color-pattern-catalog.css?v=merged-entry">
  <script src="color-pattern-catalog.js?v=merged-entry" defer></script>
</head>
<body>
  <a class="skip-link" href="#pattern-atlas">Skip to pattern catalog</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="site-name" href="./">Spacetime-group visualizations</a>
      <nav aria-label="Project links">
        <a href="./">Gallery</a>
        <a href="future-directions.html">Colours</a>
        <a href="color-pattern-catalog.html" aria-current="page">Patterns</a>
        <a href="clockwork-coloring-correspondence.html">Clockwork</a>
        <a href="space-group-correspondence.html">Space groups</a>
        <a href="docs/orbifold_notation.html">Notation</a>
        <a href="data/color-pattern-catalog.json">Data</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>

  <main class="pattern-catalog-page">
    <section class="catalog-directory" aria-labelledby="page-title">
      <p class="overline">17 wallpaper groups · 86 colour groups · 198 periodic pattern types</p>
      <h1 id="page-title">Periodic colour-pattern catalog</h1>
      <div class="census" aria-label="Catalog counts">
        <p><strong>51</strong><span>one-colour PP types</span></p>
        <p><strong>88</strong><span>two-colour types · 46 groups</span></p>
        <p><strong>59</strong><span>three-colour types · 23 groups</span></p>
        <p><strong>147</strong><span>nontrivially coloured types</span></p>
      </div>
      <p class="scope-note"><strong>Catalogued object:</strong> a Grünbaum–Shephard colour-pattern type, represented perfectly. Literal motif geometries are infinite; two representatives have the same type precisely when, after colour relabelling, they have the same colour group, coloured-motif stabilizer/induced group, and coloured-motif-transitive subgroups.</p>
      <div class="filter-bar" role="group" aria-label="Filter by number of colours">
        <button type="button" class="is-active" data-colour-filter="all" aria-pressed="true">All</button>
        <button type="button" data-colour-filter="2" aria-pressed="false">2 colours</button>
        <button type="button" data-colour-filter="3" aria-pressed="false">3 colours</button>
        <button type="button" data-colour-filter="1" aria-pressed="false">1 colour</button>
      </div>
      <nav class="directory-grid" aria-label="Wallpaper group sections">
        {''.join(directory_rows)}
      </nav>
    </section>

    <div class="pattern-atlas" id="pattern-atlas">
{chr(10).join(family_sections)}
    </div>
    <noscript><p class="noscript-note">JavaScript is required for the nested pattern selector. The complete classification is available in <a href="data/color-pattern-catalog.json">JSON</a>.</p></noscript>
  </main>
</body>
</html>
'''


def expected_outputs() -> dict[Path, bytes]:
    payload = build_payload()
    return {
        DATA: (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        PAGE: build_html(payload).encode("utf-8"),
    }


def check_outputs(outputs: dict[Path, bytes]) -> list[str]:
    errors: list[str] = []
    for path, expected in outputs.items():
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
        elif path.read_bytes() != expected:
            errors.append(f"stale {path.relative_to(ROOT)}")
    return errors


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated outputs are stale")
    args = parser.parse_args(list(argv) if argv is not None else None)
    outputs = expected_outputs()
    if args.check:
        errors = check_outputs(outputs)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("colour-pattern catalog outputs are current")
        return 0
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
