"""Annotated source-excerpt metadata for the colour-pattern catalog.

The catalog has two independent evidence layers:

* Conway--Burgiel--Goodman-Strauss Tables 11.1 and 12.1, with the
  *short colour signature* (or its deliberately blank cell) outlined;
* Gruenbaum--Shephard Figures 8.2.2, 8.2.3, 8.3.5, and 8.3.6, with the
  printed PP pattern-type label outlined.

Coordinates are in source-PDF points.  The source PDFs stay local; only the
small, watermarked WebP excerpts generated from these specifications ship.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from tos_book_excerpt_specs import BOOK_EXCERPTS


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "color-pattern-excerpts"
SOT_BOOK_URL = "https://books.google.com/books?id=EtQCk0TNafsC&pg=PA{page}"


# Table 11.1 row baselines.  The first page contains 31 types; the continuation
# contains the remaining 15, including the two inequivalent **/** forms.
SOT_TWO_ROW: dict[str, tuple[int, float, float]] = {
    "*632/3*3": (140, 166.0, 18),
    "*632/*333": (140, 177.0, 18),
    "*632/632": (140, 188.0, 18),
    "632/333": (140, 199.5, 18),
    "*442/*442": (140, 222.0, 18),
    "*442/4*2": (140, 233.0, 18),
    "*442/*2222": (140, 244.0, 18),
    "*442/2*22": (140, 255.0, 18),
    "*442/442": (140, 266.0, 18),
    "4*2/442": (140, 277.0, 18),
    "4*2/2*22": (140, 288.0, 18),
    "4*2/22×": (140, 299.0, 18),
    "442/442": (140, 310.0, 18),
    "442/2222": (140, 321.0, 18),
    "*333/333": (140, 332.5, 18),
    "3*3/333": (140, 355.0, 18),
    "*2222/*2222": (140, 399.5, 18),
    "*2222/2*22": (140, 410.5, 18),
    "*2222/**": (140, 421.5, 18),
    "*2222/22*": (140, 432.5, 18),
    "*2222/2222": (140, 443.5, 18),
    "2*22/22*": (140, 454.5, 18),
    "2*22/2222": (140, 465.5, 18),
    "2*22/*2222": (140, 476.5, 18),
    "2*22/*×": (140, 487.5, 18),
    "2*22/22×": (140, 498.5, 18),
    "22*/2222": (140, 509.5, 18),
    "22*/22*": (140, 520.5, 18),
    "22*/22×": (140, 531.5, 18),
    "22*/**": (140, 542.5, 18),
    "22*/××": (140, 553.5, 18),
    "22×/2222": (141, 166.0, 18),
    "22×/××": (141, 177.0, 18),
    "2222/2222": (141, 188.5, 18),
    "2222/◦": (141, 199.5, 18),
    "**/◦": (141, 210.5, 18),
    "**/** (2)": (141, 221.5, 18),
    "**/** (1)": (141, 232.5, 18),
    "**/*×": (141, 243.5, 18),
    "**/××": (141, 254.5, 18),
    "*×/**": (141, 265.5, 18),
    "*×/××": (141, 276.5, 18),
    "*×/◦": (141, 287.5, 18),
    "××/××": (141, 298.5, 27),
    "××/◦": (141, 320.5, 18),
    "◦/◦": (141, 331.5, 26),
}


# Table 12.1 row baselines.  The 632^3//333 short-signature cell is blank in
# print; outlining the empty cell records that omission rather than inventing
# a signature for the source.
SOT_THREE_ROW: dict[str, tuple[float, float]] = {
    "*632³//*333": (159.5, 18),
    "*632³//2222": (172.0, 18),
    "632³/2222": (184.5, 18),
    "632³//333": (197.0, 18),
    "*333³//◦": (210.5, 18),
    "*333³//333": (223.0, 18),
    "3*3³/◦": (236.0, 18),
    "3*3³//*333": (248.5, 18),
    "333³/◦": (261.0, 18),
    "333³/333": (274.0, 18),
    "*2222³//**": (287.5, 18),
    "2*22³//**": (300.5, 18),
    "22*³//◦": (313.5, 18),
    "22*³//**": (326.0, 18),
    "22×³//××": (339.0, 18),
    "2222³//◦": (352.0, 18),
    "**³/**": (365.0, 18),
    "**³//◦": (377.5, 18),
    "*×³/*×": (390.5, 18),
    "*×³//◦": (403.5, 18),
    "××³/××": (416.5, 18),
    "××³//◦": (429.0, 18),
    "◦³/◦": (438.0, 24),
}


def _grid_row(
    label_xs: tuple[float, ...],
    label_y: float,
    *,
    crop_xs: tuple[float, ...] | None = None,
    crop_widths: tuple[float, ...] | None = None,
) -> list[dict[str, tuple[float, float, float, float]]]:
    count = len(label_xs)
    if crop_xs is None:
        crop_xs = (35.0, 190.0, 345.0)[:count]
    if crop_widths is None:
        crop_widths = (178.0, 178.0, 188.0)[:count]
    crop_y = max(30.0, label_y - 176.0)
    crop_height = min(610.0 - crop_y, 202.0)
    return [
        {
            "crop": (crop_x, crop_y, crop_width, crop_height),
            "highlight": (label_x - 5.0, label_y - 4.0, 76.0, 19.0),
        }
        for label_x, crop_x, crop_width in zip(label_xs, crop_xs, crop_widths)
    ]


def _rows(*rows: list[dict[str, tuple[float, float, float, float]]]) -> tuple[dict[str, Any], ...]:
    return tuple(slot for row in rows for slot in row)


# Slots are in the exact reading order of the corresponding figure pages.
GS_PAGE_SLOTS: dict[int, tuple[dict[str, Any], ...]] = {
    408: _rows(_grid_row((170, 322, 474), 548)),
    409: _rows(*(_grid_row((136, 292, 449), y) for y in (190, 383, 579))),
    410: _rows(*(_grid_row((165, 322, 478), y) for y in (190, 373, 556))),
    411: _rows(*(_grid_row((122, 278, 435), y) for y in (180, 374, 576))),
    412: _rows(*(_grid_row((160, 317, 474), y) for y in (198, 378, 558))),
    413: _rows(
        _grid_row((130, 284, 438), 195),
        _grid_row((130, 284, 438), 385),
        _grid_row((280,), 580, crop_xs=(145,), crop_widths=(270,)),
    ),
    414: _rows(*(_grid_row((130, 285, 443), y) for y in (370, 550))),
    415: _rows(*(_grid_row((128, 285, 440), y) for y in (195, 382, 568))),
    416: _rows(
        _grid_row((160, 317, 474), 188),
        _grid_row((160, 317, 474), 370),
        _grid_row((245, 403), 558, crop_xs=(90, 245), crop_widths=(235, 250)),
    ),
    426: _rows(*(_grid_row((150, 307, 464), y) for y in (375, 550))),
    427: _rows(*(_grid_row((120, 277, 435), y) for y in (190, 382, 570))),
    428: _rows(*(_grid_row((150, 305, 460), y) for y in (180, 370, 558))),
    429: _rows(*(_grid_row((130, 285, 438), y) for y in (175, 370, 562))),
    430: _rows(*(_grid_row((145, 300, 455), y) for y in (180, 360, 548))),
    431: _rows(*(_grid_row((127, 285, 442), y) for y in (350, 540))),
    432: _rows(*(_grid_row((155, 312, 470), y) for y in (190, 380, 565))),
    433: _rows(*(_grid_row((120, 278, 435), y) for y in (198, 385, 570))),
    434: _rows(*(_grid_row((165, 322, 478), y) for y in (200, 375, 560))),
    435: _rows(_grid_row((165, 322, 478), 200)),
}


def _raw_colour_type(group: dict[str, Any]) -> str:
    notation = group["chaim_notation"]
    if group.get("notation_variant"):
        notation += f" ({group['notation_variant']})"
    return notation


def _group_excerpt(group: dict[str, Any]) -> dict[str, Any]:
    raw_type = _raw_colour_type(group)
    colours = group["number_of_colours"]
    if colours == 1:
        source = BOOK_EXCERPTS[f"p40::{raw_type}"]
        return {
            "work": "The Symmetries of Things",
            "image": source["image"],
            "title": f"Plane-group signature {raw_type}",
            "context": source["context"],
            "alt": source["alt"],
            "printed_page": 40,
            "source_url": SOT_BOOK_URL.format(page=40),
        }

    if colours == 2:
        page, _y, _height = SOT_TWO_ROW[raw_type]
        context = (
            f"Complete Table 11.1 on printed pp. 140-141; the outline marks "
            f"the printed short-signature cell for {raw_type}."
        )
    else:
        page = 156
        context = (
            f"Complete Table 12.1 on printed p. 156; the outline marks the "
            f"printed short-signature cell for {raw_type}."
        )
        if raw_type == "632³//333":
            context += " The book leaves this short-signature cell blank."
    return {
        "work": "The Symmetries of Things",
        "image": f"output/color-pattern-excerpts/tos-{group['id']}.webp",
        "title": f"Short colour signature for {raw_type}",
        "context": context,
        "alt": f"Annotated source table with the short colour signature for {raw_type} outlined.",
        "printed_page": page,
        "source_url": SOT_BOOK_URL.format(page=page),
    }


def _pattern_excerpt(pattern: dict[str, Any], *, source_symbol: str | None = None) -> dict[str, Any]:
    displayed = pattern["gs_pattern_type"]
    source_symbol = source_symbol or displayed
    page = pattern["source"]["printed_page"]
    context = (
        f"Grünbaum-Shephard Figure {pattern['source']['figure'].split(',')[0].replace('Figure ', '')} "
        f"on printed p. {page}; the outline marks the printed pattern-type label {source_symbol}."
    )
    if displayed != source_symbol:
        context += f" This Chapter 8 occurrence supplies the same PP stem as the one-colour type {displayed}."
    return {
        "work": "Tilings and Patterns",
        "image": f"output/color-pattern-excerpts/gs-{pattern['id']}.webp",
        "title": f"Pattern type {displayed}",
        "context": context,
        "alt": f"Annotated Grünbaum-Shephard figure with pattern-type label {source_symbol} outlined.",
        "printed_page": page,
        "source_symbol": source_symbol,
    }


def decorate_payload(payload: dict[str, Any]) -> None:
    """Attach stable viewer metadata to every group and pattern record."""

    for group in payload["colour_groups"]:
        group["book_excerpt"] = _group_excerpt(group)

    coloured = [p for p in payload["pattern_types"] if p["number_of_colours"] > 1]
    page_offsets: defaultdict[int, int] = defaultdict(int)
    for pattern in coloured:
        page = pattern["source"]["printed_page"]
        slot = page_offsets[page]
        page_offsets[page] += 1
        pattern["book_figure_slot"] = slot
        pattern["book_excerpt"] = _pattern_excerpt(pattern)

    first_by_stem: dict[str, dict[str, Any]] = {}
    for pattern in coloured:
        first_by_stem.setdefault(pattern["underlying_pattern_type"], pattern)
    for pattern in payload["pattern_types"]:
        if pattern["number_of_colours"] != 1:
            continue
        source = first_by_stem[pattern["underlying_pattern_type"]]
        excerpt = _pattern_excerpt(source, source_symbol=source["gs_pattern_type"])
        excerpt["title"] = f"Pattern type {pattern['gs_pattern_type']}"
        excerpt["context"] += (
            f" The attached excerpt contains Chapter 8, not the Chapter 5 one-colour plates; "
            f"{source['gs_pattern_type']} is the printed occurrence of the same PP stem."
        )
        pattern["book_excerpt"] = excerpt


def build_excerpt_specs(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return specifications for all newly generated excerpt images."""

    specs: dict[str, dict[str, Any]] = {}
    for group in payload["colour_groups"]:
        if group["number_of_colours"] == 1:
            continue
        raw_type = _raw_colour_type(group)
        excerpt = group["book_excerpt"]
        if group["number_of_colours"] == 2:
            page, y, height = SOT_TWO_ROW[raw_type]
            highlight = (300.0, y, 137.0, height) if page == 140 else (225.0, y, 112.0, height)
            panels = (
                {"printed_page": 140, "pdf_page": 159, "crop": (198, 143, 324, 454)},
                {"printed_page": 141, "pdf_page": 160, "crop": (105, 140, 294, 225)},
            )
        else:
            page = 156
            y, height = SOT_THREE_ROW[raw_type]
            highlight = (332.0, y, 86.0, height)
            panels = ({"printed_page": 156, "pdf_page": 175, "crop": (228, 140, 262, 340)},)
        specs[excerpt["image"]] = {
            "kind": "sot",
            "printed_page": page,
            "pdf_page": page + 19,
            "highlight": highlight,
            "table_panels": panels,
            "footer": "THE SYMMETRIES OF THINGS",
        }

    for pattern in payload["pattern_types"]:
        if pattern["number_of_colours"] == 1:
            continue
        excerpt = pattern["book_excerpt"]
        page = pattern["source"]["printed_page"]
        slot = GS_PAGE_SLOTS[page][pattern["book_figure_slot"]]
        specs[excerpt["image"]] = {
            "kind": "gs",
            "printed_page": page,
            "pdf_page": page - 400,
            "crop": slot["crop"],
            "highlight": slot["highlight"],
            "footer": "GRÜNBAUM-SHEPHARD · TILINGS AND PATTERNS",
        }
    return deepcopy(specs)


def validate_excerpt_metadata(payload: dict[str, Any]) -> None:
    groups = payload["colour_groups"]
    patterns = payload["pattern_types"]
    if any("book_excerpt" not in record for record in (*groups, *patterns)):
        raise ValueError("every group and pattern needs book-excerpt metadata")
    if set(SOT_TWO_ROW) != {
        _raw_colour_type(group) for group in groups if group["number_of_colours"] == 2
    }:
        raise ValueError("Table 11.1 excerpt map does not match the two-colour census")
    if set(SOT_THREE_ROW) != {
        _raw_colour_type(group) for group in groups if group["number_of_colours"] == 3
    }:
        raise ValueError("Table 12.1 excerpt map does not match the three-colour census")
    expected_page_counts: defaultdict[int, int] = defaultdict(int)
    for pattern in patterns:
        if pattern["number_of_colours"] > 1:
            expected_page_counts[pattern["source"]["printed_page"]] += 1
    for page, slots in GS_PAGE_SLOTS.items():
        if expected_page_counts[page] != len(slots):
            raise ValueError(
                f"G&S p. {page} has {len(slots)} excerpt slots for "
                f"{expected_page_counts[page]} pattern types"
            )
