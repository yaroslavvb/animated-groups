from __future__ import annotations

from collections import Counter, defaultdict
from html import escape
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_clockwork_coloring_correspondence as correspondence  # noqa: E402
import generate_space_group_correspondence as space_correspondence  # noqa: E402
import generate_tos_book_excerpts as book_excerpts  # noqa: E402


BOOK_REPRESENTATIVE_FIXTURE = {
    "g7": 6,
    "g60": 2,
    "g63": 2,
    "g64": 4,
    "g65": 4,
    "g66": 2,
    "g67": 2,
    "g70": 2,
    "g73": 2,
    "g74": 4,
    "g98": 2,
    "g136": 2,
    "g138": 2,
}
BOOK_DISCREPANCY_FIXTURE = {"g234", "g244", "g245"}
COMPOSITE_EXTENSION_FIXTURE = {
    "g75", "g96", "g97", "g99", "g137", "g139", "g235", "g247", "g248"
}
FIXED_CLOCK_POWER_FIXTURE = {
    "g75": [0, 2, 1],
    "g96": [3, 3, 2],
    "g97": [1, 1, 2],
    "g99": [1, 3, 0],
    "g137": [1, 0],
    "g139": [1, 2],
    "g225": [2, 2, 2],
    "g226": [1, 1, 1],
    "g227": [1, 2, 0],
    "g234": [2, 0],
    "g244": [1, 2, 0],
    "g245": [2, 1, 0],
    "g247": [5, 4, 3],
    "g248": [1, 2, 3],
}
SOURCE_LABELING_FIXTURE = {
    "g75": ["A", "C", "B", "D"],
    "g96": ["A", "C", "D", "B"],
    "g97": ["A", "B", "D", "C"],
    "g99": ["A", "C", "B", "D"],
    "g137": ["A", "C", "B", "D"],
    "g139": ["A", "C", "B", "D"],
    "g225": ["A", "C", "B"],
    "g234": ["A", "C", "B"],
    "g235": ["A", "E", "D", "C", "B", "F"],
    "g245": ["A", "C", "B"],
    "g247": ["A", "C", "E", "F", "D", "B"],
    "g248": ["A", "B", "D", "F", "E", "C"],
}

MOTIF_CLEAR_LABEL_POSITION_FIXTURE = {
    "g59": {
        "α": (423.41, 212.83),
        "β": (404.6, 321.29),
        "Z": (374.0, 354.72),
    },
    "g63": {
        "α": (423.41, 212.83),
        "β": (404.6, 321.29),
        "Z": (374.0, 354.72),
    },
    "g75": {
        "α": (401.58, 240.62),
        "β": (402.44, 106.06),
        "Z": (374.0, 282.36),
    },
}

# Each compact item below the static plate is a distinct crystallographic
# symbol whose displayed generator, or its inverse, advances the fixed palette
# exactly one step.  Repeated equivalent centres intentionally collapse to one
# item.  Tuple fields are kind, symbol, source, direction, and visible label.
FORWARD_COLOUR_ACTION_FIXTURE = {
    "g6": (("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),),
    "g7": (("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),),
    "g9": (
        ("reflection", "plane-c", "direct", "", "colour reflection"),
        ("reflection", "plane-n", "direct", "", "colour glide reflection"),
    ),
    "g55": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g57": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g59": (("reflection", "plane-n", "direct", "", "colour glide reflection"),),
    "g60": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g61": (
        ("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),
        ("reflection", "plane-c", "direct", "", "colour reflection"),
    ),
    "g62": (("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),),
    "g63": (("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),),
    "g64": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g65": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g66": (("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),),
    "g67": (
        ("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),
        ("reflection", "plane-c", "direct", "", "colour reflection"),
    ),
    "g69": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g70": (
        ("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),
        ("reflection", "plane-c", "direct", "", "colour reflection"),
    ),
    "g71": (("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),),
    "g72": (
        ("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),
        ("reflection", "plane-c", "direct", "", "colour reflection"),
    ),
    "g73": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g74": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g75": (("reflection", "plane-d", "direct", "", "colour glide reflection"),),
    "g95": (("rotation", "rotation-4-2", "direct", "counterclockwise", "1/4 turn CCW · colour +1/2"),),
    "g96": (("rotation", "rotation-4-1", "inverse", "counterclockwise", "1/4 turn CCW"),),
    "g97": (("rotation", "rotation-4-3", "direct", "clockwise", "1/4 turn CW"),),
    "g98": (
        ("rotation", "rotation-4-2", "direct", "counterclockwise", "1/4 turn CCW · colour +1/2"),
        ("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),
    ),
    "g99": (
        ("rotation", "rotation-4-1", "direct", "counterclockwise", "1/4 turn CCW"),
        ("rotation", "rotation-4-3", "inverse", "clockwise", "1/4 turn CW"),
    ),
    "g129": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g130": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g131": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g133": (
        ("rotation", "rotation-4-2", "direct", "counterclockwise", "1/4 turn CCW · colour +1/2"),
        ("reflection", "plane-c", "direct", "", "colour reflection"),
    ),
    "g134": (("rotation", "rotation-4-2", "direct", "counterclockwise", "1/4 turn CCW · colour +1/2"),),
    "g135": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g136": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g137": (("rotation", "rotation-4-1", "direct", "counterclockwise", "1/4 turn CCW"),),
    "g138": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g139": (("rotation", "rotation-4-1", "direct", "counterclockwise", "1/4 turn CCW"),),
    "g225": (("rotation", "rotation-3-2", "inverse", "clockwise", "1/3 turn CW"),),
    "g226": (("rotation", "rotation-3-1", "direct", "counterclockwise", "1/3 turn CCW"),),
    "g227": (
        ("rotation", "rotation-3-1", "direct", "counterclockwise", "1/3 turn CCW"),
        ("rotation", "rotation-3-2", "inverse", "clockwise", "1/3 turn CW"),
    ),
    "g231": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g233": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g234": (("rotation", "rotation-3-1", "inverse", "counterclockwise", "1/3 turn CCW"),),
    "g244": (
        ("rotation", "rotation-6-2", "direct", "counterclockwise", "1/6 turn CCW · colour +1/3"),
        ("rotation", "rotation-3-2", "inverse", "clockwise", "1/3 turn CW"),
    ),
    "g245": (
        ("rotation", "rotation-6-4", "inverse", "clockwise", "1/6 turn CW · colour +1/3"),
        ("rotation", "rotation-3-1", "direct", "counterclockwise", "1/3 turn CCW"),
    ),
    "g246": (
        ("rotation", "rotation-6-3", "direct", "counterclockwise", "1/6 turn CCW · colour +1/2"),
        ("rotation", "rotation-2-1", "direct", "counterclockwise", "1/2 turn CCW"),
    ),
    "g247": (("rotation", "rotation-6-5", "inverse", "clockwise", "1/6 turn CW"),),
    "g248": (("rotation", "rotation-6-1", "direct", "counterclockwise", "1/6 turn CCW"),),
    "g269": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g270": (("reflection", "plane-c", "direct", "", "colour reflection"),),
    "g271": (("reflection", "plane-c", "direct", "", "colour reflection"),),
}
SUPERSCRIPT_ASCII = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

VIEWPORT_CENTER_FIXTURE = {
    "g8": (-0.1767766952965, 0.0),
    "g10": (0.17677675, 0.0),
    "g11": (0.3535535, 0.0),
    "g54": (0.25, 0.25),
    "g64": (0.25, -0.275567625),
    "g73": (-0.12451575, 0.25),
    "g128": (-0.35355339059327373, -0.14644660940672624),
    "g131": (-0.20710678118654754, 0.5),
    "g230": (-1 / 6, 0.28867513459473976),
    "g268": (-0.3943375672974532, 0.10566243270254677),
    "g269": (-0.10566243270263011, -0.39433756729736996),
}


def _polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    return abs(
        sum(
            left[0] * right[1] - right[0] * left[1]
            for left, right in zip(points, points[1:] + points[:1], strict=True)
        )
    ) / 2


def _clip_to_axis_half_plane(
    points: list[tuple[float, float]],
    normal: tuple[float, float],
    offset: float,
) -> list[tuple[float, float]]:
    """Clip a polygon to one side of an infinite projected generator axis."""

    clipped: list[tuple[float, float]] = []
    for start, end in zip(points, points[1:] + points[:1], strict=True):
        start_value = normal[0] * start[0] + normal[1] * start[1] - offset
        end_value = normal[0] * end[0] + normal[1] * end[1] - offset
        start_inside = start_value <= 1e-9
        end_inside = end_value <= 1e-9
        if start_inside:
            clipped.append(start)
        if start_inside != end_inside:
            interpolation = start_value / (start_value - end_value)
            clipped.append(
                (
                    start[0] + interpolation * (end[0] - start[0]),
                    start[1] + interpolation * (end[1] - start[1]),
                )
            )
    return clipped


def _projected_axis_metrics(
    group: dict[str, object],
    action: dict[str, object],
) -> tuple[float, tuple[tuple[float, float], tuple[float, float]]]:
    """Return the smaller area share and inset-clipped endpoints for one axis."""

    center = group["viewport_center"]
    render = group["render"]
    visualization = action["plate_visualization"]
    assert isinstance(center, list)
    assert isinstance(render, dict)
    assert isinstance(visualization, dict)
    axis_point = visualization["axis_point"]
    axis_direction = visualization["axis_direction"]
    assert isinstance(axis_point, list)
    assert isinstance(axis_direction, list)
    scale = correspondence._plate_cell_scale(render)
    point = (
        correspondence.IMAGE_WIDTH / 2
        + scale * (float(axis_point[0]) - float(center[0])),
        correspondence.IMAGE_HEIGHT / 2
        - scale * (float(axis_point[1]) - float(center[1])),
    )
    screen_direction = (
        float(axis_direction[0]),
        -float(axis_direction[1]),
    )
    direction_length = math.hypot(*screen_direction)
    unit = (
        screen_direction[0] / direction_length,
        screen_direction[1] / direction_length,
    )
    normal = (-unit[1], unit[0])
    offset = normal[0] * point[0] + normal[1] * point[1]
    rectangle = [
        (0.0, 0.0),
        (float(correspondence.IMAGE_WIDTH), 0.0),
        (
            float(correspondence.IMAGE_WIDTH),
            float(correspondence.IMAGE_HEIGHT),
        ),
        (0.0, float(correspondence.IMAGE_HEIGHT)),
    ]
    one_side = _polygon_area(
        _clip_to_axis_half_plane(rectangle, normal, offset)
    )
    total = correspondence.IMAGE_WIDTH * correspondence.IMAGE_HEIGHT
    smaller_share = min(one_side, total - one_side) / total

    lower = -math.inf
    upper = math.inf
    inset = 9.0
    for coordinate, component, minimum, maximum in (
        (point[0], unit[0], inset, correspondence.IMAGE_WIDTH - inset),
        (point[1], unit[1], inset, correspondence.IMAGE_HEIGHT - inset),
    ):
        if abs(component) <= 1e-9:
            assert minimum <= coordinate <= maximum
            continue
        first = (minimum - coordinate) / component
        second = (maximum - coordinate) / component
        lower = max(lower, min(first, second))
        upper = min(upper, max(first, second))
    assert lower <= upper
    endpoints = (
        (point[0] + lower * unit[0], point[1] + lower * unit[1]),
        (point[0] + upper * unit[0], point[1] + upper * unit[1]),
    )
    return smaller_share, endpoints


def _fully_visible_static_centers(
    group: dict[str, object],
) -> list[tuple[float, float]]:
    """Enumerate motif centres whose full circumscribed radius is on the plate."""

    render = group["render"]
    viewport_center = group["viewport_center"]
    assert isinstance(render, dict)
    assert isinstance(viewport_center, list)
    width = correspondence.IMAGE_WIDTH * correspondence.ANTIALIAS
    height = correspondence.IMAGE_HEIGHT * correspondence.ANTIALIAS
    b1, b2, radius, ranges = correspondence._site_geometry(
        render,
        width,
        height,
        viewport_center,
    )
    physical_scale = math.hypot(*b1) / math.hypot(*render["basis"][0])
    origin = (
        width / 2 - physical_scale * float(viewport_center[0]),
        height / 2 + physical_scale * float(viewport_center[1]),
    )
    base = render.get("base", [0.31, 0.17])
    centers: list[tuple[float, float]] = []
    for operation in render["ops"]:
        matrix = operation["M"]
        base_x = (
            matrix[0][0] * base[0]
            + matrix[0][1] * base[1]
            + operation["v"][0]
        )
        base_y = (
            matrix[1][0] * base[0]
            + matrix[1][1] * base[1]
            + operation["v"][1]
        )
        for lattice_x in ranges[0]:
            for lattice_y in ranges[1]:
                x = (
                    origin[0]
                    + (base_x + lattice_x) * b1[0]
                    + (base_y + lattice_y) * b2[0]
                )
                y = (
                    origin[1]
                    + (base_x + lattice_x) * b1[1]
                    + (base_y + lattice_y) * b2[1]
                )
                if radius <= x <= width - radius and radius <= y <= height - radius:
                    centers.append(
                        (
                            x / correspondence.ANTIALIAS,
                            y / correspondence.ANTIALIAS,
                        )
                    )
    return centers


def superscript_orders(signature: str) -> list[int]:
    runs: list[str] = []
    current = ""
    for character in signature:
        if character in "⁰¹²³⁴⁵⁶⁷⁸⁹":
            current += character.translate(SUPERSCRIPT_ASCII)
        elif current:
            runs.append(current)
            current = ""
    if current:
        runs.append(current)
    return [int(run) for run in runs]


def expected_book_audit_target(
    group: dict[str, object],
) -> tuple[dict[str, object], str, str, bool, str]:
    """Resolve the independently expected source for one Book type audit link."""

    evidence = group["signature_evidence"]
    assert isinstance(evidence, dict)
    excerpt = evidence.get("excerpt")
    if excerpt is not None:
        assert isinstance(excerpt, dict)
        excerpt_id = (
            evidence.get("source_colour_group_id")
            or excerpt.get("excerpt_key")
            or f'{group["id"]}-short-form'
        )
        source_url = excerpt.get("source_url") or excerpt.get("source")
        assert isinstance(excerpt_id, str)
        assert isinstance(source_url, str)
        return excerpt, f"book-audit::{excerpt_id}", source_url, True, "signature"

    references = group["book_audit"]
    assert isinstance(references, dict)
    primary = next(
        reference
        for reference in references["references"]
        if reference["role"] == "primary"
    )
    excerpt = correspondence.BOOK_EXCERPTS[primary["excerpt_key"]]
    if group["clock_order"] == 1:
        route = "onefold"
        short_signature = True
    else:
        assert evidence["status"] == "rule-extension"
        route = "type-fallback"
        short_signature = False
    return excerpt, excerpt["key"], primary["url"], short_signature, route


class CorrespondenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.section_ids: list[str] = []
        self.section_labelled_by: list[str] = []
        self.entry_heading_ids: list[str] = []
        self.entry_heading_texts: list[list[str]] = []
        self.family_ids: list[str] = []
        self.empty_family_ids: list[str] = []
        self.trivial_product_ids: list[str] = []
        self.tabbar_count = 0
        self.tabs: list[tuple[str, str, str]] = []
        self.wallpaper_links: list[str] = []
        self.directory_groups: list[tuple[str, str]] = []
        self.directory_palette_spans = 0
        self.catalog_links: list[str] = []
        self.plate_images: list[tuple[str, str, str, str]] = []
        self.plate_generator_overlays: list[dict[str, str | None]] = []
        self.plate_generators: list[tuple[str, str, str]] = []
        self.plate_generator_attributes: list[
            tuple[str, dict[str, str | None]]
        ] = []
        self.plate_generator_axis_lines: list[
            tuple[str, str, dict[str, str | None]]
        ] = []
        self.plate_generator_symbols: list[str] = []
        self.plate_generator_axes: list[str] = []
        self.plate_translation_arrows = 0
        self.plate_translation_arrow_halos = 0
        self.plate_quarter_arrows = 0
        self.plate_quarter_arrow_halos = 0
        self.crystal_viewers: list[dict[str, str | None]] = []
        self.crystal_stages: list[dict[str, str | None]] = []
        self.crystal_load_buttons: list[dict[str, str | None]] = []
        self.crystal_close_buttons: list[dict[str, str | None]] = []
        self.crystal_previews: list[dict[str, str | None]] = []
        self.crystal_frame_hosts: list[dict[str, str | None]] = []
        self.crystal_billiards_links: list[dict[str, str | None]] = []
        self.iframes: list[dict[str, str | None]] = []
        self.book_links: list[tuple[str, str, str]] = []
        self.book_excerpt_links: list[dict[str, str | None]] = []
        self.book_dialog_ids: list[str] = []
        self.book_excerpt_images: list[dict[str, str | None]] = []
        self.film_group_ids: list[str] = []
        self.canvases: list[tuple[str, str, str]] = []
        self.buttons: list[tuple[bool, str, str | None]] = []
        self.sliders: list[tuple[bool, str, str, str | None]] = []
        self.scripts: list[tuple[str, str]] = []
        self.mobile_viewport_bootstraps = 0
        self.presentation_tables: list[str] = []
        self.presentation_generator_count = 0
        self.presentation_time_shifts: list[str] = []
        self.presentation_clock_powers: list[str] = []
        self.presentation_source_cycles: list[str] = []
        self.presentation_generator_keys = 0
        self.presentation_generator_geometries = 0
        self.turn_directions: list[dict[str, str | None]] = []
        self.colour_orders: list[
            tuple[str, dict[str, str | None], list[str]]
        ] = []
        self.colour_order_actions: list[
            tuple[int | None, dict[str, str | None]]
        ] = []
        self.colour_order_action_svgs: list[
            tuple[int | None, dict[str, str | None]]
        ] = []
        self.short_signature_links: list[dict[str, str | None]] = []
        self.other_names_ids: list[str] = []
        self.identification_rows: list[tuple[str, tuple[str, ...]]] = []
        self.identified_names: list[dict[str, str | None]] = []
        self.short_form_support_in_book_audit: list[bool] = []
        self.extra_links_ids: list[str] = []
        self.extra_link_references: list[dict[str, str | None]] = []
        self.plane_group_links: list[str] = []
        self.height_lift_links: list[str] = []
        self.ucl_links: list[str] = []
        self.international_tables_references: list[dict[str, str | None]] = []
        self.ucl_references: list[dict[str, str | None]] = []
        self.diagram_symbol_teasers = 0
        self.diagram_symbol_dialogs = 0
        self.diagram_symbol_dialog_attributes: list[dict[str, str | None]] = []
        self.diagram_symbol_open_buttons: list[dict[str, str | None]] = []
        self.diagram_symbol_close_buttons: list[dict[str, str | None]] = []
        self.diagram_legend_symbol_rows: list[tuple[str, str]] = []
        self.diagram_legend_svgs: list[
            tuple[int | None, dict[str, str | None]]
        ] = []
        self.diagram_legend_row_texts: list[list[str]] = []
        self._inside_diagram_symbol_legend = False
        self._current_legend_row_tag = ""
        self._current_legend_row_index: int | None = None
        self._current_plate_overlay = ""
        self._current_plate_generator = ""
        self._current_colour_order_index: int | None = None
        self._span_depth = 0
        self._colour_order_action_span_depth: int | None = None
        self._current_other_names_id = ""
        self._inside_book_audit_row = False
        self._current_entry_heading_index: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "span":
            self._span_depth += 1
        if tag == "section" and "correspondence-entry" in classes:
            self.section_ids.append(attributes.get("id", ""))
            self.section_labelled_by.append(attributes.get("aria-labelledby", ""))
        heading_id = attributes.get("id") or ""
        heading_group_id = heading_id.removesuffix("-title")
        if (
            tag == "h3"
            and heading_id.endswith("-title")
            and heading_group_id.startswith("g")
            and heading_group_id[1:].isdigit()
        ):
            self.entry_heading_ids.append(heading_id)
            self.entry_heading_texts.append([])
            self._current_entry_heading_index = len(self.entry_heading_texts) - 1
        if tag == "aside" and "diagram-symbol-teaser" in classes:
            self.diagram_symbol_teasers += 1
        if tag == "dialog" and "diagram-symbol-dialog" in classes:
            self.diagram_symbol_dialogs += 1
            self.diagram_symbol_dialog_attributes.append(attributes)
            self._inside_diagram_symbol_legend = True
        if tag == "button" and "data-diagram-symbol-open" in attributes:
            self.diagram_symbol_open_buttons.append(attributes)
        if tag == "button" and "data-diagram-symbol-close" in attributes:
            self.diagram_symbol_close_buttons.append(attributes)
        if self._inside_diagram_symbol_legend and attributes.get(
            "data-legend-symbol"
        ):
            self.diagram_legend_symbol_rows.append(
                (tag, attributes.get("data-legend-symbol", ""))
            )
            self.diagram_legend_row_texts.append([])
            self._current_legend_row_tag = tag
            self._current_legend_row_index = (
                len(self.diagram_legend_symbol_rows) - 1
            )
        if tag == "svg" and self._inside_diagram_symbol_legend:
            self.diagram_legend_svgs.append(
                (self._current_legend_row_index, attributes)
            )
        if tag == "section" and "other-names" in classes:
            labelled_by = attributes.get("aria-labelledby", "")
            group_id = labelled_by.removesuffix("-other-names-title")
            self.other_names_ids.append(group_id)
            self._current_other_names_id = group_id
        if tag == "li" and self._current_other_names_id:
            self.identification_rows.append(
                (self._current_other_names_id, tuple(sorted(classes)))
            )
            self._inside_book_audit_row = "book-audit-row" in classes
        if tag == "span" and "identified-name" in classes:
            self.identified_names.append(attributes)
        if tag == "details" and "extra-links" in classes:
            self.extra_links_ids.append(attributes.get("data-extra-links", ""))
        if tag == "a" and attributes.get("data-catalog-id"):
            self.extra_link_references.append(attributes)
        if tag == "section" and "wallpaper-family" in classes:
            self.family_ids.append(attributes.get("id", ""))
            if "is-empty" in classes:
                self.empty_family_ids.append(attributes.get("id", ""))
        if tag == "aside" and "data-trivial-product" in attributes:
            self.trivial_product_ids.append(attributes.get("id", ""))
        if tag == "nav" and "clockwork-tabbar" in classes:
            self.tabbar_count += 1
        if tag == "a" and "data-clockwork-tab" in attributes:
            self.tabs.append(
                (
                    attributes.get("id", ""),
                    attributes.get("href", ""),
                    attributes.get("data-panel-id", ""),
                )
            )
        if tag == "a" and "directory-family-link" in classes:
            self.wallpaper_links.append(attributes.get("href", ""))
        if tag == "a" and attributes.get("data-directory-group"):
            self.directory_groups.append(
                (
                    attributes.get("data-directory-group", ""),
                    attributes.get("href", ""),
                )
            )
        if tag == "span" and "--directory-colour:" in (attributes.get("style") or ""):
            self.directory_palette_spans += 1
        if tag == "a" and (attributes.get("href") or "").startswith(
            correspondence.CATALOG_ROOT
        ):
            self.catalog_links.append(attributes["href"] or "")
        if tag == "a" and (attributes.get("href") or "").startswith(
            "https://it.iucr.org/Ac/ch2o2v0001/sgtable2o2o"
        ):
            self.plane_group_links.append(attributes["href"] or "")
        if tag == "a" and "international-tables-reference" in classes:
            self.international_tables_references.append(attributes)
        if tag == "a" and (attributes.get("href") or "").startswith(
            "space-group-correspondence.html#"
        ):
            self.height_lift_links.append(attributes["href"] or "")
        if (
            tag == "a"
            and "ucl-reference" in classes
            and (attributes.get("href") or "").startswith(
                "http://img.chem.ucl.ac.uk/sgp/large/"
            )
        ):
            self.ucl_links.append(attributes["href"] or "")
        if tag == "a" and "ucl-reference" in classes:
            self.ucl_references.append(attributes)
        if tag == "a" and "book-page-link" in classes:
            self.book_links.append(
                (
                    attributes.get("data-book-source", ""),
                    attributes.get("data-printed-page", ""),
                    attributes.get("data-pdf-page", ""),
                )
            )
        if tag == "a" and attributes.get("data-book-excerpt"):
            self.book_excerpt_links.append(attributes)
            if "short-form-support-link" in classes:
                self.short_form_support_in_book_audit.append(
                    self._inside_book_audit_row
                )
        if tag == "dialog" and "book-excerpt-dialog" in classes:
            self.book_dialog_ids.append(attributes.get("id", ""))
        if tag == "img" and "data-book-excerpt-image" in attributes:
            self.book_excerpt_images.append(attributes)
        if tag == "figure" and "clockwork-film" in classes:
            self.film_group_ids.append(attributes.get("data-group-id", ""))
        if tag == "figure" and "crystal-viewer" in classes:
            self.crystal_viewers.append(attributes)
        if "crystal-viewer-stage" in classes:
            self.crystal_stages.append(attributes)
        if tag == "button" and "data-crystal-load" in attributes:
            self.crystal_load_buttons.append(attributes)
        if tag == "button" and "data-crystal-close" in attributes:
            self.crystal_close_buttons.append(attributes)
        if tag == "img" and "crystal-viewer-preview" in classes:
            self.crystal_previews.append(attributes)
        if "data-crystal-frame" in attributes:
            self.crystal_frame_hosts.append(attributes)
        if tag == "a" and attributes.get("data-related-animation") == "billiards":
            self.crystal_billiards_links.append(attributes)
        if tag == "iframe":
            self.iframes.append(attributes)
        if tag == "canvas" and "clockwork-canvas" in classes:
            self.canvases.append(
                (
                    attributes.get("id", ""),
                    attributes.get("width", ""),
                    attributes.get("height", ""),
                )
            )
        if tag == "button" and "data-film-toggle" in attributes:
            self.buttons.append(
                (
                    "disabled" in attributes,
                    attributes.get("aria-pressed", ""),
                    attributes.get("aria-controls"),
                )
            )
        if tag == "input" and "data-film-slider" in attributes:
            self.sliders.append(
                (
                    "disabled" in attributes,
                    attributes.get("value", ""),
                    attributes.get("type", ""),
                    attributes.get("id"),
                )
            )
        if tag == "script":
            if "data-mobile-viewport-bootstrap" in attributes:
                self.mobile_viewport_bootstraps += 1
            else:
                self.scripts.append(
                    (attributes.get("src", ""), attributes.get("type", ""))
                )
        if tag == "table" and attributes.get("data-presentation"):
            self.presentation_tables.append(
                attributes.get("data-presentation", "")
            )
        if tag == "tr" and "presentation-generator-row" in classes:
            self.presentation_generator_count += 1
        if tag == "td" and "presentation-time-action" in classes:
            self.presentation_time_shifts.append(
                attributes.get("data-time-shift", "")
            )
        if tag == "td" and "presentation-colour-action" in classes:
            self.presentation_clock_powers.append(
                attributes.get("data-clock-power", "")
            )
            self.presentation_source_cycles.append(
                attributes.get("data-source-cycle", "")
            )
        if tag == "span" and "generator-key" in classes:
            self.presentation_generator_keys += 1
        if tag == "span" and "generator-geometry" in classes:
            self.presentation_generator_geometries += 1
        if tag == "span" and "turn-direction" in classes:
            self.turn_directions.append(attributes)
        if tag == "p" and "colour-order" in classes:
            if "colour-order--plate" in classes:
                placement = "plate"
            elif "colour-order--presentation" in classes:
                placement = "presentation"
            else:
                placement = ""
            self.colour_orders.append((placement, attributes, []))
            self._current_colour_order_index = len(self.colour_orders) - 1
        if tag == "span" and "colour-order-action" in classes:
            self.colour_order_actions.append(
                (self._current_colour_order_index, attributes)
            )
            self._colour_order_action_span_depth = self._span_depth
        if tag == "svg" and self._colour_order_action_span_depth is not None:
            self.colour_order_action_svgs.append(
                (self._current_colour_order_index, attributes)
            )
        if tag == "a" and "short-signature-link" in classes:
            self.short_signature_links.append(attributes)
        if tag == "img" and (attributes.get("src") or "").startswith(
            "output/clockwork-colorings/"
        ):
            self.plate_images.append(
                (
                    attributes.get("src", ""),
                    attributes.get("alt", ""),
                    attributes.get("width", ""),
                    attributes.get("height", ""),
                )
            )
        if tag == "svg" and "plate-generator-overlay" in classes:
            self.plate_generator_overlays.append(attributes)
            self._current_plate_overlay = attributes.get(
                "data-generator-overlay", ""
            )
        if tag == "g" and "plate-generator" in classes:
            self._current_plate_generator = attributes.get("data-generator", "")
            self.plate_generators.append(
                (
                    attributes.get("data-generator", ""),
                    attributes.get("data-generator-kind", ""),
                    attributes.get("data-rotation-order", ""),
                )
            )
            self.plate_generator_symbols.append(
                attributes.get("data-generator-symbol", "")
            )
            self.plate_generator_attributes.append(
                (self._current_plate_overlay, attributes)
            )
        if tag == "line" and "plate-generator-axis" in classes:
            self.plate_generator_axis_lines.append(
                (
                    self._current_plate_overlay,
                    self._current_plate_generator,
                    attributes,
                )
            )
            plane_classes = sorted(
                class_name.removeprefix("plate-generator-axis--plane-")
                for class_name in classes
                if class_name.startswith("plate-generator-axis--plane-")
            )
            self.plate_generator_axes.extend(plane_classes)
        if tag == "path" and "plate-generator-quarter-arrow" in classes:
            self.plate_quarter_arrows += 1
        if tag == "path" and "plate-generator-quarter-arrow-halo" in classes:
            self.plate_quarter_arrow_halos += 1
        if tag == "path" and "plate-generator-translation" in classes:
            self.plate_translation_arrows += 1
        if tag == "path" and "plate-generator-translation-halo" in classes:
            self.plate_translation_arrow_halos += 1

    def handle_data(self, data: str) -> None:
        if self._current_entry_heading_index is not None:
            self.entry_heading_texts[self._current_entry_heading_index].append(data)
        if self._current_legend_row_index is not None:
            self.diagram_legend_row_texts[
                self._current_legend_row_index
            ].append(data)
        if self._current_colour_order_index is not None:
            self.colour_orders[self._current_colour_order_index][2].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3" and self._current_entry_heading_index is not None:
            self._current_entry_heading_index = None
        if tag == "li" and self._inside_book_audit_row:
            self._inside_book_audit_row = False
        if tag == "section" and self._current_other_names_id:
            self._current_other_names_id = ""
        if tag == "svg" and self._current_plate_overlay:
            self._current_plate_overlay = ""
            self._current_plate_generator = ""
        if tag == "span":
            if self._span_depth == self._colour_order_action_span_depth:
                self._colour_order_action_span_depth = None
            self._span_depth -= 1
        if tag == "p" and self._current_colour_order_index is not None:
            self._current_colour_order_index = None
        if tag == self._current_legend_row_tag:
            self._current_legend_row_tag = ""
            self._current_legend_row_index = None
        if tag == "dialog" and self._inside_diagram_symbol_legend:
            self._inside_diagram_symbol_legend = False


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class ClockworkColoringCorrespondenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(correspondence.DATA.read_text(encoding="utf-8"))
        cls.page = correspondence.PAGE.read_text(encoding="utf-8")
        cls.parser = CorrespondenceParser()
        cls.parser.feed(cls.page)
        cls.page_groups = [
            group
            for base in correspondence.BASE_ORDER
            for group in sorted(
                (
                    group
                    for group in cls.payload["groups"]
                    if group["parent"]["hm"] == base
                ),
                key=lambda group: group["clock_order"] == 1,
            )
        ]
        cls.display_groups = [
            group
            for base in correspondence.BASE_ORDER
            for group in cls.payload["groups"]
            if group["parent"]["hm"] == base and group["clock_order"] > 1
        ]
        cls.trivial_groups = [
            group
            for base in correspondence.BASE_ORDER
            for group in cls.payload["groups"]
            if group["parent"]["hm"] == base and group["clock_order"] == 1
        ]
        cls.crystal_examples = json.loads(
            (ROOT / "data" / "crystal-examples.json").read_text(encoding="utf-8")
        )

    def test_68_record_source_renders_all_68_full_sections(self) -> None:
        groups = self.payload["groups"]
        manifest = json.loads(correspondence.MANIFEST.read_text(encoding="utf-8"))
        ids = [group["id"] for group in groups]
        page_ids = [group["id"] for group in self.page_groups]
        trivial_ids = [group["id"] for group in self.trivial_groups]
        self.assertEqual(self.payload["meta"]["schema_version"], 10)
        self.assertEqual(len(groups), 68)
        self.assertEqual(len(page_ids), 68)
        self.assertEqual(len(trivial_ids), 17)
        self.assertEqual(self.parser.section_ids, page_ids)
        self.assertEqual(
            self.parser.section_labelled_by,
            [f"{group_id}-title" for group_id in page_ids],
        )
        self.assertEqual(
            self.parser.entry_heading_ids,
            [f"{group_id}-title" for group_id in page_ids],
        )
        self.assertEqual(len(self.parser.entry_heading_texts), len(page_ids))
        for group_id, heading_parts in zip(
            page_ids,
            self.parser.entry_heading_texts,
        ):
            heading_text = " ".join(heading_parts)
            self.assertNotIn(group_id, heading_text, group_id)
        self.assertNotIn('class="group-id"', self.page)
        self.assertEqual(self.parser.trivial_product_ids, [])
        self.assertEqual(ids, [group["id"] for group in manifest["groups"]])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            [group["parent"]["hm"] for group in self.trivial_groups],
            list(correspondence.BASE_ORDER),
        )
        for group in self.trivial_groups:
            self.assertTrue(group["product"])
            self.assertEqual(group["clock_order"], 1)
            self.assertEqual(group["parent"], group["kernel"])

        for index, base in enumerate(correspondence.BASE_ORDER):
            start = self.page.index(f'id="wallpaper-{base}"')
            if index + 1 < len(correspondence.BASE_ORDER):
                end = self.page.index(
                    f'id="wallpaper-{correspondence.BASE_ORDER[index + 1]}"'
                )
            else:
                end = self.page.index('<section class="provenance"')
            family_html = self.page[start:end]
            family_groups = [
                group for group in self.page_groups if group["parent"]["hm"] == base
            ]
            self.assertEqual(family_html.count("data-clockwork-tabs"), 1, base)
            self.assertEqual(
                family_html.count('class="correspondence-entry"'),
                len(family_groups),
                base,
            )
            self.assertNotIn("data-trivial-product", family_html)
            self.assertNotIn('class="trivial-product"', family_html)

        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(".trivial-product", css)
        self.assertNotIn("family-omission", self.page)

    def test_all_17_wallpaper_sections_have_tabs_for_every_forward_group(self) -> None:
        self.assertEqual(
            self.parser.family_ids,
            [f"wallpaper-{base}" for base in correspondence.BASE_ORDER],
        )
        page_ids = [group["id"] for group in self.page_groups]
        self.assertEqual(
            self.parser.tabs,
            [(f"tab-{group_id}", f"#{group_id}", group_id) for group_id in page_ids],
        )
        self.assertEqual(self.parser.tabbar_count, 17)
        self.assertEqual(self.parser.empty_family_ids, [])
        for base in correspondence.BASE_ORDER:
            summary = correspondence.WALLPAPER_SUMMARIES[base]
            self.assertIn(correspondence.orbifold_html(summary), self.page)

            family_groups = [
                group for group in self.page_groups if group["parent"]["hm"] == base
            ]
            self.assertEqual(family_groups[-1]["clock_order"], 1, base)

        self.assertNotIn("Forward note", self.page)
        self.assertNotIn("No nontrivial forward lift occurs", self.page)
        self.assertNotIn("Nontrivial orders", self.page)
        self.assertNotIn('class="family-empty"', self.page)

        script = (ROOT / "clockwork-coloring-correspondence.js").read_text(encoding="utf-8")
        self.assertIn("initializeClockworkTabs", script)
        self.assertIn('setAttribute("role", "tablist")', script)
        self.assertIn('setAttribute("role", "tab")', script)
        self.assertIn('setAttribute("role", "tabpanel")', script)
        self.assertIn('event.key === "ArrowRight"', script)
        self.assertIn('event.key === "Home"', script)
        self.assertIn('window.addEventListener("hashchange"', script)
        self.assertIn('window.addEventListener("popstate"', script)
        self.assertIn('if (previousId !== groupId)', script)
        self.assertIn('if (inactive && inactive !== active)', script)

    def test_crystal_example_map_is_complete_pinned_and_auditable(self) -> None:
        examples = self.crystal_examples["groups"]
        source_ids = [group["id"] for group in self.payload["groups"]]
        example_ids = [example["id"] for example in examples]
        self.assertEqual(len(examples), 68)
        self.assertEqual(len(example_ids), len(set(example_ids)))
        self.assertEqual(example_ids, source_ids)
        self.assertEqual(self.crystal_examples["meta"]["groups"], 68)
        self.assertEqual(
            Counter(example["provider"] for example in examples),
            Counter({"sketchfab": 67, "3dmol-cod": 1}),
        )

        space_payload = json.loads(
            correspondence.SPACE_GROUP_DATA.read_text(encoding="utf-8")
        )
        space_by_id = {
            record["id"]: record["space_group"]
            for record in space_payload["groups"]
        }
        for example in examples:
            group_id = example["id"]
            self.assertEqual(example["it_number"], space_by_id[group_id]["it_number"])
            self.assertEqual(example["hm_short"], space_by_id[group_id]["hm_short"])
            self.assertTrue(example["crystal_name"], group_id)
            self.assertEqual(urlparse(example["source_url"]).scheme, "https", group_id)
            self.assertEqual(
                urlparse(example["source_url"]).netloc,
                "crystalsymmetry.wordpress.com",
                group_id,
            )
            self.assertNotIn("embed_url", example, group_id)

            if example["provider"] == "sketchfab":
                self.assertEqual(len(example["model_uid"]), 32, group_id)
                self.assertTrue(
                    all(character in "0123456789abcdef" for character in example["model_uid"]),
                    group_id,
                )
                self.assertTrue(example["model_name"], group_id)
                self.assertTrue(example["creator"], group_id)
                viewer = urlparse(example["viewer_url"])
                self.assertEqual(viewer.scheme, "https", group_id)
                self.assertEqual(viewer.netloc, "sketchfab.com", group_id)
                self.assertIn(example["model_uid"], viewer.path, group_id)
            else:
                self.assertEqual(group_id, "g247")
                self.assertEqual(str(example["cod_id"]), "2101517")
                self.assertEqual(
                    example["cif_url"],
                    "https://www.crystallography.net/cod/2101517.cif",
                )
                self.assertEqual(
                    urlparse(example["viewer_url"]).netloc,
                    "www.crystallography.net",
                )

        mismatches = [
            example for example in examples if example["reference_match"] != "exact"
        ]
        self.assertEqual([example["id"] for example in mismatches], ["g7"])
        self.assertTrue(mismatches[0]["note"])

        related_animation_examples = [
            example for example in examples if "related_animation_url" in example
        ]
        self.assertEqual(
            [
                (
                    example["id"],
                    example["related_animation_url"],
                    example["related_animation_label"],
                )
                for example in related_animation_examples
            ],
            [
                (
                    "g235",
                    "https://yaroslavvb.github.io/animated-groups-fable/billiards.html",
                    "Billiards animation",
                )
            ],
        )

    def test_proustite_entry_links_the_matching_billiards_animation(self) -> None:
        self.assertEqual(len(self.parser.crystal_billiards_links), 1)
        link = self.parser.crystal_billiards_links[0]
        self.assertEqual(link.get("data-group-id"), "g235")
        self.assertEqual(
            link.get("href"),
            "https://yaroslavvb.github.io/animated-groups-fable/billiards.html",
        )
        self.assertEqual(link.get("target"), "_blank")
        self.assertEqual(set((link.get("rel") or "").split()), {"noopener"})

    def test_every_entry_has_a_lazy_real_crystal_viewer(self) -> None:
        examples = self.crystal_examples["groups"]
        example_by_id = {example["id"]: example for example in examples}
        page_ids = [group["id"] for group in self.page_groups]
        self.assertEqual(len(self.parser.crystal_viewers), 68)
        self.assertEqual(
            [attributes.get("data-group-id") for attributes in self.parser.crystal_viewers],
            page_ids,
        )
        self.assertEqual(len(self.parser.crystal_stages), 68)
        self.assertEqual(len(self.parser.crystal_load_buttons), 68)
        self.assertEqual(len(self.parser.crystal_close_buttons), 68)
        self.assertEqual(len(self.parser.crystal_previews), 68)
        self.assertEqual(len(self.parser.crystal_frame_hosts), 68)
        self.assertEqual(self.parser.iframes, [])

        for viewer in self.parser.crystal_viewers:
            group_id = viewer.get("data-group-id") or ""
            example = example_by_id[group_id]
            self.assertIn("data-crystal-viewer", viewer)
            self.assertEqual(viewer.get("data-provider"), example["provider"])
            embed = urlparse(viewer.get("data-crystal-embed") or "")
            self.assertEqual(embed.scheme, "https", group_id)
            if example["provider"] == "sketchfab":
                self.assertEqual(embed.netloc, "sketchfab.com", group_id)
                self.assertEqual(
                    embed.path,
                    f'/models/{example["model_uid"]}/embed',
                    group_id,
                )
            else:
                self.assertEqual(embed.netloc, "3dmol.csb.pitt.edu", group_id)
                self.assertEqual(embed.path, "/viewer.html", group_id)
                query = parse_qs(embed.query)
                self.assertEqual(query.get("url"), [example["cif_url"]])
                self.assertEqual(query.get("type"), ["cif"])

        self.assertEqual(
            [attributes.get("id") for attributes in self.parser.crystal_stages],
            [f"{group_id}-crystal-stage" for group_id in page_ids],
        )
        self.assertEqual(
            [attributes.get("aria-describedby") for attributes in self.parser.crystal_stages],
            [f"{group_id}-crystal-status" for group_id in page_ids],
        )
        self.assertEqual(
            [attributes.get("aria-controls") for attributes in self.parser.crystal_load_buttons],
            [f"{group_id}-crystal-stage" for group_id in page_ids],
        )
        self.assertTrue(
            all(
                attributes.get("type") == "button"
                for attributes in self.parser.crystal_load_buttons
                + self.parser.crystal_close_buttons
            )
        )
        preview_urls = [
            urlparse(attributes.get("src") or "")
            for attributes in self.parser.crystal_previews
        ]
        self.assertEqual(
            [preview.path for preview in preview_urls],
            [f"output/space-groups/{group_id}.webp" for group_id in page_ids],
        )
        self.assertTrue(all(not preview.fragment for preview in preview_urls))
        self.assertTrue(
            all(
                not preview.query or set(parse_qs(preview.query)) == {"v"}
                for preview in preview_urls
            )
        )
        for group_id, attributes in zip(page_ids, self.parser.crystal_previews):
            alt = (attributes.get("alt") or "").casefold()
            self.assertIn("space–time", alt, group_id)
            self.assertIn("vertical time", alt, group_id)
            self.assertIn("one clock period", alt, group_id)

        figures = re.findall(
            r'<figure class="crystal-viewer".*?</figure>',
            self.page,
            re.DOTALL,
        )
        self.assertEqual(len(figures), 68)
        for group_id, figure in zip(page_ids, figures):
            visible_copy = re.sub(r"<[^>]+>", " ", figure)
            visible_copy = re.sub(r"\s+", " ", visible_copy).casefold()
            self.assertIn("vertical axis is time", visible_copy, group_id)
            self.assertIn("one clock period", visible_copy, group_id)

        self.assertEqual(self.page.count(escape(example_by_id["g7"]["note"])), 1)
        self.assertEqual(
            self.page.count(escape(example_by_id["g137"]["source_warning"])),
            1,
        )

    def test_crystal_viewer_module_allows_only_one_live_iframe(self) -> None:
        script_path = ROOT / "crystal-viewer.js"
        self.assertTrue(script_path.is_file())
        script = script_path.read_text(encoding="utf-8")
        self.assertEqual(script.count("let activeRoot = null"), 1)
        self.assertIn('document.querySelectorAll("[data-crystal-viewer]")', script)
        self.assertIn('document.createElement("iframe")', script)
        self.assertIn('document.addEventListener("clockwork:tab-change"', script)
        self.assertIn("activeRoot", script)
        self.assertIn("frameHost.replaceChildren()", script)
        self.assertIn('iframe.referrerPolicy = "no-referrer"', script)
        self.assertIn('iframe.setAttribute(\n    "sandbox"', script)
        self.assertIn("closeButton.focus()", script)
        self.assertNotIn("https://cdn", script)

    def test_generated_page_has_no_wolfram_or_mathematica_content(self) -> None:
        self.assertNotIn("Wolfram", self.page)
        self.assertNotIn("Mathematica", self.page)
        self.assertNotIn("FiniteGroupData", self.page)
        self.assertNotIn("wolfram-group", self.page)
        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("wolfram-group", css)

    def test_every_row_has_an_exact_forward_catalog_deep_link(self) -> None:
        expected = [
            f"{correspondence.CATALOG_ROOT}#{group['id']}"
            for group in self.page_groups
        ]
        self.assertEqual(self.parser.catalog_links, expected)

    def test_every_row_has_identifications_and_complete_extra_catalogues(self) -> None:
        page_ids = [group["id"] for group in self.page_groups]
        self.assertEqual(self.parser.other_names_ids, page_ids)
        self.assertEqual(
            self.page.count("Identifications"),
            len(self.page_groups),
        )
        self.assertEqual(
            self.page.count('<span class="term-help-label" aria-hidden="true">Book type audit</span>'),
            len(self.page_groups),
        )
        self.assertEqual(
            self.parser.identification_rows,
            [
                row
                for group_id in page_ids
                for row in (
                    (group_id, ("book-audit-row",)),
                    (group_id, ("other-names-row",)),
                )
            ],
        )
        self.assertEqual(
            self.page.count(
                '<span class="other-name-category">Other names</span>'
            ),
            len(self.page_groups),
        )
        self.assertNotIn("Colour-fixing plane-group type K", self.page)
        self.assertNotIn("Height-lift space-group type", self.page)

        space_payload = json.loads(
            correspondence.SPACE_GROUP_DATA.read_text(encoding="utf-8")
        )
        space_by_id = {
            record["id"]: record["space_group"]
            for record in space_payload["groups"]
        }
        page_groups = self.page_groups
        page_ids = [group["id"] for group in page_groups]
        self.assertEqual(self.parser.extra_links_ids, page_ids)
        self.assertEqual(len(set(self.parser.extra_links_ids)), 68)
        self.assertEqual(self.page.count(">Extra links</summary>"), 68)
        self.assertEqual(self.page.count('<details class="extra-links"'), 68)
        self.assertNotIn('<details class="extra-links" open', self.page)
        extra_links_css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".extra-links > summary", extra_links_css)
        self.assertIn(".extra-links[open] > summary::after", extra_links_css)
        self.assertIn("min-height: 2.9rem", extra_links_css)

        expected_extra_links = [
            (group["id"], link)
            for group in page_groups
            for link in space_by_id[group["id"]]["extra_links"]
        ]
        self.assertEqual(
            [attributes.get("data-group-id") for attributes in self.parser.extra_link_references],
            [group_id for group_id, _ in expected_extra_links],
        )
        self.assertEqual(
            [attributes.get("data-catalog-id") for attributes in self.parser.extra_link_references],
            [link["catalog_id"] for _, link in expected_extra_links],
        )
        self.assertEqual(
            [attributes.get("href") for attributes in self.parser.extra_link_references],
            [link["url"] for _, link in expected_extra_links],
        )
        self.assertEqual(
            [attributes.get("data-link-scope") for attributes in self.parser.extra_link_references],
            [link["scope"] for _, link in expected_extra_links],
        )
        self.assertTrue(
            all(
                attributes.get("target") == "_blank"
                and attributes.get("rel") == "noopener"
                for attributes in self.parser.extra_link_references
            )
        )
        extra_by_group: dict[str, list[dict[str, str | None]]] = defaultdict(list)
        for attributes in self.parser.extra_link_references:
            extra_by_group[attributes.get("data-group-id", "")].append(attributes)
        self.assertEqual(set(extra_by_group), set(page_ids))
        for group_id, attributes_list in extra_by_group.items():
            self.assertEqual(
                tuple(item.get("data-catalog-id") for item in attributes_list),
                space_correspondence.EXTRA_CATALOG_IDS,
                group_id,
            )
            urls = [item.get("href") for item in attributes_list]
            self.assertEqual(len(urls), len(set(urls)), group_id)

        expected_parent_links = [
            link["url"]
            for group in page_groups
            for link in space_by_id[group["id"]]["extra_links"]
            if link["catalog_id"] == "iucr-plane-group"
        ]
        self.assertEqual(self.parser.plane_group_links, expected_parent_links)
        self.assertEqual(
            [
                attributes.get("href")
                for attributes in self.parser.international_tables_references
            ],
            expected_parent_links,
        )
        self.assertEqual(self.parser.height_lift_links, [])
        self.assertEqual(
            self.parser.ucl_links,
            [space_by_id[group_id]["ucl_reference_url"] for group_id in page_ids],
        )
        self.assertEqual(
            [attributes.get("href") for attributes in self.parser.ucl_references],
            [space_by_id[group_id]["ucl_reference_url"] for group_id in page_ids],
        )
        self.assertTrue(
            all(
                attributes.get("target") == "_blank"
                and attributes.get("rel") == "noopener"
                for attributes in self.parser.ucl_references
            )
        )

        for group in self.page_groups:
            group_id = group["id"]
            space_group = space_by_id[group_id]
            section_start = self.page.index(
                f'<section class="other-names" aria-labelledby="{group_id}-other-names-title">'
            )
            section_end = self.page.index("</section>", section_start)
            section = self.page[section_start:section_end]
            self.assertNotIn("international-tables-reference", section, group_id)
            self.assertNotIn("ucl-reference", section, group_id)
            self.assertNotIn("space-group-correspondence.html#", section, group_id)
            self.assertIn(
                correspondence.fibrifold_html(
                    correspondence.FIBRIFOLD_BY_ID[group_id]
                ),
                section,
                group_id,
            )
            self.assertIn(
                '<span class="hermann-mauguin-name">'
                f'{correspondence._hm_html(space_group["hm_short"])}</span>',
                section,
                group_id,
            )
            if correspondence._hm_compare_key(
                space_group["hm_full"]
            ) != correspondence._hm_compare_key(space_group["hm_short"]):
                self.assertIn(
                    '<span class="hermann-mauguin-name '
                    'hermann-mauguin-name--full">'
                    f'{correspondence._hm_html(space_group["hm_full"])}</span>',
                    section,
                    group_id,
                )
            else:
                self.assertNotIn("hermann-mauguin-name--full", section, group_id)
            self.assertIn(
                '<span class="international-tables-number">'
                f'No. {space_group["it_number"]}</span>',
                section,
                group_id,
            )
            self.assertIn(
                '<span class="schoenflies-name" '
                f'aria-label="{escape(space_group["schoenflies"])}">'
                f'{correspondence._schoenflies_html(space_group["schoenflies"])}</span>',
                section,
                group_id,
            )
            self.assertIn(
                '<span class="hall-symbol-name">'
                f'{escape(space_group["hall"])}</span>',
                section,
                group_id,
            )

        g246_start = self.page.index('<details class="extra-links" data-extra-links="g246"')
        g246_end = self.page.index("</details>", g246_start)
        g246 = self.page[g246_start:g246_end]
        self.assertIn("CrystalSymmetry worked example", g246)
        self.assertIn("No. 173 P6_3", g246)
        self.assertIn("Point group 6", g246)
        self.assertIn("No. 16 p6", g246)
        self.assertIn("Select No. 173 P6_3 manually", g246)
        self.assertNotIn("UCL diagram and tables", self.page)
        self.assertNotIn("Parent plane-group type G", self.page)

        self.assertEqual(
            set(correspondence.FIBRIFOLD_BY_ID),
            {group["id"] for group in self.payload["groups"]},
        )
        self.assertEqual(
            self.page.count('class="fibrifold-name"'),
            68,
        )
        self.assertEqual(
            self.page.count('class="hermann-mauguin-name"'),
            68,
        )
        self.assertEqual(
            self.page.count(
                'class="hermann-mauguin-name hermann-mauguin-name--full"'
            ),
            7,
        )
        self.assertEqual(
            self.page.count('class="international-tables-number"'),
            68,
        )
        self.assertEqual(
            self.page.count('class="schoenflies-name"'),
            68,
        )
        self.assertEqual(
            self.page.count('class="hall-symbol-name"'),
            68,
        )
        self.assertNotIn('class="fibrifold-orientation-note"', self.page)
        self.assertNotIn("data-trivial-product", self.page)

        self.assertNotIn(
            "chaimgoodmanstrauss.com/various-crystallographic-space-groups/",
            self.page,
        )

    def test_identification_help_is_non_latching_and_complete(self) -> None:
        self.assertEqual(
            set(correspondence.TERM_HELP),
            {
                "Book type audit",
                "Catalog instance",
                "Conway fibrifold notation",
                "Hermann–Mauguin space-group symbol",
                "Full Hermann–Mauguin space-group symbol",
                "International Tables number",
                "Schoenflies space-group symbol",
                "Hall setting symbol",
                "Complementary forward skips",
            },
        )
        book_help = correspondence.TERM_HELP["Book type audit"]
        self.assertEqual(
            self.page.count(
                '<span class="term-help-label" aria-hidden="true">'
                "Book type audit</span>"
            ),
            len(self.page_groups),
        )
        self.assertEqual(
            self.page.count(
                '<span class="term-help-copy" aria-hidden="true">'
                f"{escape(book_help)}</span>"
            ),
            len(self.page_groups),
        )

        space_payload = json.loads(
            correspondence.SPACE_GROUP_DATA.read_text(encoding="utf-8")
        )
        space_by_id = {
            group["id"]: group["space_group"] for group in space_payload["groups"]
        }
        expected_name_systems: list[tuple[str, str]] = []
        for group in self.page_groups:
            group_id = group["id"]
            space_group = space_by_id[group_id]
            systems = [
                "Conway fibrifold notation",
                "Hermann–Mauguin space-group symbol",
            ]
            if correspondence._hm_compare_key(
                space_group["hm_full"]
            ) != correspondence._hm_compare_key(space_group["hm_short"]):
                systems.append("Full Hermann–Mauguin space-group symbol")
            systems.extend(
                [
                    "International Tables number",
                    "Schoenflies space-group symbol",
                    "Hall setting symbol",
                ]
            )
            if group["complementary_skip_mate"]:
                systems.append("Complementary forward skips")
            systems.append("Catalog instance")
            expected_name_systems.extend((group_id, system) for system in systems)
        self.assertEqual(len(expected_name_systems), 68 * 6 + 7 + 8)
        self.assertEqual(
            [
                attributes.get("data-name-system")
                for attributes in self.parser.identified_names
            ],
            [system for _, system in expected_name_systems],
        )
        for attributes, (group_id, system) in zip(
            self.parser.identified_names,
            expected_name_systems,
        ):
            space_group = space_by_id[group_id]
            classes = set((attributes.get("class") or "").split())
            self.assertTrue({"identified-name", "term-help"} <= classes, group_id)
            self.assertNotIn("tabindex", attributes, group_id)
            title = attributes.get("title") or ""
            expected_help = correspondence.TERM_HELP[system]
            setting_help = correspondence.SPACE_GROUP_SETTING_HELP.get(
                space_group["choice"], ""
            )
            if system == "Conway fibrifold notation":
                orientation_note = "Two orientations share this fibrifold name"
                if group_id in correspondence.FIBRIFOLD_ENANTIOMORPHIC_IDS:
                    expected_help += (
                        " Two orientations share this fibrifold name; the current "
                        "catalog record selects one orientation."
                    )
                else:
                    self.assertNotIn(orientation_note, title, group_id)
            elif system == "Hermann–Mauguin space-group symbol":
                expected_help += f' Full form: {space_group["hm_full"]}.'
                if setting_help:
                    expected_help += f" {setting_help}"
            elif system in {
                "Full Hermann–Mauguin space-group symbol",
                "Hall setting symbol",
            } and setting_help:
                expected_help += f" {setting_help}"
            self.assertEqual(title, f"{system}: {expected_help}", group_id)

        mates = [
            group for group in self.page_groups if group["complementary_skip_mate"]
        ]
        self.assertEqual(len(mates), 8)
        self.assertEqual(
            self.page.count('data-name-system="Complementary forward skips"'),
            len(mates),
        )
        for group in mates:
            section_start = self.page.index(
                f'<section class="other-names" aria-labelledby="{group["id"]}-other-names-title">'
            )
            section_end = self.page.index("</section>", section_start)
            section = self.page[section_start:section_end]
            self.assertIn(
                f'href="#{group["complementary_skip_mate"]}"',
                section,
                group["id"],
            )

        self.assertNotIn('<details class="term-help">', self.page)
        self.assertEqual(
            self.page.count('<details class="presentation-source-audit">'),
            len(SOURCE_LABELING_FIXTURE),
        )
        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".term-help:hover .term-help-copy", css)
        self.assertIn(".term-help:focus-within .term-help-copy", css)
        self.assertIn(".hermann-mauguin-name", css)
        self.assertIn(".international-tables-number", css)
        self.assertIn(".schoenflies-name", css)
        self.assertIn(".hall-symbol-name", css)
        self.assertNotIn(".term-help[open]", css)
        self.assertNotIn("@media (hover: none)", css)
        self.assertIn("pointer-events: none", css)
        self.assertEqual(
            correspondence.CORRESPONDENCE_STYLE_SRC,
            "clockwork-coloring-correspondence.css?"
            "v=compact-generator-actions-v1",
        )
        self.assertIn(
            f'href="{correspondence.CORRESPONDENCE_STYLE_SRC}"', self.page
        )

    def test_g235_lists_every_major_crystallographic_name_once_and_in_order(self) -> None:
        section_start = self.page.index(
            '<section class="other-names" aria-labelledby="g235-other-names-title">'
        )
        section_end = self.page.index("</section>", section_start)
        section = self.page[section_start:section_end]
        self.assertEqual(
            re.findall(r'data-name-system="([^"]+)"', section),
            [
                "Conway fibrifold notation",
                "Hermann–Mauguin space-group symbol",
                "International Tables number",
                "Schoenflies space-group symbol",
                "Hall setting symbol",
                "Catalog instance",
            ],
        )
        expected_values = [
            '<span class="hermann-mauguin-name">R3c</span>',
            '<span class="international-tables-number">No. 161</span>',
            '<span class="schoenflies-name" aria-label="C3v^6">'
            'C<sub>3v</sub><sup>6</sup></span>',
            '<span class="hall-symbol-name">R 3 -2&quot;c</span>',
        ]
        for markup in expected_values:
            self.assertEqual(section.count(markup), 1, markup)
        self.assertNotIn("Full Hermann–Mauguin space-group symbol", section)
        self.assertNotIn("hermann-mauguin-name--full", section)
        self.assertIn("Full form: R 3 c.", section)
        self.assertIn(
            "Selected setting: hexagonal axes for the rhombohedral lattice.",
            section,
        )

    def test_tos_notation_and_clock_orders_are_complete(self) -> None:
        groups = self.payload["groups"]
        self.assertEqual(len(correspondence.BOOK_TWO_FOLD_SIGNATURE_BY_TYPE), 46)
        self.assertEqual(len(correspondence.BOOK_HIGHER_SIGNATURE_BY_ID), 15)
        self.assertEqual(
            correspondence.BOOK_REPRESENTATIVE_MULTIPLICITY_BY_ID,
            BOOK_REPRESENTATIVE_FIXTURE,
        )
        counts = Counter(group["clock_order"] for group in groups)
        self.assertEqual(
            {n: counts.get(n, 0) for n in range(1, 7)},
            correspondence.EXPECTED_ORDER_COUNTS,
        )
        for group in groups:
            self.assertTrue(group["parent"]["orbifold"])
            self.assertTrue(group["kernel"]["orbifold"])
            self.assertEqual(
                group["tos_notation"],
                correspondence.tos_notation(
                    group["parent"]["orbifold"],
                    group["kernel"]["orbifold"],
                    group["clock_order"],
                ),
            )
            self.assertEqual(
                group["book_color_signature"],
                correspondence.book_color_signature(
                    group["id"],
                    group["parent"]["orbifold"],
                    group["tos_notation"],
                    group["clock_order"],
                ),
            )
            self.assertEqual(
                group["signature_evidence"],
                correspondence.signature_evidence(
                    group["id"],
                    group["clock_order"],
                    group["tos_notation"],
                ),
            )
            self.assertNotIn("//", group["tos_notation"])
            if group["parent"]["hm"] == "p1":
                self.assertEqual(group["parent"]["orbifold"], "◦")
            if group["kernel"]["hm"] == "p1":
                self.assertEqual(group["kernel"]["orbifold"], "◦")
            self.assertEqual(len(group["phase_residues"]), group["clock_order"])
            if group["clock_order"] > 1:
                for permutation_order in superscript_orders(
                    group["book_color_signature"]
                ):
                    self.assertEqual(
                        group["clock_order"] % permutation_order,
                        0,
                        group["id"],
                    )
        g60 = next(group for group in groups if group["id"] == "g60")
        self.assertEqual(g60["book_color_signature"], "*¹2²2¹2²2")
        self.assertIn(
            '<span class="orbifold-star">∗</span><sup>1</sup>2<sup>2</sup>2<sup>1</sup>2<sup>2</sup>2',
            self.page,
        )
        self.assertEqual(
            self.page.count(
                '<span class="book-color-signature" aria-label="Chaim notation '
            ),
            len(self.page_groups),
        )
        for group in self.page_groups:
            entry_start = self.page.index(
                f'<section class="correspondence-entry" id="{group["id"]}"'
            )
            heading_end = self.page.index("</h3>", entry_start)
            heading = self.page[entry_start:heading_end]
            self.assertIn(
                correspondence.superscript_html(group["book_color_signature"]),
                heading,
                group["id"],
            )

        self.assertNotIn('class="notation-crosswalk"', self.page)
        self.assertNotIn("A reduced clock phase a/b induces permutation order b", self.page)
        self.assertNotIn("unique Table 11.1 short signature", self.page)
        self.assertNotIn("non-product forward lift", self.page)
        self.assertNotIn("Clockwork symbol", self.page)
        self.assertNotIn("Clockwork notation", self.page)
        self.assertNotIn('class="clockwork-symbol"', self.page)
        self.assertNotIn('class="clockwork-description"', self.page)
        self.assertNotIn('class="phase-description"', self.page)
        self.assertNotIn('class="coloring-description"', self.page)
        # The retired all-groups notation field stays absent.  The deliberately
        # narrower collision marker is covered below.

        script = (ROOT / "clockwork-coloring-correspondence.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("record.symbol", script)

    def test_chaim_signature_collisions_get_unique_clockwork_symbols(self) -> None:
        expected_fibres = {
            "⁴4⁴4²2": {"g96": "4₁4₁2₁", "g97": "4₃4₃2₁"},
            "³3³3³3": {"g225": "3₂3₂3₂", "g226": "3₁3₁3₁"},
            "³6³3¹2": {"g244": "6₂3₂2", "g245": "6₄3₁2"},
            "⁶6³3²2": {"g247": "6₅3₂2₁", "g248": "6₁3₁2₁"},
        }
        fibres: dict[str, list[dict[str, object]]] = defaultdict(list)
        for group in self.display_groups:
            fibres[group["book_color_signature"]].append(group)
        actual_fibres = {
            signature: {
                str(group["id"]): str(group["symbol"])
                for group in fibre
            }
            for signature, fibre in fibres.items()
            if len(fibre) > 1
        }
        self.assertEqual(actual_fibres, expected_fibres)
        collision_ids = {
            group_id
            for fibre in expected_fibres.values()
            for group_id in fibre
        }
        self.assertEqual(
            collision_ids,
            set(correspondence.COLOUR_SIGNATURE_COLLISION_IDS),
        )
        self.assertEqual(len(fibres), 47)
        self.assertEqual(
            len({group["symbol"] for group in self.display_groups}),
            len(self.display_groups),
        )

        self.assertEqual(self.page.count('class="notation-caveat"'), 1)
        self.assertIn("Chaim Goodman–Strauss’s coloured-orbifold notation", self.page)
        self.assertIn("Across all 68 forward groups it gives 64", self.page)
        self.assertIn("Four types leave the two orientations", self.page)
        for colour_type in (
            "442<sup>4</sup>/◦",
            "333<sup>3</sup>/◦",
            "632<sup>6</sup>/◦",
            "632<sup>3</sup>/2222",
        ):
            self.assertIn(colour_type, self.page)
        self.assertIn(
            f'href="{correspondence.HIERARCHY_CHIRALITY_URL}"',
            self.page,
        )
        self.assertIn(
            'href="docs/orbifold_notation.html#uncovered-cases"',
            self.page,
        )
        self.assertEqual(
            self.page.count('class="clockwork-disambiguator '),
            3 * len(collision_ids),
        )
        for context in ("heading", "tab", "directory"):
            self.assertEqual(
                self.page.count(f"clockwork-disambiguator--{context}"),
                len(collision_ids),
            )

        groups_by_id = {group["id"]: group for group in self.display_groups}
        for group_id, group in groups_by_id.items():
            rendered_symbol = correspondence.clockwork_symbol_html(
                str(group["symbol"])
            )
            contexts = {
                "directory": self.page[
                    self.page.index(
                        f'<a class="directory-group" href="#{group_id}"'
                    ):
                    self.page.index(
                        "</a>",
                        self.page.index(
                            f'<a class="directory-group" href="#{group_id}"'
                        ),
                    )
                ],
                "tab": self.page[
                    self.page.index(
                        f'<a class="clockwork-tab" id="tab-{group_id}"'
                    ):
                    self.page.index(
                        "</a>",
                        self.page.index(
                            f'<a class="clockwork-tab" id="tab-{group_id}"'
                        ),
                    )
                ],
                "heading": self.page[
                    self.page.index(
                        f'<section class="correspondence-entry" id="{group_id}"'
                    ):
                    self.page.index(
                        "</header>",
                        self.page.index(
                            f'<section class="correspondence-entry" id="{group_id}"'
                        ),
                    )
                ],
            }
            if group_id in collision_ids:
                for context, fragment in contexts.items():
                    self.assertIn(
                        f"clockwork-disambiguator--{context}",
                        fragment,
                        group_id,
                    )
                    self.assertIn(rendered_symbol, fragment, group_id)
                    self.assertIn(
                        f"project-specific clockwork symbol {escape(group['symbol'])}".lower(),
                        fragment.lower(),
                        group_id,
                    )
            else:
                for context, fragment in contexts.items():
                    self.assertNotIn(
                        f"clockwork-disambiguator--{context}",
                        fragment,
                        group_id,
                    )
        self.assertEqual(self.page.count("aria-describedby="), len(self.page_groups))

    def test_visible_mirror_atoms_use_the_books_baseline_math_glyph(self) -> None:
        protected_star = '<span class="orbifold-star">∗</span>'
        self.assertGreater(self.page.count(protected_star), 0)

        visible_text = VisibleTextParser()
        visible_text.feed(self.page.replace(protected_star, ""))
        unprotected = "".join(visible_text.parts)
        self.assertNotIn("*", unprotected)
        self.assertNotIn("∗", unprotected)

        raw_data = correspondence.DATA.read_text(encoding="utf-8")
        self.assertIn('"book_color_signature": "*', raw_data)
        self.assertNotIn("∗", raw_data)

        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".orbifold-star {", css)
        self.assertIn('"STIX Two Math", "Cambria Math"', css)
        self.assertIn("vertical-align: baseline", css)

    def test_short_signature_source_links_are_visually_quiet_at_rest(self) -> None:
        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        resting_rule = css.split(".short-signature-link {", 1)[1].split("}", 1)[0]
        self.assertIn("text-decoration: none", resting_rule)
        self.assertIn(".short-signature-link:hover,", css)
        heading_icon_rule = css.split(
            "a.short-signature-link[data-book-excerpt]::after {", 1
        )[1].split("}", 1)[0]
        self.assertIn("content: none", heading_icon_rule)

    def test_every_example_displays_chaims_full_group_presentation(self) -> None:
        page_ids = [group["id"] for group in self.page_groups]
        self.assertEqual(self.parser.presentation_tables, page_ids)
        self.assertEqual(
            self.parser.presentation_generator_count,
            sum(
                len(group["chaim_presentation"]["generators"])
                for group in self.page_groups
            ),
        )
        self.assertEqual(self.parser.presentation_generator_count, 199)
        expected_time_shifts = [
            generator["time_shift"]
            for group in self.page_groups
            for generator in group["chaim_presentation"]["generators"]
        ]
        self.assertEqual(
            self.parser.presentation_time_shifts,
            expected_time_shifts,
        )
        self.assertEqual(
            self.parser.presentation_clock_powers,
            [
                str(generator["clock_power"])
                for group in self.page_groups
                for generator in group["chaim_presentation"]["generators"]
            ],
        )
        self.assertEqual(
            self.parser.presentation_source_cycles,
            [
                generator["source_cycle_notation"]
                for group in self.page_groups
                for generator in group["chaim_presentation"]["generators"]
            ],
        )
        self.assertEqual(
            Counter(
                generator["time_shift_label"]
                for group in self.page_groups
                for generator in group["chaim_presentation"]["generators"]
            ),
            Counter(
                {
                    "none": 95,
                    "+1/2 period": 77,
                    "+1/3 period": 7,
                    "+2/3 period": 9,
                    "+1/4 period": 6,
                    "+3/4 period": 3,
                    "+1/6 period": 1,
                    "+5/6 period": 1,
                }
            ),
        )
        self.assertEqual(
            self.page.count('class="group-presentation"'),
            len(self.page_groups),
        )
        self.assertEqual(
            self.page.count('<th scope="col">Color</th>'),
            len(self.page_groups),
        )
        self.assertEqual(
            self.page.count('<th scope="col">Time</th>'),
            len(self.page_groups),
        )
        self.assertEqual(
            self.page.count('class="presentation-colour-action"'),
            self.parser.presentation_generator_count,
        )
        identity_actions = sum(
            generator["clock_power"] % group["clock_order"] == 0
            for group in self.page_groups
            for generator in group["chaim_presentation"]["generators"]
        )
        self.assertEqual(
            len(
                re.findall(
                    r'<td class="presentation-colour-action"[^>]*data-clock-power="0"[^>]*>none</td>',
                    self.page,
                )
            ),
            identity_actions,
        )
        self.assertEqual(
            self.page.count('class="presentation-time-action"'),
            self.parser.presentation_generator_count,
        )
        self.assertEqual(
            self.parser.presentation_generator_keys,
            self.parser.presentation_generator_count,
        )
        self.assertEqual(
            self.parser.presentation_generator_geometries,
            self.parser.presentation_generator_count,
        )
        self.assertNotIn("presentation-generator-marker", self.page)
        for group_id in page_ids:
            table_start = self.page.index(f'<table data-presentation="{group_id}"')
            table_end = self.page.index("</table>", table_start)
            self.assertNotIn("<svg", self.page[table_start:table_end], group_id)
        self.assertEqual(
            self.page.count(">Presentation</h4>"),
            len(self.page_groups),
        )
        self.assertEqual(
            self.page.count('<strong>Relations</strong>'),
            len(self.page_groups),
        )
        self.assertNotIn("Geometric generators and their powers", self.page)
        self.assertNotIn("A, B, … form a minimal set", self.page)
        self.assertNotIn("superscripts mark powers", self.page)
        self.assertNotIn("about centre", self.page)
        self.assertNotIn("axis direction A", self.page)
        self.assertNotIn("axis direction B", self.page)
        self.assertNotIn("G/Λ =", self.page)
        self.assertEqual(
            self.page.count("Γ = ⟨"),
            len(self.page_groups),
        )

        for group in self.payload["groups"]:
            # The old finite quotient remains an internal render check, but it
            # is no longer mislabeled as the visible group presentation.
            expected_cell = correspondence.cell_action_presentation(
                group["id"], group["render"], group["parent"]["hm"]
            )
            self.assertEqual(
                group["cell_action_presentation"], expected_cell, group["id"]
            )
            for generator in expected_cell["generators"]:
                phase = correspondence.Fraction(generator["phase"])
                self.assertEqual(
                    group["clock_order"] % phase.denominator,
                    0,
                    group["id"],
                )
                self.assertTrue(generator["operation"])
                self.assertTrue(generator["time_shift"])

            expected_chaim = correspondence.chaim_presentation(
                group["id"],
                group["parent"]["hm"],
                group["clock_order"],
                group["tos_notation"],
                group["book_color_signature"],
                group["render"],
            )
            self.assertEqual(group["chaim_presentation"], expected_chaim, group["id"])
            source_presentation = correspondence.group_presentation(
                group["parent"]["hm"]
            )
            self.assertEqual(
                [row["generator"] for row in expected_chaim["generators"]],
                source_presentation["generators"],
                group["id"],
            )
            self.assertEqual(
                expected_chaim["relations"],
                source_presentation["relations"],
                group["id"],
            )
            clock_cycle = tuple(expected_chaim["clock_cycle"]["permutation"])
            self.assertEqual(
                clock_cycle,
                tuple(
                    (index + 1) % group["clock_order"]
                    for index in range(group["clock_order"])
                ),
                group["id"],
            )
            self.assertEqual(
                correspondence._permutation_order(clock_cycle),
                group["clock_order"],
                group["id"],
            )
            fixed_labels = [
                chr(ord("A") + index)
                for index in range(group["clock_order"])
            ]
            self.assertEqual(
                expected_chaim["colour_labels"],
                fixed_labels,
                group["id"],
            )
            self.assertEqual(
                [residue["colour_label"] for residue in group["phase_residues"]],
                fixed_labels,
                group["id"],
            )
            source_labels = [
                ord(label) - ord("A")
                for label in expected_chaim["source_labeling"][
                    "labels_by_fixed_phase"
                ]
            ]
            for generator in expected_chaim["generators"]:
                time_shift = correspondence.Fraction(generator["time_shift"])
                exponent = time_shift * group["clock_order"]
                self.assertEqual(exponent.denominator, 1, group["id"])
                self.assertEqual(
                    generator["clock_power"],
                    exponent.numerator % group["clock_order"],
                    f'{group["id"]}:{generator["generator"]}',
                )
                self.assertEqual(
                    correspondence._colour_permutation_power(
                        clock_cycle,
                        generator["clock_power"],
                    ),
                    tuple(generator["colour_permutation"]),
                    f'{group["id"]}:{generator["generator"]}',
                )
                self.assertEqual(
                    generator["cycle_notation"],
                    correspondence._permutation_notation(
                        generator["colour_permutation"]
                    ),
                    f'{group["id"]}:{generator["generator"]}',
                )
                source_permutation = tuple(generator["source_colour_permutation"])
                fixed_permutation = tuple(generator["colour_permutation"])
                for index in range(group["clock_order"]):
                    self.assertEqual(
                        source_permutation[source_labels[index]],
                        source_labels[fixed_permutation[index]],
                        f'{group["id"]}:{generator["generator"]}',
                    )
                self.assertEqual(
                    generator["time_shift_label"],
                    correspondence._time_shift_description(time_shift),
                    group["id"],
                )
                self.assertEqual(
                    group["clock_order"] % time_shift.denominator,
                    0,
                    group["id"],
                )
            if group["clock_order"] > 1:
                self.assertEqual(
                    tuple(superscript_orders(group["book_color_signature"])),
                    tuple(
                        correspondence._permutation_order(row["colour_permutation"])
                        for row in expected_chaim["generators"]
                    ),
                    group["id"],
                )

        by_id = {group["id"]: group for group in self.page_groups}
        self.assertEqual(
            set(correspondence.CANONICAL_TO_RENDER_CONJUGACY_BY_ID),
            set(by_id),
        )
        for group_id, clock_powers in FIXED_CLOCK_POWER_FIXTURE.items():
            presentation = by_id[group_id]["chaim_presentation"]
            self.assertEqual(
                [row["clock_power"] for row in presentation["generators"]],
                clock_powers,
                group_id,
            )
        nonidentity_source_labels = {
            group["id"]: group["chaim_presentation"]["source_labeling"][
                "labels_by_fixed_phase"
            ]
            for group in self.payload["groups"]
            if group["chaim_presentation"]["source_labeling"][
                "labels_by_fixed_phase"
            ]
            != group["chaim_presentation"]["colour_labels"]
        }
        self.assertEqual(nonidentity_source_labels, SOURCE_LABELING_FIXTURE)

        g225 = by_id["g225"]["chaim_presentation"]
        self.assertEqual(
            [row["generator"] for row in g225["generators"]],
            ["α", "β", "γ"],
        )
        self.assertEqual(
            [row["cycle_notation"] for row in g225["generators"]],
            ["(ACB)", "(ACB)", "(ACB)"],
        )
        self.assertEqual(
            [row["source_cycle_notation"] for row in g225["generators"]],
            ["(ABC)", "(ABC)", "(ABC)"],
        )
        self.assertEqual(
            [row["time_shift_label"] for row in g225["generators"]],
            ["+2/3 period", "+2/3 period", "+2/3 period"],
        )
        self.assertEqual(g225["relations"], "α³ = β³ = γ³ = αβγ = 1")

        g225_start = self.page.index(
            '<section class="correspondence-entry" id="g225"'
        )
        g225_end = self.page.index(
            '<section class="correspondence-entry" id="g226"'
        )
        g225_html = self.page[g225_start:g225_end]
        self.assertEqual(g225_html.count('class="presentation-generator-row"'), 3)
        self.assertEqual(g225_html.count(">+2/3 period</td>"), 3)
        self.assertEqual(g225_html.count('data-clock-power="2"'), 3)
        self.assertEqual(g225_html.count("<var>C</var><sub>3</sub><sup>2</sup>"), 3)
        self.assertIn("Γ = ⟨α, β, γ | α³ = β³ = γ³ = αβγ = 1⟩", g225_html)
        self.assertNotIn("G/Λ", g225_html)

        self.assertEqual(
            [row["generator"] for row in by_id["g244"]["chaim_presentation"]["generators"]],
            ["α", "β", "γ"],
        )
        self.assertEqual(
            [row["marker"] for row in by_id["g244"]["chaim_presentation"]["generators"]],
            [
                {"kind": "rotation", "order": 6},
                {"kind": "rotation", "order": 3},
                {"kind": "rotation", "order": 2},
            ],
        )
        self.assertEqual(
            [
                (row["clock_power"], row["time_shift"])
                for row in by_id["g244"]["chaim_presentation"]["generators"]
            ],
            [(1, "1/3"), (2, "2/3"), (0, "0")],
        )
        self.assertEqual(
            [row["cycle_notation"] for row in by_id["g227"]["chaim_presentation"]["generators"]],
            ["(ABC)", "(ACB)", "1"],
        )
        self.assertEqual(
            [
                row["time_shift_label"]
                for row in by_id["g227"]["chaim_presentation"]["generators"]
            ],
            ["+1/3 period", "+2/3 period", "none"],
        )
        self.assertEqual(
            by_id["g227"]["signature_evidence"]["generator_relabeling"],
            {"α": "fable β", "β": "fable γ", "γ": "fable α"},
        )
        self.assertEqual(
            [row["generator"] for row in by_id["g269"]["chaim_presentation"]["generators"]],
            ["P", "Q", "R"],
        )
        self.assertTrue(
            all(
                row["marker"]["kind"] == "mirror"
                for row in by_id["g269"]["chaim_presentation"]["generators"]
            )
        )
        self.assertEqual(
            by_id["g75"]["chaim_presentation"]["generators"][-1]["generator"],
            "Z",
        )
        self.assertEqual(
            by_id["g75"]["chaim_presentation"]["generators"][-1]["marker"]["kind"],
            "glide",
        )
        self.assertEqual(
            correspondence.THREE_COLOUR_ACTION_CODES["*333³//◦"],
            ("AB", "BC", "CA"),
        )

        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".group-presentation table", css)
        self.assertIn(".presentation-relations", css)
        self.assertIn(".presentation-generator-identity", css)
        self.assertNotIn(".presentation-generator-marker", css)
        self.assertNotIn(".presentation-mirror-line", css)
        self.assertNotIn(".presentation-generator-glide", css)
        self.assertNotIn(".presentation-glide-half-arrow", css)
        self.assertNotIn(".presentation-translation-arrow", css)
        self.assertIn(".generator-symbol-core", css)
        self.assertIn(".generator-symbol-body .generator-symbol-arms", css)
        self.assertIn('data-rotation-order="3"', self.page)
        self.assertIn('data-rotation-order="6"', self.page)
        self.assertIn("font-variant-numeric: tabular-nums", css)
        self.assertIn("@media (max-width: 430px)", css)
        self.assertIn(".directory-families", css)
        self.assertIn(".directory-groups", css)
        self.assertIn("flex-wrap: wrap", css)
        self.assertIn("overflow-x: auto", css)
        self.assertIn(".directory-palette span", css)
        self.assertRegex(css, r"\.directory\s*\{[^}]*display: block;")
        self.assertIn("?v=compact-generator-actions-v1", self.page)

    def test_page_reflows_below_the_shared_320px_viewport_floor(self) -> None:
        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )

        # Android display or page zoom can make the effective layout viewport
        # narrower than the shared stylesheet's historical 320px body floor.
        # The page must remove that floor, then keep its longest heading word
        # from recreating root-level horizontal overflow at those widths.
        self.assertRegex(
            css,
            r"(?ms)^body\s*\{\s*min-width:\s*0;\s*\}",
        )

        mobile = re.search(
            r"(?ms)^@media \(max-width: 430px\) \{(?P<rules>.*?)^\}",
            css,
        )
        if mobile is None:
            self.fail("missing max-width: 430px correspondence rules")
        heading = re.search(
            r"\.directory h1\s*\{(?P<declarations>[^}]*)\}",
            mobile.group("rules"),
        )
        if heading is None:
            self.fail("missing narrow-viewport .directory h1 rule")
        declarations = heading.group("declarations")
        self.assertIn("font-size: clamp(2rem, 11.5vw, 2.35rem);", declarations)
        self.assertIn("overflow-wrap: anywhere;", declarations)

        self.assertEqual(
            correspondence.CORRESPONDENCE_STYLE_SRC,
            "clockwork-coloring-correspondence.css?"
            "v=compact-generator-actions-v1",
        )
        self.assertIn(
            f'href="{correspondence.CORRESPONDENCE_STYLE_SRC}"',
            self.page,
        )

    def test_visual_viewport_reflow_constrains_the_visible_mobile_slice(self) -> None:
        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )

        # Android page zoom may leave a 320px layout viewport while exposing a
        # narrower VisualViewport.  Both top-level containers must use that
        # visible width and stay left-anchored; centering would clip both sides.
        containers = re.search(
            r"(?ms)^:root\[data-visual-viewport-constrained\] \.header-inner,\s*"
            r"^:root\[data-visual-viewport-constrained\] \.correspondence-page\s*"
            r"\{(?P<declarations>.*?)^\}",
            css,
        )
        if containers is None:
            self.fail("missing VisualViewport-constrained page containers")
        declarations = containers.group("declarations")
        self.assertRegex(
            declarations,
            r"width:\s*min\(\s*calc\(var\(--clockwork-visual-viewport-width\)\s*"
            r"-\s*1\.25rem\),\s*var\(--content\)\s*\);",
        )
        self.assertIn("margin-right: auto;", declarations)
        self.assertIn("margin-left: 0.625rem;", declarations)
        self.assertRegex(
            css,
            r"(?ms)^:root\[data-visual-viewport-constrained\] \.directory h1\s*"
            r"\{[^}]*overflow-wrap:\s*anywhere;[^}]*\}",
        )

        bootstrap_tag = (
            "  <script data-mobile-viewport-bootstrap>\n"
            f"{correspondence.MOBILE_VIEWPORT_BOOTSTRAP}\n"
            "  </script>"
        )
        self.assertEqual(self.parser.mobile_viewport_bootstraps, 1)
        self.assertEqual(self.page.count("<script data-mobile-viewport-bootstrap>"), 1)
        self.assertIn(bootstrap_tag, self.page)
        self.assertLess(
            self.page.index("<script data-mobile-viewport-bootstrap>"),
            self.page.index('href="site-controls-v2.css"'),
        )
        self.assertLess(
            self.page.index("<script data-mobile-viewport-bootstrap>"),
            self.page.index(f'href="{correspondence.CORRESPONDENCE_STYLE_SRC}"'),
        )

        # Execute the generated inline bootstrap with a small DOM mock. This
        # verifies its synchronous first commit, finite/positive fallback,
        # Math.min cap, and rAF-coalesced passive resize listeners.
        node_script = r"""
import fs from "node:fs";

const page = fs.readFileSync("clockwork-coloring-correspondence.html", "utf8");
const marker = "<script data-mobile-viewport-bootstrap>";
const tagStart = page.indexOf(marker);
const scriptStart = page.indexOf(">", tagStart) + 1;
const scriptEnd = page.indexOf("</script>", scriptStart);
if (tagStart < 0 || scriptStart <= 0 || scriptEnd < 0) {
  throw new Error("generated mobile viewport bootstrap not found");
}
const implementation = page.slice(scriptStart, scriptEnd);

const attributes = new Set();
const properties = new Map();
const root = {
  toggleAttribute(name, force) {
    if (force) attributes.add(name);
    else attributes.delete(name);
  },
  style: {
    setProperty(name, value) { properties.set(name, value); },
    removeProperty(name) { properties.delete(name); },
  },
};
const listeners = { window: new Map(), visualViewport: new Map() };
const frames = new Map();
let nextFrame = 1;
const visualViewport = {
  width: 300,
  addEventListener(type, callback, options) {
    listeners.visualViewport.set(type, { callback, options });
  },
};
globalThis.document = { documentElement: root };
globalThis.window = {
  innerWidth: 320,
  visualViewport,
  requestAnimationFrame(callback) {
    const id = nextFrame++;
    frames.set(id, callback);
    return id;
  },
  addEventListener(type, callback, options) {
    listeners.window.set(type, { callback, options });
  },
};

function snapshot() {
  return {
    constrained: attributes.has("data-visual-viewport-constrained"),
    width: properties.get("--clockwork-visual-viewport-width") ?? null,
  };
}

function flushAnimationFrames() {
  const callbacks = [...frames.values()];
  frames.clear();
  for (const callback of callbacks) callback();
}

eval(implementation);
const initial = snapshot();
const initialFrames = frames.size;

window.visualViewport.width = 280;
listeners.visualViewport.get("resize").callback();
listeners.window.get("resize").callback();
const coalescedFrames = frames.size;
const beforeFlush = snapshot();
flushAnimationFrames();
const narrowed = snapshot();

window.visualViewport.width = 319.5;
listeners.visualViewport.get("resize").callback();
flushAnimationFrames();
const withinEpsilon = snapshot();

window.visualViewport.width = 400;
listeners.window.get("resize").callback();
flushAnimationFrames();
const cappedAtLayout = snapshot();

window.visualViewport.width = 0;
listeners.visualViewport.get("resize").callback();
flushAnimationFrames();
const nonPositive = snapshot();

window.visualViewport.width = Number.NaN;
listeners.visualViewport.get("resize").callback();
flushAnimationFrames();
const invalid = snapshot();

window.innerWidth = 360;
window.visualViewport.width = 300;
listeners.window.get("resize").callback();
flushAnimationFrames();
const resizedLayout = snapshot();

window.innerWidth = 620;
window.visualViewport.width = 300;
listeners.window.get("resize").callback();
flushAnimationFrames();
const mobileBoundary = snapshot();

window.innerWidth = 621;
listeners.window.get("resize").callback();
flushAnimationFrames();
const aboveMobileBoundary = snapshot();

window.innerWidth = 800;
window.visualViewport.width = 600;
listeners.visualViewport.get("resize").callback();
flushAnimationFrames();
const desktopZoom = snapshot();

process.stdout.write(JSON.stringify({
  initial,
  initialFrames,
  coalescedFrames,
  beforeFlush,
  withinEpsilon,
  narrowed,
  cappedAtLayout,
  nonPositive,
  invalid,
  resizedLayout,
  mobileBoundary,
  aboveMobileBoundary,
  desktopZoom,
  windowPassive: listeners.window.get("resize").options.passive,
  visualViewportPassive:
    listeners.visualViewport.get("resize").options.passive,
  sharedResizeCallback:
    listeners.window.get("resize").callback
      === listeners.visualViewport.get("resize").callback,
}));
"""
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(
            report["initial"],
            {"constrained": True, "width": "300px"},
        )
        self.assertEqual(report["initialFrames"], 0)
        self.assertEqual(report["coalescedFrames"], 1)
        self.assertEqual(
            report["beforeFlush"],
            {"constrained": True, "width": "300px"},
        )
        self.assertEqual(
            report["narrowed"],
            {"constrained": True, "width": "280px"},
        )
        for state in ("withinEpsilon", "cappedAtLayout", "nonPositive", "invalid"):
            self.assertEqual(
                report[state],
                {"constrained": False, "width": None},
                state,
            )
        self.assertEqual(
            report["resizedLayout"],
            {"constrained": True, "width": "300px"},
        )
        self.assertEqual(
            report["mobileBoundary"],
            {"constrained": True, "width": "300px"},
        )
        self.assertEqual(
            report["aboveMobileBoundary"],
            {"constrained": False, "width": None},
        )
        self.assertEqual(
            report["desktopZoom"],
            {"constrained": False, "width": None},
        )
        self.assertTrue(report["windowPassive"])
        self.assertTrue(report["visualViewportPassive"])
        self.assertTrue(report["sharedResizeCallback"])

        expected_version = "compact-generator-actions-v1"
        self.assertEqual(
            correspondence.CORRESPONDENCE_STYLE_SRC,
            f"clockwork-coloring-correspondence.css?v={expected_version}",
        )
        self.assertEqual(
            correspondence.CORRESPONDENCE_SCRIPT_SRC,
            "clockwork-coloring-correspondence.js?v=reflection-centering-v1",
        )
        self.assertIn(
            f'href="{correspondence.CORRESPONDENCE_STYLE_SRC}"',
            self.page,
        )
        self.assertIn(
            f'src="{correspondence.CORRESPONDENCE_SCRIPT_SRC}"',
            self.page,
        )

    def test_intro_is_one_concise_three_visualization_sentence(self) -> None:
        intro = (
            "Each group has three corresponding visualizations: a clockwork "
            "animation, a static 2D colouring, and an interactive crystal model "
            "in the associated polar space group."
        )
        self.assertEqual(self.page.count(intro), 1)
        self.assertIn(
            f'<p class="directory-viewer-note">{intro}</p>',
            self.page,
        )
        for retired_copy in (
            "Colors follow one fixed clock",
            "A = phase 0",
            "Every action is a forward time skip",
            "Raised numbers in the signature give colour-permutation orders",
            "Every record now carries the same three-part visual trail",
        ):
            self.assertNotIn(retired_copy, self.page)
        self.assertNotIn('class="directory-legend"', self.page)
        self.assertEqual(
            self.page.count('class="colour-order colour-order--presentation"'),
            len(self.page_groups),
        )
        self.assertNotIn('class="presentation-cyclic-key"', self.page)
        self.assertNotIn("A row with Time +k/", self.page)
        self.assertNotIn("is shown as “none.”", self.page)
        self.assertNotIn(
            "C<sub>N</sub> is a color/time cycle, not a spatial rotation,",
            self.page,
        )
        self.assertEqual(
            self.page.count("fixed-clock powers and directed time shifts"),
            len(self.page_groups),
        )

    def test_colour_legends_keep_the_palette_and_add_plate_only_forward_actions(
        self,
    ) -> None:
        expected_swatches = sum(
            group["clock_order"] for group in self.page_groups
        )
        self.assertEqual(expected_swatches, 149)
        self.assertEqual(
            self.page.count('class="colour-order colour-order--plate"'),
            len(self.page_groups),
        )
        self.assertEqual(
            self.page.count('class="colour-order colour-order--presentation"'),
            len(self.page_groups),
        )
        self.assertEqual(
            self.page.count('role="img" aria-label="Colour order:'),
            2 * len(self.page_groups),
        )
        self.assertEqual(
            self.page.count(
                '<span class="colour-order-label">order</span>'
            ),
            2 * len(self.page_groups),
        )
        self.assertEqual(
            self.page.count(
                '<span class="colour-order-palette" aria-hidden="true">'
            ),
            2 * len(self.page_groups),
        )
        self.assertEqual(
            self.page.count('class="colour-order-swatch"'),
            2 * expected_swatches,
        )

        expected_order_sequence = [
            (group, placement)
            for group in self.page_groups
            for placement in ("plate", "presentation")
        ]
        self.assertEqual(
            [placement for placement, _attributes, _text in self.parser.colour_orders],
            [placement for _group, placement in expected_order_sequence],
        )
        actions_by_order: defaultdict[
            int, list[dict[str, str | None]]
        ] = defaultdict(list)
        for order_index, attributes in self.parser.colour_order_actions:
            self.assertIsNotNone(order_index)
            actions_by_order[order_index or 0].append(attributes)
        svgs_by_order: defaultdict[
            int, list[dict[str, str | None]]
        ] = defaultdict(list)
        for order_index, attributes in self.parser.colour_order_action_svgs:
            self.assertIsNotNone(order_index)
            svgs_by_order[order_index or 0].append(attributes)

        expected_action_count = sum(
            len(FORWARD_COLOUR_ACTION_FIXTURE.get(group["id"], ()))
            for group in self.page_groups
        )
        self.assertEqual(expected_action_count, 62)
        self.assertEqual(len(self.parser.colour_order_actions), 62)
        self.assertEqual(len(self.parser.colour_order_action_svgs), 62)

        accessible_turns = {
            2: "half-turn",
            3: "one-third turn",
            4: "quarter-turn",
            6: "one-sixth turn",
        }
        accessible_palette_steps = {
            2: "one-half",
            3: "one-third",
            4: "one-quarter",
            6: "one-sixth",
        }
        plane_names = {
            "plane-c": "c-glide-plane symbol",
            "plane-n": "n-glide-plane symbol",
            "plane-d": "d-glide-plane symbol",
        }

        for order_index, (group, placement) in enumerate(expected_order_sequence):
            section_start = self.page.index(
                f'<section class="correspondence-entry" id="{group["id"]}"'
            )
            section_end = self.page.index("</section>", section_start)
            section = self.page[section_start:section_end]
            expected_html = correspondence._colour_order_html(group, placement)
            self.assertIn(expected_html, section, group["id"])
            parsed_placement, attributes, text_parts = self.parser.colour_orders[
                order_index
            ]
            self.assertEqual(parsed_placement, placement)
            palette_names = [
                correspondence.PALETTE_NAME_BY_COLOR[residue["color"]]
                for residue in group["phase_residues"]
            ]
            palette_label = "Colour order: " + ", ".join(palette_names)
            expected_actions = (
                FORWARD_COLOUR_ACTION_FIXTURE.get(group["id"], ())
                if placement == "plate"
                else ()
            )
            if expected_actions:
                accessible_pairs = []
                for kind, symbol, _source, direction, description in expected_actions:
                    if kind == "rotation":
                        _rotation, order, step = symbol.split("-")
                        symbol_name = f"{order} subscript {step} screw-axis symbol"
                        spatial_order = int(order)
                        accessible_description = (
                            f"{accessible_turns[spatial_order]} {direction}"
                        )
                        if spatial_order != group["clock_order"]:
                            palette_step = accessible_palette_steps[
                                group["clock_order"]
                            ]
                            accessible_description += (
                                ", with colour advancing by "
                                f"{palette_step} of the fixed palette cycle"
                            )
                    else:
                        symbol_name = plane_names[symbol]
                        accessible_description = description
                    accessible_pairs.append(
                        f"{symbol_name}, {accessible_description}"
                    )
                prefix = (
                    "Symbol advancing the displayed colour order by one step "
                    "as polar height increases"
                    if len(accessible_pairs) == 1
                    else "Symbols each advancing the displayed colour order by "
                    "one step as polar height increases"
                )
                expected_aria = (
                    f"{palette_label}. {prefix}: "
                    + "; ".join(accessible_pairs)
                    + "."
                )
            else:
                expected_aria = palette_label
            self.assertEqual(attributes.get("role"), "img")
            self.assertEqual(attributes.get("aria-label"), expected_aria)

            actual_actions = actions_by_order[order_index]
            self.assertEqual(
                [
                    (
                        row.get("data-action-kind"),
                        row.get("data-forward-symbol"),
                        row.get("data-palette-step-source"),
                        row.get("data-polar-turn-direction") or "",
                        row.get("data-turn-description")
                        or (
                            "colour reflection"
                            if row.get("data-forward-symbol") == "plane-c"
                            else "colour glide reflection"
                        ),
                    )
                    for row in actual_actions
                ],
                list(expected_actions),
                f'{group["id"]}:{placement}',
            )
            self.assertEqual(
                len(svgs_by_order[order_index]),
                len(expected_actions),
                f'{group["id"]}:{placement}',
            )
            for attributes, svg, expected_action in zip(
                actual_actions,
                svgs_by_order[order_index],
                expected_actions,
                strict=True,
            ):
                kind, symbol, source, direction, description = expected_action
                action_classes = set((attributes.get("class") or "").split())
                self.assertEqual(
                    action_classes,
                    {"colour-order-action", f"colour-order-action--{kind}"},
                )
                self.assertEqual(attributes.get("data-forward-symbol"), symbol)
                self.assertEqual(attributes.get("data-action-kind"), kind)
                self.assertEqual(attributes.get("data-palette-step-source"), source)
                self.assertEqual(svg.get("aria-hidden"), "true")
                self.assertEqual(svg.get("focusable"), "false")
                svg_classes = set((svg.get("class") or "").split())
                self.assertEqual(
                    svg_classes,
                    {
                        "colour-order-action-glyph",
                        f"colour-order-action-glyph--{kind}",
                    },
                )
                if kind == "rotation":
                    self.assertEqual(svg.get("viewbox"), "0 0 32 32")
                    self.assertEqual(svg.get("data-rotation-symbol"), symbol)
                    self.assertEqual(
                        attributes.get("data-forward-rotation-symbol"), symbol
                    )
                    self.assertEqual(
                        attributes.get("data-polar-turn-direction"), direction
                    )
                    self.assertEqual(
                        attributes.get("data-turn-description"), description
                    )
                    self.assertNotIn("data-forward-plane-symbol", attributes)
                else:
                    self.assertEqual(svg.get("viewbox"), "0 0 48 32")
                    self.assertEqual(
                        svg.get("data-plane-symbol"), symbol.removeprefix("plane-")
                    )
                    self.assertEqual(
                        attributes.get("data-forward-plane-symbol"), symbol
                    )
                    self.assertNotIn("data-forward-rotation-symbol", attributes)
                    self.assertNotIn("data-polar-turn-direction", attributes)
                    self.assertNotIn("data-turn-description", attributes)

            visible_parts = [part.strip() for part in text_parts if part.strip()]
            self.assertEqual(
                visible_parts,
                [
                    "order",
                    *(
                        description
                        for _kind, _symbol, _source, _direction, description
                        in expected_actions
                    ),
                ],
                f'{group["id"]}:{placement}',
            )
            if placement == "presentation":
                self.assertNotIn("<svg", expected_html, group["id"])
                self.assertNotIn("data-forward-symbol", expected_html)
                self.assertNotIn("data-forward-rotation-symbol", expected_html)
                self.assertNotIn("data-forward-plane-symbol", expected_html)
                self.assertNotIn("data-polar-turn-direction", expected_html)

        self.assertNotIn('class="colour-key"', self.page)
        self.assertNotIn('class="presentation-palette"', self.page)
        self.assertNotIn('class="presentation-colour"', self.page)
        self.assertNotIn(" · phase ", self.page)
        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".colour-order--plate", css)
        self.assertIn(".colour-order--presentation", css)
        self.assertIn(".colour-order-palette", css)
        self.assertIn(".colour-order-swatch", css)
        self.assertIn(".colour-order-action", css)
        self.assertIn(".colour-order-action-glyph--rotation", css)
        self.assertIn(".colour-order-action-glyph--reflection", css)
        self.assertIn(".colour-order-action-description", css)
        self.assertNotIn(".colour-order-rotation", css)
        self.assertIn("border-radius: 2px", css)
        self.assertNotIn(".colour-key", css)
        self.assertNotIn(".presentation-colour {", css)
        self.assertNotIn(".presentation-colour i", css)

        # Standard mobile widths keep the complete key on the palette line;
        # only unusually narrow viewports may wrap whole, indivisible actions.
        plate_rule = re.search(
            r"(?ms)^\.colour-order--plate\s*\{(?P<declarations>.*?)^\}",
            css,
        )
        self.assertIsNotNone(plate_rule)
        self.assertIn("flex-wrap: nowrap;", plate_rule.group("declarations"))
        action_rule = re.search(
            r"(?ms)^\.colour-order-action\s*\{(?P<declarations>.*?)^\}",
            css,
        )
        self.assertIsNotNone(action_rule)
        action_declarations = action_rule.group("declarations")
        self.assertIn("display: inline-flex;", action_declarations)
        self.assertIn("flex: none;", action_declarations)
        self.assertIn("white-space: nowrap;", action_declarations)
        self.assertRegex(
            css,
            r"(?ms)@media \(max-width: 620px\).*?\.colour-order--plate\s*\{"
            r"[^}]*font-size:\s*0\.6rem;",
        )
        self.assertRegex(
            css,
            r"(?ms)@media \(max-width: 410px\).*?\.colour-order--plate\s*\{"
            r"[^}]*flex-wrap:\s*wrap;",
        )

    def test_screw_drill_direction_follows_increasing_polar_height(self) -> None:
        cases = (
            (2, 1, "counterclockwise"),
            (3, 1, "counterclockwise"),
            (3, 2, "clockwise"),
            (4, 1, "counterclockwise"),
            (4, 2, "counterclockwise"),
            (4, 3, "clockwise"),
            (6, 1, "counterclockwise"),
            (6, 2, "counterclockwise"),
            (6, 3, "counterclockwise"),
            (6, 4, "clockwise"),
            (6, 5, "clockwise"),
        )
        for order, screw_step, direction in cases:
            with self.subTest(order=order, screw_step=screw_step):
                self.assertEqual(
                    correspondence._screw_drill_direction(order, screw_step),
                    direction,
                )

    def test_forward_turn_descriptions_separate_spatial_and_palette_fractions(
        self,
    ) -> None:
        cases = (
            (
                (3, 3, "clockwise"),
                ("1/3 turn CW", "one-third turn clockwise"),
            ),
            (
                (4, 2, "counterclockwise"),
                (
                    "1/4 turn CCW · colour +1/2",
                    "quarter-turn counterclockwise, with colour advancing by "
                    "one-half of the fixed palette cycle",
                ),
            ),
            (
                (6, 3, "counterclockwise"),
                (
                    "1/6 turn CCW · colour +1/3",
                    "one-sixth turn counterclockwise, with colour advancing by "
                    "one-third of the fixed palette cycle",
                ),
            ),
        )
        for inputs, expected in cases:
            with self.subTest(inputs=inputs):
                self.assertEqual(
                    correspondence._forward_turn_descriptions(*inputs),
                    expected,
                )

        invalid_cases = (
            (5, 3, "counterclockwise"),
            (3, 5, "counterclockwise"),
            (3, 3, "sideways"),
        )
        for inputs in invalid_cases:
            with self.subTest(inputs=inputs):
                with self.assertRaisesRegex(
                    ValueError,
                    "unsupported compact turn description",
                ):
                    correspondence._forward_turn_descriptions(*inputs)

    def test_forward_action_legend_uses_direct_or_inverse_one_step_and_deduplicates(
        self,
    ) -> None:
        derived_fixture: dict[
            str, tuple[tuple[str, str, str, str, str], ...]
        ] = {}
        item_census: Counter[int] = Counter()
        raw_match_counts: dict[str, int] = {}
        for group in self.page_groups:
            raw_matches = []
            semantic_items = []
            seen_symbols: dict[str, tuple[str, str, str, str]] = {}
            for generator in group["chaim_presentation"]["generators"]:
                if group["clock_order"] <= 1:
                    expected_source = None
                else:
                    clock_power = generator["clock_power"] % group["clock_order"]
                    if clock_power == 1:
                        expected_source = "direct"
                    elif clock_power == group["clock_order"] - 1:
                        expected_source = "inverse"
                    else:
                        expected_source = None
                self.assertEqual(
                    correspondence._one_step_source(group, generator),
                    expected_source,
                    f'{group["id"]}:{generator["generator"]}',
                )
                if expected_source is None:
                    continue
                raw_matches.append(generator)
                kind = generator["marker"]["kind"]
                if kind == "rotation":
                    order = generator["marker"]["order"]
                    angle = generator["plate_visualization"]["angle_degrees"]
                    screw_step = correspondence._rotation_screw_step(
                        order,
                        correspondence.Fraction(generator["time_shift"]),
                        angle,
                    )
                    symbol = f"rotation-{order}-{screw_step}"
                    direction = (
                        "counterclockwise"
                        if screw_step <= order / 2
                        else "clockwise"
                    )
                    direction_abbreviation = (
                        "CCW" if direction == "counterclockwise" else "CW"
                    )
                    description = f"1/{order} turn {direction_abbreviation}"
                    if order != group["clock_order"]:
                        description += f' · colour +1/{group["clock_order"]}'
                    fixture_kind = "rotation"
                elif kind in {"mirror", "glide"}:
                    plane_symbol = correspondence._polar_plane_symbol(
                        group["id"], generator
                    )
                    symbol = f"plane-{plane_symbol}"
                    direction = ""
                    description = (
                        "colour reflection"
                        if plane_symbol in {"m", "c"}
                        else "colour glide reflection"
                    )
                    fixture_kind = "reflection"
                else:
                    continue
                if symbol in seen_symbols:
                    self.assertEqual(
                        seen_symbols[symbol],
                        (fixture_kind, expected_source, direction, description),
                        f'{group["id"]}:{symbol}',
                    )
                    continue
                seen_symbols[symbol] = (
                    fixture_kind,
                    expected_source,
                    direction,
                    description,
                )
                semantic_items.append(
                    (
                        fixture_kind,
                        symbol,
                        expected_source,
                        direction,
                        description,
                    )
                )

            raw_match_counts[group["id"]] = len(raw_matches)
            expected_items = tuple(semantic_items)
            if expected_items:
                derived_fixture[group["id"]] = expected_items
            item_census[len(expected_items)] += 1

            rendered_items = correspondence._forward_colour_legend_items(group)
            self.assertLessEqual(len(rendered_items), 2, group["id"])
            self.assertEqual(
                tuple(
                    (
                        item["kind"],
                        item["symbol_key"],
                        item["source"],
                        item["polar_direction"],
                        item["description"],
                    )
                    for item in rendered_items
                ),
                expected_items,
                group["id"],
            )
            for item in rendered_items:
                self.assertEqual(
                    set(item),
                    {
                        "kind",
                        "symbol_key",
                        "source",
                        "polar_direction",
                        "description",
                        "accessible_description",
                        "accessible_name",
                        "symbol_html",
                    },
                    group["id"],
                )
                self.assertEqual(item["symbol_html"].count("<svg"), 1)
                if item["kind"] == "rotation":
                    _rotation, order, step = item["symbol_key"].split("-")
                    self.assertEqual(
                        item["accessible_name"],
                        f"{order} subscript {step} screw-axis symbol",
                    )
                    self.assertIn(
                        f'data-rotation-symbol="{item["symbol_key"]}"',
                        item["symbol_html"],
                    )
                else:
                    plane = item["symbol_key"].removeprefix("plane-")
                    self.assertIn(
                        f'data-plane-symbol="{plane}"', item["symbol_html"]
                    )

        self.assertEqual(derived_fixture, FORWARD_COLOUR_ACTION_FIXTURE)
        self.assertEqual(item_census, Counter({0: 18, 1: 38, 2: 12}))
        self.assertEqual(sum(size * count for size, count in item_census.items()), 62)
        self.assertEqual(
            Counter(
                kind
                for items in derived_fixture.values()
                for kind, _symbol, _source, _direction, _description in items
            ),
            Counter({"rotation": 34, "reflection": 28}),
        )
        self.assertEqual(
            Counter(
                source
                for items in derived_fixture.values()
                for _kind, _symbol, source, _direction, _description in items
            ),
            Counter({"direct": 54, "inverse": 8}),
        )
        self.assertEqual(
            Counter(
                direction
                for items in derived_fixture.values()
                for kind, _symbol, _source, direction, _description in items
                if kind == "rotation"
            ),
            Counter({"counterclockwise": 27, "clockwise": 7}),
        )
        rotation_items = [
            (group_id, symbol, description)
            for group_id, items in derived_fixture.items()
            for kind, symbol, _source, _direction, description in items
            if kind == "rotation"
        ]
        qualified_rotation_items = {
            (group_id, symbol)
            for group_id, symbol, description in rotation_items
            if " · colour +" in description
        }
        self.assertEqual(
            qualified_rotation_items,
            {
                ("g95", "rotation-4-2"),
                ("g98", "rotation-4-2"),
                ("g133", "rotation-4-2"),
                ("g134", "rotation-4-2"),
                ("g244", "rotation-6-2"),
                ("g245", "rotation-6-4"),
                ("g246", "rotation-6-3"),
            },
        )
        self.assertEqual(len(rotation_items), 34)
        self.assertEqual(len(qualified_rotation_items), 7)
        equal_fraction_items = [
            description
            for group_id, symbol, description in rotation_items
            if int(symbol.split("-")[1])
            == next(
                group["clock_order"]
                for group in self.page_groups
                if group["id"] == group_id
            )
        ]
        self.assertEqual(len(equal_fraction_items), 27)
        self.assertTrue(
            all("colour +" not in description for description in equal_fraction_items)
        )

        # Equivalent centres collapse to one symbol/action entry.
        self.assertEqual(raw_match_counts["g6"], 4)
        self.assertEqual(raw_match_counts["g226"], 3)
        self.assertEqual(raw_match_counts["g55"], 4)
        self.assertEqual(len(FORWARD_COLOUR_ACTION_FIXTURE["g6"]), 1)
        self.assertEqual(len(FORWARD_COLOUR_ACTION_FIXTURE["g226"]), 1)
        self.assertEqual(len(FORWARD_COLOUR_ACTION_FIXTURE["g55"]), 1)

        # No named generator or inverse advances g235's six-colour palette once.
        self.assertNotIn("g235", FORWARD_COLOUR_ACTION_FIXTURE)
        self.assertEqual(raw_match_counts["g235"], 0)

    def test_g225_uses_the_inverse_3_2_drill_to_advance_colours(self) -> None:
        group = next(group for group in self.page_groups if group["id"] == "g225")
        self.assertEqual(
            [
                (generator["clock_power"], generator["time_shift"])
                for generator in group["chaim_presentation"]["generators"]
            ],
            [(2, "2/3")] * 3,
        )
        self.assertEqual(
            FORWARD_COLOUR_ACTION_FIXTURE["g225"],
            (
                (
                    "rotation",
                    "rotation-3-2",
                    "inverse",
                    "clockwise",
                    "1/3 turn CW",
                ),
            ),
        )
        section_start = self.page.index(
            '<section class="correspondence-entry" id="g225"'
        )
        section_end = self.page.index("</section>", section_start)
        section = self.page[section_start:section_end]
        expected_aria = (
            "Colour order: blue, orange, green. Symbol advancing the displayed "
            "colour order by one step as polar height increases: 3 subscript 2 "
            "screw-axis symbol, one-third turn clockwise."
        )
        self.assertIn(f'role="img" aria-label="{expected_aria}"', section)
        self.assertIn(
            'data-forward-symbol="rotation-3-2" data-action-kind="rotation" '
            'data-palette-step-source="inverse" '
            'data-forward-rotation-symbol="rotation-3-2" '
            'data-polar-turn-direction="clockwise" '
            'data-turn-description="1/3 turn CW"',
            section,
        )

    def test_mismatched_turn_and_palette_fractions_are_explicit_and_accessible(
        self,
    ) -> None:
        cases = {
            "g95": (
                ("1/4 turn CCW · colour +1/2",),
                "Colour order: blue, orange. Symbol advancing the displayed "
                "colour order by one step as polar height increases: 4 "
                "subscript 2 screw-axis symbol, quarter-turn counterclockwise, "
                "with colour advancing by one-half of the fixed palette cycle.",
            ),
            "g244": (
                ("1/6 turn CCW · colour +1/3", "1/3 turn CW"),
                "Colour order: blue, orange, green. Symbols each advancing the "
                "displayed colour order by one step as polar height increases: "
                "6 subscript 2 screw-axis symbol, one-sixth turn "
                "counterclockwise, with colour advancing by one-third of the "
                "fixed palette cycle; 3 subscript 2 screw-axis symbol, "
                "one-third turn clockwise.",
            ),
            "g245": (
                ("1/6 turn CW · colour +1/3", "1/3 turn CCW"),
                "Colour order: blue, orange, green. Symbols each advancing the "
                "displayed colour order by one step as polar height increases: "
                "6 subscript 4 screw-axis symbol, one-sixth turn clockwise, "
                "with colour advancing by one-third of the fixed palette cycle; "
                "3 subscript 1 screw-axis symbol, one-third turn "
                "counterclockwise.",
            ),
            "g246": (
                ("1/6 turn CCW · colour +1/2", "1/2 turn CCW"),
                "Colour order: blue, orange. Symbols each advancing the displayed "
                "colour order by one step as polar height increases: 6 subscript "
                "3 screw-axis symbol, one-sixth turn counterclockwise, with colour "
                "advancing by one-half of the fixed palette cycle; 2 subscript 1 "
                "screw-axis symbol, half-turn counterclockwise.",
            ),
        }
        for group_id, (visible_labels, expected_aria) in cases.items():
            with self.subTest(group_id=group_id):
                section_start = self.page.index(
                    f'<section class="correspondence-entry" id="{group_id}"'
                )
                section_end = self.page.index("</section>", section_start)
                section = self.page[section_start:section_end]
                caption_start = section.index(
                    '<p class="colour-order colour-order--plate"'
                )
                caption_end = section.index("</p>", caption_start)
                caption = section[caption_start:caption_end]
                self.assertIn(
                    f'role="img" aria-label="{expected_aria}"',
                    caption,
                )
                self.assertEqual(
                    re.findall(r'data-turn-description="([^"]+)"', caption),
                    list(visible_labels),
                )
                for label in visible_labels:
                    self.assertIn(
                        '<span class="colour-order-action-description" '
                        f'aria-hidden="true">{label}</span>',
                        caption,
                    )

    def test_g9_keys_both_colour_reflections_and_g235_stays_honest(self) -> None:
        g9_start = self.page.index(
            '<section class="correspondence-entry" id="g9"'
        )
        g9_end = self.page.index("</section>", g9_start)
        g9 = self.page[g9_start:g9_end]
        expected_g9_aria = (
            "Colour order: blue, orange. Symbols each advancing the displayed "
            "colour order by one step as polar height increases: c-glide-plane "
            "symbol, colour reflection; n-glide-plane symbol, colour glide "
            "reflection."
        )
        self.assertIn(f'role="img" aria-label="{expected_g9_aria}"', g9)
        self.assertIn('data-forward-plane-symbol="plane-c"', g9)
        self.assertIn('data-forward-plane-symbol="plane-n"', g9)
        self.assertIn(">colour reflection</span>", g9)
        self.assertIn(">colour glide reflection</span>", g9)

        g235 = next(group for group in self.page_groups if group["id"] == "g235")
        self.assertEqual(
            [generator["clock_power"] for generator in g235["chaim_presentation"]["generators"]],
            [4, 3],
        )
        self.assertEqual(correspondence._forward_colour_legend_items(g235), [])
        g235_start = self.page.index(
            '<section class="correspondence-entry" id="g235"'
        )
        g235_end = self.page.index("</section>", g235_start)
        g235_section = self.page[g235_start:g235_end]
        plate_caption_start = g235_section.index(
            '<p class="colour-order colour-order--plate"'
        )
        plate_caption_end = g235_section.index("</p>", plate_caption_start)
        plate_caption = g235_section[plate_caption_start:plate_caption_end]
        self.assertNotIn("colour-order-action", plate_caption)
        self.assertNotIn("advancing the displayed colour order", plate_caption)

    def test_turn_hover_uses_one_counterclockwise_face_order_convention(self) -> None:
        turn_generators = [
            generator
            for group in self.page_groups
            for generator in group["chaim_presentation"]["generators"]
            if "turn" in generator["geometry"]
        ]
        self.assertEqual(len(turn_generators), 96)
        self.assertEqual(len(self.parser.turn_directions), len(turn_generators))
        self.assertEqual(
            Counter(
                generator["plate_visualization"]["angle_degrees"]
                for generator in turn_generators
            ),
            Counter({180: 50, 120: 18, 270: 10, 90: 8, 60: 6, 240: 4}),
        )

        for attributes in self.parser.turn_directions:
            self.assertEqual(
                attributes.get("data-turn-direction"),
                "counterclockwise",
            )
            self.assertNotIn("data-turn-degrees", attributes)
            self.assertEqual(attributes.get("tabindex"), "0")
            self.assertEqual(attributes.get("title"), correspondence.TURN_DIRECTION_HELP)
            self.assertEqual(
                attributes.get("aria-label"),
                f"turn: {correspondence.TURN_DIRECTION_HELP}",
            )
        self.assertEqual(
            self.page.count('class="turn-direction-tooltip" role="tooltip"'),
            len(turn_generators),
        )
        self.assertEqual(
            self.page.count(correspondence.TURN_DIRECTION_HELP),
            3 * len(turn_generators),
        )

        for parent in correspondence.BASE_ORDER:
            canonical = {
                generator["generator"]: generator
                for generator in correspondence.affine_generators_for(parent)[
                    "generators"
                ]
            }
            for name, geometry in correspondence.GENERATOR_GEOMETRY[parent]:
                if "turn" not in geometry:
                    continue
                angle = canonical[name]["visualization"]["angle_degrees"]
                self.assertGreater(angle, 0)
                self.assertLessEqual(angle, 180)

    def test_top_teaser_opens_complete_visual_crystallographic_index(self) -> None:
        self.assertEqual(self.parser.diagram_symbol_teasers, 1)
        self.assertEqual(self.parser.diagram_symbol_dialogs, 1)
        teaser_start = self.page.index('<aside class="diagram-symbol-teaser"')
        teaser_end = self.page.index("</aside>", teaser_start)
        teaser = self.page[teaser_start:teaser_end]
        start = self.page.index('<dialog class="diagram-symbol-dialog"')
        end = self.page.index("</dialog>", start)
        first_family = self.page.index('<section class="wallpaper-family"')
        legend = self.page[start:end]
        self.assertLess(teaser_start, first_family)
        self.assertLess(start, first_family)
        self.assertEqual(teaser.count("<svg"), 2)
        self.assertIn('data-legend-icon="rotation-3-1"', teaser)
        self.assertIn('data-legend-icon="plane-d"', teaser)
        self.assertIn("Open visual index", teaser)
        self.assertIn(
            "Translation, rotation, screw-axis, mirror, and glide marks",
            teaser,
        )

        self.assertEqual(
            self.parser.diagram_symbol_dialog_attributes,
            [
                {
                    "class": "diagram-symbol-dialog",
                    "id": "diagram-symbol-dialog",
                    "role": "dialog",
                    "aria-modal": "true",
                    "aria-labelledby": "diagram-symbol-dialog-title",
                }
            ],
        )
        self.assertNotIn("open", self.parser.diagram_symbol_dialog_attributes[0])
        self.assertEqual(len(self.parser.diagram_symbol_open_buttons), 1)
        self.assertEqual(
            self.parser.diagram_symbol_open_buttons[0].get("aria-haspopup"),
            "dialog",
        )
        self.assertEqual(
            self.parser.diagram_symbol_open_buttons[0].get("aria-controls"),
            "diagram-symbol-dialog",
        )
        self.assertEqual(len(self.parser.diagram_symbol_close_buttons), 1)
        self.assertEqual(
            self.parser.diagram_symbol_close_buttons[0].get("aria-label"),
            "Close visual index",
        )
        expected_symbols = [
            "translation",
            "rotation-2-0",
            "rotation-2-1",
            "rotation-3-0",
            "rotation-3-1",
            "rotation-3-2",
            "rotation-4-0",
            "rotation-4-1",
            "rotation-4-2",
            "rotation-4-3",
            "rotation-6-0",
            "rotation-6-1",
            "rotation-6-2",
            "rotation-6-3",
            "rotation-6-4",
            "rotation-6-5",
            "plane-m",
            "plane-axial",
            "plane-c",
            "plane-n",
            "plane-d",
        ]
        self.assertEqual(
            self.parser.diagram_legend_symbol_rows,
            [("li", symbol) for symbol in expected_symbols],
        )
        self.assertEqual(
            [
                row_index
                for row_index, _attributes in self.parser.diagram_legend_svgs
            ],
            list(range(len(expected_symbols))),
        )
        for row_index, attributes in self.parser.diagram_legend_svgs:
            self.assertTrue(attributes.get("viewbox"))
            self.assertEqual(attributes.get("aria-hidden"), "true")
            self.assertEqual(attributes.get("focusable"), "false")
            self.assertEqual(
                attributes.get("data-legend-icon"),
                expected_symbols[row_index],
            )
        self.assertEqual(legend.count("<svg"), len(expected_symbols))
        self.assertEqual(legend.count("data-legend-symbol="), len(expected_symbols))
        self.assertNotIn("data-generator-symbol=", legend)
        self.assertEqual(legend.count('class="diagram-symbol-list" role="list"'), 3)
        self.assertEqual(legend.count('role="img" aria-label='), 11)
        legend_symbols = [
            symbol for _tag, symbol in self.parser.diagram_legend_symbol_rows
        ]
        self.assertEqual(
            set(legend_symbols),
            set(self.parser.plate_generator_symbols),
        )
        self.assertTrue(
            all(count == 1 for count in Counter(legend_symbols).values())
        )
        for parts in self.parser.diagram_legend_row_texts:
            explanation = " ".join(" ".join(parts).split())
            self.assertGreaterEqual(len(explanation.split()), 3)
            self.assertLessEqual(len(explanation.split()), 24)

        visible = VisibleTextParser()
        visible.feed(legend)
        copy = " ".join(" ".join(visible.parts).split()).lower()
        for phrase in (
            "crystallographic generator symbols",
            "primitive translation",
            "2-fold",
            "3-fold",
            "4-fold",
            "6-fold",
            "screw",
            "mirror",
            "axial glide",
            "clock-axis glide",
            "diagonal n-glide",
            "quarter-diagonal d-glide",
        ):
            self.assertIn(phrase, copy)

        script = (ROOT / "clockwork-coloring-correspondence.js").read_text(
            encoding="utf-8"
        )
        controller_start = script.index("function initializeDiagramSymbolDialog()")
        controller_end = script.index("function initializeBookExcerptLinks()")
        controller = script[controller_start:controller_end]
        self.assertIn("dialog.showModal()", controller)
        self.assertIn("dialog.close()", controller)
        self.assertIn("event.target === dialog", controller)
        self.assertIn('event.key === "Escape"', controller)
        self.assertIn("opener.focus()", controller)
        self.assertIn("initializeDiagramSymbolDialog();", script)

        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".diagram-symbol-dialog::backdrop", css)
        self.assertIn(".diagram-symbol-dialog:not([open])", css)

    def test_visible_copy_is_orbifold_first_not_crystallographic(self) -> None:
        forbidden_terms = (
            "classified in",
            "triclinic",
            "monoclinic",
            "orthorhombic",
            "trigonal",
            "hexagonal",
            "bravais",
            "lattice",
            "symmorphic",
            "p31m/3 p3m1",
        )
        visible_parser = VisibleTextParser()
        page_without_identifications = re.sub(
            r'<section class="other-names".*?</section>',
            "",
            self.page,
            flags=re.DOTALL,
        )
        visible_parser.feed(page_without_identifications)
        page_lower = " ".join(visible_parser.parts).lower()
        for term in forbidden_terms:
            self.assertNotIn(term, page_lower)

        self.assertNotIn('class="family-hm"', self.page)
        self.assertNotIn('class="chip-hm"', self.page)
        for conventional_name in correspondence.BASE_ORDER:
            self.assertNotIn(f"({conventional_name})", self.page)

        self.assertNotIn("Orbifold family", self.page)
        self.assertNotIn("Projected group G", self.page)
        self.assertNotIn("Colour-fixing subgroup K", self.page)
        self.assertNotIn("Regular quotient", self.page)
        self.assertNotIn("Base orbifold", self.page)
        self.assertNotIn('class="entry-identity"', self.page)
        self.assertNotIn('class="entry-kicker"', self.page)
        self.assertNotIn('class="group-data"', self.page)
        self.assertNotIn('class="orientation-note"', self.page)
        self.assertNotIn("The phase character maps", self.page)
        self.assertNotIn("Static perfect-colouring plate", self.page)
        self.assertEqual(
            self.parser.wallpaper_links,
            [f"#wallpaper-{base}" for base in correspondence.BASE_ORDER],
        )
        page_ids = [group["id"] for group in self.page_groups]
        self.assertEqual(
            self.parser.directory_groups,
            [(group_id, f"#{group_id}") for group_id in page_ids],
        )
        self.assertEqual(len(self.parser.wallpaper_links), 17)
        self.assertEqual(len(self.parser.directory_groups), 68)
        self.assertEqual(
            self.parser.directory_palette_spans,
            sum(group["clock_order"] for group in self.page_groups),
        )
        directory_start = self.page.index('<nav class="directory"')
        directory_end = self.page.index('<div class="correspondence-atlas"')
        directory_html = self.page[directory_start:directory_end]
        self.assertIn('href="#wallpaper-p1"', directory_html)
        self.assertIn('href="#wallpaper-pm"', directory_html)
        self.assertIn('href="#wallpaper-pg"', directory_html)
        self.assertNotIn('class="directory-census"', directory_html)
        self.assertNotIn('class="census-number"', directory_html)
        for retired_census_copy in (
            "trivial groups",
            "Time is an independent direct-product factor",
            "nontrivial groups",
            "groups with 3 or more colours",
            "Some spatial symmetries advance time phase",
        ):
            self.assertNotIn(retired_census_copy, directory_html)
        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(".directory-census", css)
        self.assertNotIn(".census-number", css)
        for group in self.page_groups:
            card_start = directory_html.index(f'data-directory-group="{group["id"]}"')
            card_end = directory_html.index("</a>", card_start)
            card = directory_html[card_start:card_end]
            self.assertIn(
                correspondence.superscript_html(group["book_color_signature"]),
                card,
                group["id"],
            )
            self.assertIn(f'class="directory-group-id">{group["id"]}</span>', card)
            for residue in group["phase_residues"]:
                self.assertIn(residue["color"], card)
        atlas_start = self.page.index('<div class="correspondence-atlas"')
        first_family = self.page.index('<section class="wallpaper-family')
        self.assertLess(directory_start, atlas_start)
        self.assertLess(atlas_start, first_family)
        self.assertNotIn('class="page-introduction"', self.page)
        self.assertNotIn('class="method"', self.page)
        self.assertNotIn('class="book-method"', self.page)
        self.assertNotIn("The map in one line", self.page)
        self.assertNotIn("The superscripts, the kernel, and the slash", self.page)
        self.assertNotIn("What the book verifies", self.page)

        for group in self.payload["groups"]:
            self.assertTrue({"system", "bravais", "symmorphic"} <= group.keys())
            self.assertNotIn("classified in", group["clockwork_description"].lower())
            self.assertIn(
                f"plane orbifold {group['parent']['orbifold']}",
                group["clockwork_description"],
            )
            if group["clock_order"] > 1:
                self.assertIn(
                    f"kernel K = {group['kernel']['orbifold']}",
                    group["coloring_description"],
                )

    def test_every_row_has_a_book_page_and_honest_coverage_status(self) -> None:
        groups = self.payload["groups"]
        statuses = Counter(group["book_audit"]["status"] for group in groups)
        self.assertEqual(dict(statuses), correspondence.EXPECTED_BOOK_AUDIT_COUNTS)
        self.assertEqual(
            self.payload["meta"]["book_audit_counts"],
            correspondence.EXPECTED_BOOK_AUDIT_COUNTS,
        )
        signature_statuses = Counter(
            group["signature_evidence"]["status"] for group in groups
        )
        self.assertEqual(
            dict(signature_statuses),
            correspondence.EXPECTED_SIGNATURE_EVIDENCE_COUNTS,
        )
        self.assertEqual(
            self.payload["meta"]["signature_evidence_counts"],
            correspondence.EXPECTED_SIGNATURE_EVIDENCE_COUNTS,
        )
        expected_book_audits = []
        audit_routes: Counter[str] = Counter()
        for group in self.page_groups:
            primary = [
                reference
                for reference in group["book_audit"]["references"]
                if reference["role"] == "primary"
            ]
            self.assertEqual(len(primary), 1, group["id"])
            reference = primary[0]
            excerpt, _, source_url, _, route = expected_book_audit_target(group)
            audit_routes[route] += 1
            expected_book_audits.append(
                (
                    source_url,
                    str(excerpt["printed_page"]),
                    str(excerpt["pdf_page"]),
                )
            )
            self.assertEqual(reference["pdf_page"], reference["printed_page"] + 19)
            if route == "onefold":
                self.assertEqual(group["clock_order"], 1, group["id"])
                self.assertEqual(excerpt["printed_page"], 40, group["id"])
            elif route == "type-fallback":
                self.assertEqual(
                    group["signature_evidence"]["status"],
                    "rule-extension",
                    group["id"],
                )
        self.assertEqual(
            audit_routes,
            Counter({"signature": 42, "onefold": 17, "type-fallback": 9}),
        )
        self.assertEqual(self.parser.book_links, expected_book_audits)

        for group in groups:
            order = group["clock_order"]
            audit = group["book_audit"]
            if order == 2:
                self.assertIn(group["tos_notation"], correspondence.TOS_TWO_FOLD_TYPES)
                self.assertEqual(audit["status"], "direct-table")
            elif order == 3 and group["id"] in BOOK_DISCREPANCY_FIXTURE:
                self.assertEqual(audit["status"], "internal-discrepancy")
            elif order == 3:
                self.assertIn(
                    group["tos_notation"], correspondence.TOS_THREE_FOLD_DIRECT_TYPES
                )
                self.assertEqual(audit["status"], "direct-table")
            elif order in (4, 6):
                self.assertEqual(audit["status"], "composite-extension")
                self.assertEqual(len(audit["prime_chain"]), 2)
                self.assertIn(group["id"], correspondence.COMPOSITE_BOOK_CHAINS)

        displayed_by_id = {group["id"]: group for group in self.display_groups}
        self.assertEqual(
            {
                group_id
                for group_id, group in displayed_by_id.items()
                if group["signature_evidence"]["status"] == "type-representative"
            },
            set(BOOK_REPRESENTATIVE_FIXTURE),
        )
        for group_id, multiplicity in BOOK_REPRESENTATIVE_FIXTURE.items():
            evidence = displayed_by_id[group_id]["signature_evidence"]
            self.assertEqual(evidence["variant_count"], multiplicity)
            self.assertIn(
                f"Table 11.1 groups {multiplicity} equivalent generator signatures",
                evidence["summary"],
            )

        self.assertEqual(
            {
                group_id
                for group_id, group in displayed_by_id.items()
                if group["signature_evidence"]["status"] == "rule-extension"
            },
            COMPOSITE_EXTENSION_FIXTURE,
        )

        exceptional = next(group for group in groups if group["id"] == "g234")
        self.assertEqual(exceptional["tos_notation"], "3*3³/*333")
        self.assertEqual(exceptional["book_audit"]["status"], "internal-discrepancy")
        self.assertEqual(
            [reference["printed_page"] for reference in exceptional["book_audit"]["references"]],
            [164, 156, 158],
        )
        self.assertEqual(
            exceptional["book_audit"]["references"][1]["excerpt_key"],
            "p156::3*3³/◦-conflict",
        )
        self.assertEqual(
            exceptional["book_audit"]["independent_reference"]["url"],
            correspondence.FARRIS_URL,
        )

        for group_id in ("g244", "g245"):
            group = displayed_by_id[group_id]
            self.assertEqual(group["book_color_signature"], "³6³3¹2")
            self.assertNotEqual(group["book_color_signature"], "³6²3²2")
            self.assertEqual(group["tos_notation"], "632³/2222")
            self.assertEqual(group["book_audit"]["status"], "internal-discrepancy")
            self.assertEqual(
                [
                    (reference["role"], reference["printed_page"])
                    for reference in group["book_audit"]["references"]
                ],
                [("primary", 164), ("supporting", 157), ("conflict", 156)],
            )
        self.assertNotIn("official errata does not list that typo", self.page)

    def test_short_form_crops_match_the_displayed_notation(self) -> None:
        colour_catalog = json.loads(
            correspondence.COLOR_PATTERN_DATA.read_text(encoding="utf-8")
        )
        colour_groups = {
            row["id"]: row for row in colour_catalog["colour_groups"]
        }
        direct = [
            group
            for group in self.display_groups
            if group["book_audit"]["status"] == "direct-table"
        ]
        self.assertEqual(len(direct), 39)
        for group in direct:
            evidence = group["signature_evidence"]
            source = colour_groups[evidence["source_colour_group_id"]]
            self.assertEqual(
                source["chaim_notation"], group["tos_notation"], group["id"]
            )
            self.assertEqual(
                source["chaim_short_signature"],
                group["book_color_signature"],
                group["id"],
            )
            self.assertEqual(
                evidence["printed_signature"],
                group["book_color_signature"],
                group["id"],
            )
            self.assertEqual(
                evidence["excerpt"]["image"],
                source["book_excerpt"]["image"],
                group["id"],
            )
            self.assertEqual(
                evidence["excerpt"]["highlight_target"],
                "short-signature",
                group["id"],
            )

        by_id = {group["id"]: group for group in self.display_groups}
        g234 = by_id["g234"]["signature_evidence"]
        self.assertEqual(g234["displayed_signature"], "³3*¹3")
        self.assertEqual(g234["printed_signature"], "³3*¹3")
        self.assertEqual(g234["printed_type"], "3*3³/◦")
        self.assertEqual(g234["excerpt"]["highlight_target"], "short-signature")

        for group_id in ("g244", "g245"):
            evidence = by_id[group_id]["signature_evidence"]
            self.assertEqual(evidence["displayed_signature"], "³6³3¹2")
            self.assertEqual(
                evidence["excerpt"]["highlight_target"],
                "short-signature",
            )
            self.assertEqual(
                evidence["conflicts"][0]["printed_signature"],
                "³6²3²2",
            )
            self.assertEqual(
                evidence["conflicts"][0]["excerpt"]["highlight_target"],
                "short-signature",
            )

        derived = [
            group
            for group in self.display_groups
            if group["signature_evidence"]["status"] == "rule-extension"
        ]
        self.assertEqual({group["id"] for group in derived}, COMPOSITE_EXTENSION_FIXTURE)
        for group in derived:
            self.assertIsNone(group["signature_evidence"]["excerpt"], group["id"])
            self.assertEqual(len(group["book_audit"]["prime_chain"]), 2)
            for step in group["book_audit"]["prime_chain"]:
                self.assertEqual(
                    step["short_signature_excerpt"]["highlight_target"],
                    "short-signature",
                    group["id"],
                )

    def test_g129_heading_and_book_audit_share_the_short_signature_crop(self) -> None:
        expected_image = "output/color-pattern-excerpts/tos-cg-p4m-2-4.webp"
        heading_links = [
            attributes
            for attributes in self.parser.short_signature_links
            if attributes.get("data-book-excerpt") == "short-form::cg-p4m-2-4"
        ]
        audit_links = [
            attributes
            for attributes in self.parser.book_excerpt_links
            if (
                "book-page-link" in (attributes.get("class") or "").split()
                and attributes.get("data-book-excerpt")
                == "book-audit::cg-p4m-2-4"
            )
        ]
        self.assertEqual(len(heading_links), 1)
        self.assertEqual(len(audit_links), 1)
        for attributes in (*heading_links, *audit_links):
            self.assertEqual(attributes.get("data-book-image"), expected_image)
            self.assertIn("data-short-signature-excerpt", attributes)
            self.assertEqual(
                attributes.get("data-book-title"),
                "Short colour signature for *442/*2222",
            )
        self.assertNotEqual(
            audit_links[0].get("data-book-image"),
            "output/book-excerpts/p140-star442-over-star2222.webp",
        )

    def test_all_book_links_open_separate_annotated_excerpt_pages(self) -> None:
        audit_links = [
            attributes
            for attributes in self.parser.book_excerpt_links
            if "book-page-link" in (attributes.get("class") or "").split()
        ]
        self.assertEqual(
            len(audit_links),
            len(self.page_groups),
        )
        routes: Counter[str] = Counter()
        for attributes, group in zip(audit_links, self.page_groups):
            excerpt, excerpt_id, source_url, short_signature, route = (
                expected_book_audit_target(group)
            )
            routes[route] += 1
            viewer = urlparse(attributes.get("href") or "")
            self.assertEqual(viewer.path, "book-excerpt.html")
            expected_query = {
                "image": [excerpt["image"]],
                "title": [excerpt["title"]],
                "context": [excerpt["context"]],
                "alt": [excerpt["alt"]],
                "source": [source_url],
                "v": [correspondence.BOOK_EXCERPT_VIEWER_VERSION],
            }
            self.assertEqual(parse_qs(viewer.query), expected_query)
            self.assertEqual(
                attributes.get("data-printed-page"),
                str(excerpt["printed_page"]),
            )
            self.assertEqual(
                attributes.get("data-pdf-page"),
                str(excerpt["pdf_page"]),
            )
            self.assertEqual(attributes.get("data-book-excerpt"), excerpt_id)
            self.assertEqual(attributes.get("data-book-image"), excerpt["image"])
            self.assertEqual(attributes.get("data-book-title"), excerpt["title"])
            self.assertEqual(attributes.get("data-book-context"), excerpt["context"])
            self.assertEqual(attributes.get("data-book-alt"), excerpt["alt"])
            self.assertEqual(attributes.get("data-book-source"), source_url)
            self.assertEqual(attributes.get("target"), correspondence.BOOK_EXCERPT_TARGET)
            self.assertNotIn("rel", attributes)
            self.assertNotIn("aria-haspopup", attributes)
            self.assertNotIn("aria-controls", attributes)
            if short_signature:
                self.assertIn("data-short-signature-excerpt", attributes)
            else:
                self.assertNotIn("data-short-signature-excerpt", attributes)

        self.assertEqual(
            routes,
            Counter({"signature": 42, "onefold": 17, "type-fallback": 9}),
        )
        self.assertEqual(
            sum(
                (attributes.get("data-book-excerpt") or "").startswith(
                    "book-audit::"
                )
                for attributes in audit_links
            ),
            42,
        )
        self.assertEqual(
            sum("data-short-signature-excerpt" in attributes for attributes in audit_links),
            42 + 17,
        )
        self.assertEqual(self.page.count('class="book-audit-limit"'), 9)
        self.assertEqual(
            self.page.count(">no literal row; short form derived</span>"),
            9,
        )

        linked_heading_groups = [
            group
            for group in self.display_groups
            if group["signature_evidence"]["excerpt"] is not None
        ]
        self.assertEqual(len(linked_heading_groups), 42)
        self.assertEqual(len(self.parser.short_signature_links), 42)
        for attributes, group in zip(
            self.parser.short_signature_links,
            linked_heading_groups,
        ):
            excerpt = group["signature_evidence"]["excerpt"]
            self.assertEqual(attributes.get("data-book-image"), excerpt["image"])
            self.assertEqual(
                attributes.get("data-printed-page"),
                str(excerpt["printed_page"]),
            )
            self.assertIn("data-short-signature-excerpt", attributes)
            self.assertTrue(
                (attributes.get("data-book-excerpt") or "").startswith("short-form::")
            )

        support_links = [
            attributes
            for attributes in self.parser.book_excerpt_links
            if "short-form-support-link" in (attributes.get("class") or "").split()
        ]
        self.assertEqual(len(support_links), 20)
        self.assertTrue(
            all("data-short-signature-excerpt" in attributes for attributes in support_links)
        )
        self.assertEqual(len(self.parser.short_form_support_in_book_audit), 20)
        self.assertTrue(all(self.parser.short_form_support_in_book_audit))
        self.assertEqual(len(self.parser.book_excerpt_links), 130)

    def test_the_separate_viewer_loads_complete_tables_or_contextual_webps(self) -> None:
        self.assertEqual(self.parser.book_dialog_ids, [])
        self.assertEqual(self.parser.book_excerpt_images, [])
        self.assertEqual(len(correspondence.BOOK_EXCERPTS), 65)
        table_counts = Counter()
        for key, excerpt in correspondence.BOOK_EXCERPTS.items():
            path = ROOT / excerpt["image"]
            self.assertTrue(path.is_file(), key)
            self.assertEqual(excerpt["pdf_page"], excerpt["printed_page"] + 19)
            focus_x, focus_y, focus_width, focus_height = excerpt["crop"]
            highlight_x, highlight_y, highlight_width, highlight_height = excerpt["highlight"]
            with Image.open(path) as image:
                self.assertEqual(image.format, "WEBP")
                width, height = image.size
            content_width = width - 24
            content_height = height - 78

            panels = excerpt.get("table_panels")
            if panels:
                table_counts[excerpt["table_name"]] += 1
                matching_panel_count = 0
                expected_panel_widths = []
                expected_panel_heights = []
                for panel in panels:
                    panel_x, panel_y, panel_width, panel_height = panel["crop"]
                    self.assertEqual(panel["pdf_page"], panel["printed_page"] + 19)
                    self.assertGreaterEqual(panel_x, 0, key)
                    self.assertGreaterEqual(panel_y, 0, key)
                    self.assertLessEqual(panel_x + panel_width, book_excerpts.PDF_WIDTH, key)
                    self.assertLessEqual(panel_y + panel_height, book_excerpts.PDF_HEIGHT, key)
                    expected_panel_widths.append(round((panel_x + panel_width) * 3) - round(panel_x * 3))
                    expected_panel_heights.append(round((panel_y + panel_height) * 3) - round(panel_y * 3))
                    if panel["pdf_page"] == excerpt["pdf_page"]:
                        matching_panel_count += 1
                        self.assertLessEqual(panel_x, highlight_x, key)
                        self.assertLessEqual(panel_y, highlight_y, key)
                        self.assertGreaterEqual(
                            panel_x + panel_width,
                            highlight_x + highlight_width,
                            key,
                        )
                        self.assertGreaterEqual(
                            panel_y + panel_height,
                            highlight_y + highlight_height,
                            key,
                        )
                self.assertEqual(matching_panel_count, 1, key)
                self.assertEqual(content_width, max(expected_panel_widths), key)
                self.assertEqual(
                    content_height,
                    sum(expected_panel_heights) + 18 * (len(panels) - 1),
                    key,
                )
            else:
                base_x, base_y, base_width, base_height = (
                    book_excerpts.area_context_crop(excerpt["crop"])
                )
                context_x, context_y, context_width, context_height = (
                    book_excerpts.expanded_crop(excerpt["crop"])
                )
                self.assertGreaterEqual(
                    context_width * context_height,
                    focus_width * focus_height * 5,
                    key,
                )
                self.assertAlmostEqual(context_x, base_x, places=6, msg=key)
                self.assertAlmostEqual(context_width, base_width, places=6, msg=key)
                self.assertLessEqual(context_y, base_y, key)
                self.assertGreaterEqual(context_y + context_height, base_y + base_height, key)
                self.assertAlmostEqual(
                    context_height,
                    min(
                        book_excerpts.PDF_HEIGHT,
                        base_height * book_excerpts.VERTICAL_CONTEXT_MULTIPLIER,
                    ),
                    places=6,
                    msg=key,
                )
                self.assertLessEqual(context_x, highlight_x, key)
                self.assertLessEqual(context_y, highlight_y, key)
                self.assertGreaterEqual(
                    context_x + context_width,
                    highlight_x + highlight_width,
                    key,
                )
                self.assertGreaterEqual(
                    context_y + context_height,
                    highlight_y + highlight_height,
                    key,
                )
                focus_pixel_area = (
                    focus_width * book_excerpts.RENDER_DPI / 72
                    * focus_height * book_excerpts.RENDER_DPI / 72
                )
                self.assertGreaterEqual(content_width * content_height, focus_pixel_area * 5, key)

            self.assertLessEqual(
                width,
                book_excerpts.PDF_WIDTH * book_excerpts.RENDER_DPI / 72 + 24,
                key,
            )

        self.assertEqual(
            table_counts,
            Counter({"Table 11.1": 36, "Table 3.2": 17, "Table 12.1": 5, "Table 13.1": 2}),
        )
        for excerpt in correspondence.BOOK_EXCERPTS.values():
            if excerpt.get("table_name") == "Table 11.1":
                self.assertEqual(
                    [panel["printed_page"] for panel in excerpt["table_panels"]],
                    [140, 141],
                )

        for key in (
            "p156::333³/◦",
            "p156::333³/333",
            "p156::632³/2222",
            "p156::3*3³//*333",
        ):
            context = correspondence.BOOK_EXCERPTS[key]["context"]
            self.assertIn("with threefold understood", context)
            self.assertIn("normalizes it as", context)
        self.assertIn("correct regular 632 derivation", correspondence.BOOK_EXCERPTS[
            "p157::632-regular-derivation"
        ]["title"].lower())

        viewer_page = (ROOT / "book-excerpt.html").read_text(encoding="utf-8")
        viewer_script = (ROOT / "book-excerpt.js").read_text(encoding="utf-8")
        viewer_style = (ROOT / "book-excerpt.css").read_text(encoding="utf-8")
        self.assertIn("The outline marks the cited item.", viewer_page)
        self.assertNotIn("five times the previous vertical context", viewer_page)
        self.assertIn("data-zoom-toggle", viewer_page)
        self.assertIn("data-excerpt-image", viewer_page)
        self.assertIn("new URLSearchParams", viewer_script)
        self.assertIn("window.opener.postMessage", viewer_script)
        self.assertIn('type: "clockwork:book-excerpt-ready"', viewer_script)
        self.assertIn("book-excerpts|color-pattern-excerpts", viewer_script)
        self.assertIn("?v=short-signature-audit-v2", viewer_script)
        self.assertIn("book-excerpt.js?v=short-signature-audit-v2", viewer_page)
        self.assertIn('media.dataset.zoom = actual ? "actual" : "fit"', viewer_script)
        self.assertIn('[data-zoom="actual"]', viewer_style)
        self.assertIn('[data-zoom="fit"]', viewer_style)
        self.assertNotIn("max-height: calc(100dvh", viewer_style)
        self.assertIn("book-excerpt.css?v=whole-tables", viewer_page)
        script = (ROOT / "clockwork-coloring-correspondence.js").read_text(encoding="utf-8")
        self.assertNotIn("initializeBookExcerptDialog();", script)
        self.assertIn("initializeBookExcerptLinks();", script)
        self.assertIn("let viewerWindow = null", script)
        self.assertIn("viewerWindow && !viewerWindow.closed", script)
        self.assertIn("viewerWindow.location.href = link.href", script)
        self.assertIn('event.data?.type === "clockwork:book-excerpt-ready"', script)
        self.assertIn("viewerWindow.focus()", script)
        self.assertNotIn('class="book-excerpt-dialog"', self.page)
        self.assertNotIn("view annotated excerpt in the excerpt tab", self.page)
        self.assertEqual(
            self.page.count("The Symmetries of Things · p. "),
            len(self.page_groups),
        )
        self.assertEqual(
            {attributes.get("target") for attributes in self.parser.book_excerpt_links},
            {correspondence.BOOK_EXCERPT_TARGET},
        )
        excerpt_script = (ROOT / "scripts" / "generate_tos_book_excerpts.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('WATERMARK = "© COPYRIGHTED EXCERPT"', excerpt_script)
        self.assertIn('highlight = _box(spec["highlight"]', excerpt_script)

    def test_complementary_forward_skip_pairs_explain_68_to_64(self) -> None:
        paired_rows = {
            group["id"]: group["complementary_skip_mate"]
            for group in self.payload["groups"]
            if group["complementary_skip_mate"]
        }
        self.assertEqual(paired_rows, correspondence.COMPLEMENTARY_SKIP_MATE)
        unordered = {frozenset((group_id, mate)) for group_id, mate in paired_rows.items()}
        self.assertEqual(len(unordered), 4)
        self.assertEqual(
            self.payload["meta"][
                "traditional_colour_classes_after_identifying_complementary_skips"
            ],
            64,
        )
        self.assertEqual(len(self.display_groups) - len(unordered), 47)

    def test_every_static_plate_exists_and_contains_its_phase_palette(self) -> None:
        self.assertEqual(len(self.parser.plate_images), len(self.page_groups))
        by_path = {group["image"]: group for group in self.payload["groups"]}
        displayed_paths = {group["image"] for group in self.page_groups}
        self.assertEqual(
            {
                urlparse(relative).path
                for relative, _alt, _width, _height in self.parser.plate_images
            },
            displayed_paths,
        )
        for image_url, alt, width, height in self.parser.plate_images:
            parsed = urlparse(image_url)
            relative = parsed.path
            self.assertIn(relative, by_path)
            self.assertEqual(
                parse_qs(parsed.query), {"v": ["reflection-centering-v1"]}
            )
            self.assertTrue(alt)
            self.assertEqual((width, height), ("720", "420"))
        for relative, group in by_path.items():
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            with Image.open(path) as image:
                self.assertEqual(image.format, "WEBP")
                self.assertEqual(image.size, (720, 420))
                colors = {
                    color
                    for _count, color in image.convert("RGB").getcolors(
                        maxcolors=720 * 420
                    ) or []
                }
            expected_colors = {
                tuple(bytes.fromhex(residue["color"].lstrip("#")))
                for residue in group["phase_residues"]
            }
            self.assertTrue(expected_colors.issubset(colors), relative)

    def test_static_plates_overlay_every_named_geometric_generator(self) -> None:
        display_ids = [group["id"] for group in self.page_groups]
        self.assertEqual(
            [
                attributes.get("data-generator-overlay")
                for attributes in self.parser.plate_generator_overlays
            ],
            display_ids,
        )
        self.assertEqual(
            len(self.parser.plate_generator_overlays),
            len(self.page_groups),
        )
        for attributes in self.parser.plate_generator_overlays:
            self.assertEqual(attributes.get("viewbox"), "0 0 720 420")
            self.assertEqual(attributes.get("preserveaspectratio"), "xMidYMid meet")
            self.assertEqual(attributes.get("aria-hidden"), "true")
            self.assertEqual(attributes.get("focusable"), "false")

        expected = [
            (
                generator["generator"],
                generator["marker"]["kind"],
                str(generator["marker"].get("order", "")),
            )
            for group in self.page_groups
            for generator in group["chaim_presentation"]["generators"]
        ]
        self.assertEqual(self.parser.plate_generators, expected)
        self.assertEqual(len(expected), 199)
        self.assertEqual(self.page.count("data-generator-symbol="), len(expected))
        self.assertEqual(self.page.count("data-lift-kind="), len(expected))
        self.assertEqual(
            Counter((kind, order) for _name, kind, order in expected),
            Counter(
                {
                    ("translation", ""): 3,
                    ("rotation", "2"): 50,
                    ("rotation", "3"): 22,
                    ("rotation", "4"): 18,
                    ("rotation", "6"): 6,
                    ("mirror", ""): 92,
                    ("glide", ""): 8,
                }
            ),
        )
        expected_symbols = []
        expected_lift_kinds = []
        expected_plane_symbols = []
        expected_attributes = []
        rotation_steps = Counter()
        for group in self.page_groups:
            for generator in group["chaim_presentation"]["generators"]:
                marker = generator["marker"]
                phase = correspondence.Fraction(generator["time_shift"])
                if marker["kind"] == "translation":
                    symbol = "translation"
                    plane_symbol = None
                    lift_kind = "translation-vector"
                    screw_step = None
                elif marker["kind"] == "rotation":
                    order = marker["order"]
                    step = correspondence._rotation_screw_step(
                        order,
                        phase,
                        generator["plate_visualization"]["angle_degrees"],
                    )
                    symbol = f"rotation-{order}-{step}"
                    plane_symbol = None
                    lift_kind = "rotation-axis" if step == 0 else "screw-axis"
                    rotation_steps[(order, step)] += 1
                    screw_step = str(step)
                else:
                    plane_symbol = correspondence._polar_plane_symbol(
                        group["id"],
                        {
                            "generator": generator["generator"],
                            "marker": marker,
                            "phase": phase,
                        },
                    )
                    symbol = f"plane-{plane_symbol}"
                    lift_kind = {
                        "m": "mirror-plane",
                        "c": "c-glide-plane",
                        "axial": "axial-glide-plane",
                        "n": "n-glide-plane",
                        "d": "d-glide-plane",
                    }[plane_symbol]
                    screw_step = None
                    expected_plane_symbols.append(plane_symbol)
                expected_symbols.append(symbol)
                expected_lift_kinds.append(lift_kind)
                expected_attributes.append(
                    (
                        group["id"],
                        generator["generator"],
                        symbol,
                        plane_symbol,
                        lift_kind,
                        str(phase),
                        screw_step,
                    )
                )
        self.assertEqual(self.parser.plate_generator_symbols, expected_symbols)
        actual_attributes = [
            (
                group_id,
                attributes.get("data-generator"),
                attributes.get("data-generator-symbol"),
                attributes.get("data-plane-symbol"),
                attributes.get("data-lift-kind"),
                attributes.get("data-time-shift"),
                attributes.get("data-screw-step"),
            )
            for group_id, attributes in self.parser.plate_generator_attributes
        ]
        self.assertEqual(actual_attributes, expected_attributes)
        self.assertEqual(
            Counter(expected_lift_kinds),
            Counter(
                {
                    "translation-vector": 3,
                    "rotation-axis": 40,
                    "screw-axis": 56,
                    "mirror-plane": 47,
                    "c-glide-plane": 45,
                    "axial-glide-plane": 5,
                    "n-glide-plane": 2,
                    "d-glide-plane": 1,
                }
            ),
        )
        self.assertEqual(
            Counter(expected_plane_symbols),
            Counter({"m": 47, "c": 45, "axial": 5, "n": 2, "d": 1}),
        )
        self.assertEqual(
            Counter(self.parser.plate_generator_axes),
            Counter(expected_plane_symbols),
        )
        self.assertEqual(
            rotation_steps,
            Counter(
                {
                    (2, 0): 26,
                    (2, 1): 24,
                    (3, 0): 8,
                    (3, 1): 8,
                    (3, 2): 6,
                    (4, 0): 5,
                    (4, 1): 5,
                    (4, 2): 5,
                    (4, 3): 3,
                    (6, 0): 1,
                    (6, 1): 1,
                    (6, 2): 1,
                    (6, 3): 1,
                    (6, 4): 1,
                    (6, 5): 1,
                }
            ),
        )

        for group in self.page_groups:
            actions = group["chaim_presentation"]["generators"]
            alignment = correspondence._canonical_generator_alignment(
                group["id"],
                group["parent"]["hm"],
                group["render"],
            )
            placement = correspondence._plate_generator_assignment(group)
            self.assertEqual(
                [row["generator"] for row in alignment],
                [row["generator"] for row in actions],
                group["id"],
            )
            self.assertEqual(
                [row["generator"] for row in placement],
                [row["generator"] for row in actions],
                group["id"],
            )
            for action, aligned, positioned in zip(
                actions, alignment, placement, strict=True
            ):
                message = f'{group["id"]}:{action["generator"]}'
                self.assertEqual(
                    action["plate_source_index"],
                    aligned["source_index"],
                    message,
                )
                self.assertEqual(
                    action["plate_lattice_shift"],
                    list(aligned["lattice_shift"]),
                    message,
                )
                self.assertEqual(
                    action["plate_visualization"],
                    aligned["visualization"],
                    message,
                )
                self.assertEqual(
                    correspondence.Fraction(action["time_shift"]),
                    aligned["phase"],
                    message,
                )
                source_operation = group["render"]["ops"][
                    action["plate_source_index"]
                ]
                self.assertEqual(
                    correspondence.exact_fraction(source_operation["tau"]),
                    aligned["phase"],
                    message,
                )
                self.assertEqual(
                    positioned,
                    {
                        "generator": action["generator"],
                        "geometry": action["geometry"],
                        "marker": action["marker"],
                        "visualization": action["plate_visualization"],
                        "phase": correspondence.Fraction(action["time_shift"]),
                    },
                    message,
                )

        page = self.page
        g225 = page[
            page.index('<section class="correspondence-entry" id="g225"'):
            page.index('<section class="correspondence-entry" id="g226"')
        ]
        self.assertEqual(g225.count("plate-generator--rotation-3"), 3)
        g244 = page[
            page.index('<section class="correspondence-entry" id="g244"'):
            page.index('<section class="correspondence-entry" id="g245"')
        ]
        self.assertEqual(g244.count("plate-generator--rotation-6"), 1)
        self.assertEqual(g244.count("plate-generator--rotation-3"), 1)
        self.assertEqual(g244.count("plate-generator--rotation-2"), 1)
        g269 = page[
            page.index('<section class="correspondence-entry" id="g269"'):
            page.index('<section class="correspondence-entry" id="g270"')
        ]
        self.assertEqual(g269.count("plate-generator--mirror"), 3)
        g9_start = page.index('<section class="correspondence-entry" id="g9"')
        g9_end = page.index('<section class="correspondence-entry" id="g8"', g9_start)
        g9 = page[g9_start:g9_end]
        self.assertEqual(g9.count("plate-generator--mirror"), 1)
        self.assertEqual(g9.count("plate-generator--glide"), 1)

        attributes_by_generator = {
            (group_id, attributes.get("data-generator")): attributes
            for group_id, attributes in self.parser.plate_generator_attributes
        }
        plane_fixtures = {
            ("g234", "P"): ("plane-m", "m", "mirror-plane", "0"),
            ("g233", "P"): ("plane-c", "c", "c-glide-plane", "1/2"),
            ("g63", "Z"): (
                "plane-axial",
                "axial",
                "axial-glide-plane",
                "0",
            ),
            ("g59", "Z"): ("plane-n", "n", "n-glide-plane", "1/2"),
            ("g75", "Z"): ("plane-d", "d", "d-glide-plane", "1/4"),
        }
        for key, expected_fixture in plane_fixtures.items():
            attributes = attributes_by_generator[key]
            self.assertEqual(
                (
                    attributes.get("data-generator-symbol"),
                    attributes.get("data-plane-symbol"),
                    attributes.get("data-lift-kind"),
                    attributes.get("data-time-shift"),
                ),
                expected_fixture,
                key,
            )
        self.assertEqual(self.parser.plate_quarter_arrows, 2)
        self.assertEqual(self.parser.plate_quarter_arrow_halos, 2)
        self.assertEqual(self.parser.plate_translation_arrows, 3)
        self.assertEqual(self.parser.plate_translation_arrow_halos, 3)

        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".colour-plate-graphic {", css)
        self.assertIn(".plate-generator-overlay {", css)
        for plane_symbol in ("m", "c", "axial", "n", "d"):
            self.assertIn(
                f".plate-generator-axis--plane-{plane_symbol}", css
            )
        self.assertIn(".plate-generator-quarter-arrow", css)
        self.assertIn(".plate-generator-translation", css)
        self.assertNotIn(".plate-generator-half-arrow", css)
        self.assertIn("@media (forced-colors: active)", css)

    def test_every_plate_label_clears_motifs_labels_glyphs_and_frame(self) -> None:
        translate_pattern = re.compile(
            r"translate\(([-+0-9.eE]+)[ ,]+([-+0-9.eE]+)\)"
        )

        def absolute_label_point(
            marker: ElementTree.Element,
        ) -> tuple[float, float]:
            points: list[tuple[float, float]] = []

            def visit(
                element: ElementTree.Element,
                translate_x: float = 0.0,
                translate_y: float = 0.0,
            ) -> None:
                transform = element.attrib.get("transform", "")
                if transform:
                    match = translate_pattern.fullmatch(transform)
                    self.assertIsNotNone(match, transform)
                    translate_x += float(match.group(1))
                    translate_y += float(match.group(2))
                classes = set(element.attrib.get("class", "").split())
                if element.tag == "text" and "plate-generator-label" in classes:
                    points.append(
                        (
                            float(element.attrib["x"]) + translate_x,
                            float(element.attrib["y"]) + translate_y,
                        )
                    )
                for child in element:
                    visit(child, translate_x, translate_y)

            visit(marker)
            self.assertEqual(len(points), 1)
            return points[0]

        label_count = 0
        rotation_transform_count = 0
        axis_count = 0
        for group in self.page_groups:
            overlay_html = correspondence._plate_generator_overlay_html(group)
            overlay = ElementTree.fromstring(overlay_html)
            placement = correspondence._plate_generator_assignment(group)
            markers = list(overlay)
            self.assertEqual(len(markers), len(placement), group["id"])

            scale = correspondence._plate_cell_scale(group["render"])
            viewport_center = group["viewport_center"]
            glyph_boxes = []
            for generator in placement:
                if generator["marker"]["kind"] != "rotation":
                    continue
                centre_x, centre_y = correspondence._plate_screen_point(
                    generator["visualization"]["centre"],
                    scale,
                    viewport_center,
                )
                half_size = correspondence.PLATE_ROTATION_GLYPH_HALF_SIZE_PX
                glyph_boxes.append(
                    (
                        math.floor(centre_x - half_size),
                        math.floor(centre_y - half_size),
                        math.ceil(centre_x + half_size),
                        math.ceil(centre_y + half_size),
                    )
                )

            motif_mask = correspondence._plate_motif_occupancy_mask(group)
            self.assertEqual(
                motif_mask.size,
                (correspondence.IMAGE_WIDTH, correspondence.IMAGE_HEIGHT),
            )
            occupied_label_boxes: list[
                tuple[str, correspondence.PlateLabelBox]
            ] = []
            actual_positions: dict[str, tuple[float, float]] = {}
            for marker, generator in zip(markers, placement, strict=True):
                name = generator["generator"]
                self.assertEqual(marker.attrib.get("data-generator"), name)
                point = absolute_label_point(marker)
                actual_positions[name] = point
                bounds = correspondence._plate_label_box(point)
                label_count += 1

                self.assertEqual(
                    correspondence._plate_label_motif_pixels(motif_mask, bounds),
                    0,
                    f'{group["id"]}:{name}:motif',
                )
                self.assertGreaterEqual(
                    bounds[0],
                    correspondence.PLATE_LABEL_FRAME_INSET_PX,
                    f'{group["id"]}:{name}:left frame',
                )
                self.assertGreaterEqual(
                    bounds[1],
                    correspondence.PLATE_LABEL_FRAME_INSET_PX,
                    f'{group["id"]}:{name}:top frame',
                )
                self.assertLessEqual(
                    bounds[2],
                    correspondence.IMAGE_WIDTH
                    - correspondence.PLATE_LABEL_FRAME_INSET_PX,
                    f'{group["id"]}:{name}:right frame',
                )
                self.assertLessEqual(
                    bounds[3],
                    correspondence.IMAGE_HEIGHT
                    - correspondence.PLATE_LABEL_FRAME_INSET_PX,
                    f'{group["id"]}:{name}:bottom frame',
                )
                for other_name, other_bounds in occupied_label_boxes:
                    self.assertEqual(
                        correspondence._plate_box_intersection_area(
                            bounds,
                            other_bounds,
                        ),
                        0,
                        f'{group["id"]}:{name}/{other_name}:labels',
                    )
                for glyph_box in glyph_boxes:
                    self.assertEqual(
                        correspondence._plate_box_intersection_area(
                            bounds,
                            glyph_box,
                        ),
                        0,
                        f'{group["id"]}:{name}:glyph',
                    )
                occupied_label_boxes.append((name, bounds))

                kind = generator["marker"]["kind"]
                if kind == "rotation":
                    transform_nodes = [
                        element
                        for element in marker.iter("g")
                        if element.attrib.get("transform")
                    ]
                    self.assertEqual(len(transform_nodes), 1)
                    match = translate_pattern.fullmatch(
                        transform_nodes[0].attrib["transform"]
                    )
                    self.assertIsNotNone(match)
                    expected_centre = correspondence._plate_screen_point(
                        generator["visualization"]["centre"],
                        scale,
                        viewport_center,
                    )
                    for actual, expected in zip(
                        (float(match.group(1)), float(match.group(2))),
                        expected_centre,
                        strict=True,
                    ):
                        self.assertAlmostEqual(
                            actual,
                            expected,
                            delta=0.011,
                            msg=f'{group["id"]}:{name}:glyph transform',
                        )
                    rotation_transform_count += 1
                elif kind in {"mirror", "glide"}:
                    axis_lines = [
                        element
                        for element in marker.iter("line")
                        if "plate-generator-axis"
                        in set(element.attrib.get("class", "").split())
                    ]
                    self.assertEqual(len(axis_lines), 1)
                    expected_axis = correspondence._clipped_plate_axis(
                        generator["visualization"]["axis_point"],
                        generator["visualization"]["axis_direction"],
                        scale,
                        viewport_center,
                    )
                    self.assertIsNotNone(expected_axis)
                    actual_axis = axis_lines[0].attrib
                    for attribute, expected in zip(
                        ("x1", "y1", "x2", "y2"),
                        (*expected_axis["start"], *expected_axis["end"]),
                        strict=True,
                    ):
                        self.assertAlmostEqual(
                            float(actual_axis[attribute]),
                            expected,
                            delta=0.011,
                            msg=f'{group["id"]}:{name}:axis {attribute}',
                        )
                    axis_count += 1

            if group["id"] in MOTIF_CLEAR_LABEL_POSITION_FIXTURE:
                self.assertEqual(
                    {
                        name: (round(point[0], 2), round(point[1], 2))
                        for name, point in actual_positions.items()
                    },
                    MOTIF_CLEAR_LABEL_POSITION_FIXTURE[group["id"]],
                )

        self.assertEqual(label_count, 199)
        self.assertEqual(rotation_transform_count, 96)
        self.assertEqual(axis_count, 100)

    def test_crystallographic_symbols_encode_the_polar_lift(self) -> None:
        by_id = {group["id"]: group for group in self.display_groups}

        def symbols(group_id: str) -> list[str]:
            result = []
            for row in by_id[group_id]["chaim_presentation"]["generators"]:
                marker = row["marker"]
                phase = correspondence.Fraction(row["time_shift"])
                if marker["kind"] == "rotation":
                    result.append(
                        correspondence._rotation_symbol_key(
                            marker["order"],
                            phase,
                            row["plate_visualization"]["angle_degrees"],
                        )
                    )
                elif marker["kind"] == "mirror":
                    result.append("plane-m" if phase == 0 else "plane-c")
                elif phase == 0:
                    result.append("plane-axial")
                elif phase == correspondence.Fraction(1, 2):
                    result.append("plane-n")
                elif phase == correspondence.Fraction(1, 4):
                    result.append("plane-d")
                else:
                    self.fail(f"unclassified plane symbol {group_id}:{row}")
            return result

        self.assertEqual(
            symbols("g225"),
            ["rotation-3-2", "rotation-3-2", "rotation-3-2"],
        )
        self.assertEqual(
            symbols("g96"),
            ["rotation-4-1", "rotation-4-1", "rotation-2-1"],
        )
        self.assertEqual(
            symbols("g97"),
            ["rotation-4-3", "rotation-4-3", "rotation-2-1"],
        )
        self.assertEqual(symbols("g234"), ["rotation-3-1", "plane-m"])
        self.assertEqual(symbols("g235"), ["rotation-3-1", "plane-c"])
        self.assertEqual(
            symbols("g244"),
            ["rotation-6-2", "rotation-3-2", "rotation-2-0"],
        )
        self.assertEqual(
            symbols("g95"),
            ["rotation-4-2", "rotation-4-2", "rotation-2-0"],
        )
        self.assertEqual(symbols("g269"), ["plane-m", "plane-c", "plane-c"])
        self.assertEqual(symbols("g9"), ["plane-c", "plane-n"])
        self.assertEqual(symbols("g248")[0], "rotation-6-1")
        self.assertEqual(symbols("g246")[0], "rotation-6-3")
        self.assertEqual(symbols("g247")[0], "rotation-6-5")

        self.assertNotIn(
            "generator-symbol-arms",
            correspondence._rotation_symbol_body_html(2, 0),
        )
        self.assertEqual(
            correspondence._rotation_symbol_body_html(3, 2).count("L"), 3
        )
        self.assertEqual(
            correspondence._rotation_symbol_body_html(3, 1).count("L"), 3
        )
        self.assertEqual(
            correspondence._rotation_symbol_body_html(4, 2).count("L"), 2
        )
        self.assertEqual(
            correspondence._rotation_symbol_body_html(6, 2).count("L"), 3
        )
        self.assertNotEqual(
            correspondence._rotation_symbol_body_html(3, 1),
            correspondence._rotation_symbol_body_html(3, 2),
        )
        self.assertNotEqual(
            correspondence._rotation_symbol_body_html(6, 1),
            correspondence._rotation_symbol_body_html(6, 5),
        )

        css = (ROOT / "clockwork-coloring-correspondence.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("--generator-ink: #74213f", css)
        self.assertNotIn("--plate-generator-ink", css)
        self.assertIn("color: var(--generator-ink)", css)
        self.assertIn(".generator-symbol-core {", css)
        self.assertIn(".generator-symbol-body .generator-symbol-arms {", css)
        self.assertIn(".plate-generator-axis,", css)
        self.assertIn(".diagram-symbol-plane,", css)
        self.assertIn(".diagram-symbol-translation {", css)
        self.assertIn(
            ".plate-generator-quarter-arrow,\n.diagram-symbol-quarter-arrow {",
            css,
        )
        self.assertNotIn(".presentation-generator-glide", css)
        self.assertNotIn(
            '<line x1="4" y1="12" x2="36" y2="12"></line>', self.page
        )

    def test_every_record_has_the_audited_viewport_center(self) -> None:
        self.assertEqual(len(self.page_groups), 68)
        for group in self.page_groups:
            center = group.get("viewport_center")
            self.assertIsInstance(center, list, group["id"])
            self.assertEqual(len(center), 2, group["id"])
            self.assertTrue(
                all(math.isfinite(float(component)) for component in center),
                group["id"],
            )

        by_id = {group["id"]: group for group in self.page_groups}
        for group_id, expected in VIEWPORT_CENTER_FIXTURE.items():
            actual = by_id[group_id]["viewport_center"]
            for component, expected_component in zip(
                actual, expected, strict=True
            ):
                self.assertAlmostEqual(
                    float(component), expected_component, places=9, msg=group_id
                )

    def test_every_reflected_axis_roughly_bisects_the_plate(self) -> None:
        expected_lines: dict[
            tuple[str, str], tuple[tuple[float, float], tuple[float, float]]
        ] = {}
        smaller_shares: dict[tuple[str, str], float] = {}
        centers_by_group = {
            group["id"]: _fully_visible_static_centers(group)
            for group in self.page_groups
        }
        for group in self.page_groups:
            for action in group["chaim_presentation"]["generators"]:
                if action["marker"]["kind"] not in {"mirror", "glide"}:
                    continue
                key = (group["id"], action["generator"])
                smaller_share, endpoints = _projected_axis_metrics(group, action)
                smaller_shares[key] = smaller_share
                expected_lines[key] = endpoints
                self.assertGreaterEqual(
                    smaller_share + 1e-9,
                    0.388,
                    f"{key[0]}:{key[1]} leaves only "
                    f"{smaller_share:.3%} on one side",
                )
                start, end = endpoints
                direction = (end[0] - start[0], end[1] - start[1])
                signed_centers = [
                    direction[0] * (center[1] - start[1])
                    - direction[1] * (center[0] - start[0])
                    for center in centers_by_group[group["id"]]
                ]
                side_counts = (
                    sum(value < -1e-6 for value in signed_centers),
                    sum(value > 1e-6 for value in signed_centers),
                )
                self.assertGreaterEqual(
                    min(side_counts),
                    6,
                    f"{key[0]}:{key[1]} has too few full motifs on one side: "
                    f"{side_counts}",
                )

        self.assertEqual(len(smaller_shares), 100)
        g269_shares = {
            generator: share
            for (group_id, generator), share in smaller_shares.items()
            if group_id == "g269"
        }
        self.assertEqual(set(g269_shares), {"P", "Q", "R"})
        self.assertTrue(
            all(share > 0.39 for share in g269_shares.values()),
            g269_shares,
        )
        self.assertGreater(g269_shares["R"], 0.40)

        actual_lines = {
            (group_id, generator): (
                (float(attributes["x1"]), float(attributes["y1"])),
                (float(attributes["x2"]), float(attributes["y2"])),
            )
            for group_id, generator, attributes
            in self.parser.plate_generator_axis_lines
        }
        self.assertEqual(set(actual_lines), set(expected_lines))
        inset = 9.0
        for key, actual_endpoints in actual_lines.items():
            expected_endpoints = expected_lines[key]
            for actual, expected in zip(
                actual_endpoints, expected_endpoints, strict=True
            ):
                self.assertAlmostEqual(actual[0], expected[0], places=2, msg=key)
                self.assertAlmostEqual(actual[1], expected[1], places=2, msg=key)
                self.assertGreaterEqual(actual[0] + 1e-9, inset, key)
                self.assertLessEqual(
                    actual[0] - 1e-9,
                    correspondence.IMAGE_WIDTH - inset,
                    key,
                )
                self.assertGreaterEqual(actual[1] + 1e-9, inset, key)
                self.assertLessEqual(
                    actual[1] - 1e-9,
                    correspondence.IMAGE_HEIGHT - inset,
                    key,
                )
                self.assertTrue(
                    abs(actual[0] - inset) <= 0.01
                    or abs(actual[0] - (correspondence.IMAGE_WIDTH - inset))
                    <= 0.01
                    or abs(actual[1] - inset) <= 0.01
                    or abs(actual[1] - (correspondence.IMAGE_HEIGHT - inset))
                    <= 0.01,
                    key,
                )

    def test_every_live_phase_circle_meets_the_measured_reference_size(self) -> None:
        geometry_module = ROOT / "clockwork-coloring-geometry.js"
        self.assertTrue(geometry_module.is_file())
        node_script = r"""
import fs from "node:fs";
import {
  MIN_PHASE_CIRCLE_DIAMETER_PX,
  buildClockworkGeometry,
} from "./clockwork-coloring-geometry.js";
const payload = JSON.parse(
  fs.readFileSync("data/clockwork-coloring-correspondence.json", "utf8"),
);
const sizes = [[507, 296], [411, 240], [325, 190], [260, 152]];
const measurements = [];
for (const group of payload.groups) {
  for (const [width, height] of sizes) {
    const geometry = buildClockworkGeometry(
      group.render,
      width,
      height,
      1,
      group.viewport_center,
    );
    const centerless = buildClockworkGeometry(
      group.render,
      width,
      height,
      1,
      [0, 0],
    );
    measurements.push({
      id: group.id,
      width,
      height,
      diameter: geometry.circleDiameter,
      centerlessDiameter: centerless.circleDiameter,
      motifRadius: geometry.motifRadius,
      centerlessMotifRadius: centerless.motifRadius,
      viewportCenter: geometry.viewportCenter,
      viewportPixelOffset: geometry.viewportPixelOffset,
    });
  }
}
process.stdout.write(JSON.stringify({
  floor: MIN_PHASE_CIRCLE_DIAMETER_PX,
  measurements,
}));
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["floor"], correspondence.MIN_VISIBLE_MOTIF_DIAMETER_PX)
        self.assertEqual(
            len(report["measurements"]),
            len(self.page_groups) * 4,
        )
        for measurement in report["measurements"]:
            self.assertGreaterEqual(
                measurement["diameter"] + 1e-6,
                report["floor"],
                f"{measurement['id']} at {measurement['width']}×{measurement['height']}",
            )
            self.assertAlmostEqual(
                measurement["diameter"],
                measurement["centerlessDiameter"],
                places=9,
                msg=measurement["id"],
            )
            self.assertAlmostEqual(
                measurement["motifRadius"],
                measurement["centerlessMotifRadius"],
                places=9,
                msg=measurement["id"],
            )

            group = next(
                group
                for group in self.page_groups
                if group["id"] == measurement["id"]
            )
            self.assertEqual(
                measurement["viewportCenter"], group["viewport_center"]
            )
            center = [float(value) for value in group["viewport_center"]]
            offset = [
                float(value) for value in measurement["viewportPixelOffset"]
            ]
            scale_candidates = []
            if abs(center[0]) > 1e-9:
                scale_candidates.append(-offset[0] / center[0])
            else:
                self.assertAlmostEqual(offset[0], 0.0, places=9)
            if abs(center[1]) > 1e-9:
                scale_candidates.append(offset[1] / center[1])
            else:
                self.assertAlmostEqual(offset[1], 0.0, places=9)
            self.assertTrue(
                all(scale > 0 for scale in scale_candidates),
                measurement["id"],
            )
            if len(scale_candidates) == 2:
                self.assertAlmostEqual(
                    scale_candidates[0],
                    scale_candidates[1],
                    places=9,
                    msg=measurement["id"],
                )

        controller = (ROOT / "clockwork-coloring-correspondence.js").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'from "./clockwork-coloring-geometry.js?v=reflection-centering-v1"',
            controller,
        )
        self.assertIn(
            '"data/clockwork-coloring-correspondence.json?'
            'v=reflection-centering-v1"',
            controller,
        )
        self.assertRegex(
            controller,
            r"buildClockworkGeometry\(\s*this\.record\.render,\s*width,\s*"
            r"height,\s*dpr,\s*this\.record\.viewport_center,?\s*\)",
        )
        self.assertNotIn("MIN_CELLS", controller)

    def test_every_static_plate_uses_the_same_reference_scale(self) -> None:
        minimum_visible = float("inf")
        for group in self.page_groups:
            _b1, _b2, radius, _ranges = correspondence._site_geometry(
                group["render"],
                correspondence.IMAGE_WIDTH * correspondence.ANTIALIAS,
                correspondence.IMAGE_HEIGHT * correspondence.ANTIALIAS,
            )
            output_radius = radius / correspondence.ANTIALIAS
            self.assertGreaterEqual(
                output_radius + 1e-6,
                correspondence.PLATE_MIN_MOTIF_RADIUS_PX,
                group["id"],
            )
            visible_diameter = (
                correspondence.PLATE_MOTIF_DIAMETER_FACTOR
                * output_radius
                * correspondence.REFERENCE_STAGE_WIDTH_PX
                / correspondence.IMAGE_WIDTH
            )
            minimum_visible = min(minimum_visible, visible_diameter)
        self.assertGreaterEqual(
            minimum_visible,
            correspondence.MIN_VISIBLE_MOTIF_DIAMETER_PX,
        )

    def test_all_68_films_are_local_and_stopped_by_default(self) -> None:
        ids = [group["id"] for group in self.page_groups]
        self.assertEqual(self.parser.film_group_ids, ids)
        self.assertEqual(
            self.parser.canvases,
            [(f"{group_id}-film", "1", "1") for group_id in ids],
        )
        self.assertEqual(len(self.parser.buttons), len(self.page_groups))
        self.assertTrue(all(disabled for disabled, _pressed, _controls in self.parser.buttons))
        self.assertTrue(all(pressed == "false" for _disabled, pressed, _controls in self.parser.buttons))
        self.assertEqual(
            [controls for _disabled, _pressed, controls in self.parser.buttons],
            [f"{group_id}-film" for group_id in ids],
        )
        self.assertEqual(len(self.parser.sliders), len(self.page_groups))
        self.assertTrue(
            all(
                disabled and value == "0" and input_type == "range"
                for disabled, value, input_type, _slider_id in self.parser.sliders
            )
        )
        self.assertEqual(len(self.parser.scripts), 2)
        self.assertIn(
            (correspondence.CORRESPONDENCE_SCRIPT_SRC, "module"),
            self.parser.scripts,
        )
        self.assertEqual(
            [
                (urlparse(src).path, script_type)
                for src, script_type in self.parser.scripts
                if urlparse(src).path == "crystal-viewer.js"
            ],
            [("crystal-viewer.js", "module")],
        )
        script_path = ROOT / "clockwork-coloring-correspondence.js"
        self.assertTrue(script_path.is_file())
        script = script_path.read_text(encoding="utf-8")
        self.assertIn("this.playingIntent = false", script)
        self.assertIn("if (!this.active) this.activate();", script)
        self.assertIn("else this.resizeAndDraw();", script)
        self.assertIn("phase - placement.tau", script)
        self.assertIn("const HAND_TAIL = 1.4", script)
        self.assertIn("const tip = -Math.PI / 2 + frac(theta) * TWO_PI", script)
        self.assertNotIn("const lit = order > 1", script)
        self.assertNotIn("FRAME_MS", script)
        self.assertIn('this.controls.addEventListener("keydown"', script)
        self.assertIn('event.key === "ArrowRight"', script)
        self.assertIn('event.key === "Home"', script)
        self.assertNotIn("fixed phase ruler, smooth hand", self.page)
        self.assertNotIn("The upper canvas repeats one continuously animated asymmetric motif", self.page)
        self.assertNotIn("autoplay", self.page.lower())
        self.assertNotIn("autoplay", script.lower())
        self.assertEqual(self.parser.iframes, [])
        self.assertNotIn("<video", self.page)
        self.assertNotIn('src="https://yaroslavvb.github.io/animated-groups-fable', self.page)
        self.assertNotIn('href="https://yaroslavvb.github.io/animated-groups-fable/js/', self.page)
        self.assertNotIn("https://yaroslavvb.github.io/animated-groups-fable", script)
        self.assertNotIn("no runtime data or code is loaded from", self.page)
        self.assertNotIn("paused by default", self.page)

    def test_navigation_links_the_correspondence_from_both_existing_pages(self) -> None:
        for page in (ROOT / "index.html", ROOT / "future-directions.html"):
            self.assertIn(
                'href="clockwork-coloring-correspondence.html">Correspondence</a>',
                page.read_text(encoding="utf-8"),
            )

    def test_generated_outputs_are_current(self) -> None:
        correspondence.validate_payload(self.payload)
        self.assertEqual(
            correspondence.check_outputs(self.payload, include_images=False),
            [],
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_clockwork_coloring_correspondence.py"),
                "--check",
                "--text-only",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
