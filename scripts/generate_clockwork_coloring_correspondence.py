#!/usr/bin/env python3
"""Build the 68-record clockwork/colouring data and 51-row atlas page.

The page reads each forward entry of one pinned 275-group catalog as a
regular cyclic colouring.  For an operation ``(M, v, tau)``, the colour
character is ``kappa(M, v) = N*tau mod N``.  Its kernel K is the subgroup of
zero-phase operations.  The kernel wallpaper types below were independently
identified against the 17 canonical wallpaper models, using the kernel's own
translation lattice (not the usually finer projected parent lattice).

The displayed colour notation follows Conway--Burgiel--Goodman-Strauss,
*The Symmetries of Things*: G/K for twofold colourings and G^N/K for the
regular cyclic N-fold action when N > 2.  Their double slash is reserved for
nonregular actions where the stabilizer H of one colour is larger than K.

The source catalog is always read-only.  A normal run rebuilds the HTML and
static WebP plates from the checked-in correspondence JSON.  Pass the pinned
catalog explicitly only to audit or deliberately refresh the extract::

    python3 scripts/generate_clockwork_coloring_correspondence.py
    python3 scripts/generate_clockwork_coloring_correspondence.py --check
    python3 scripts/generate_clockwork_coloring_correspondence.py \
        --source-catalog /path/to/catalog.json
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from html import escape
import hashlib
import io
from itertools import combinations
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable
from urllib.parse import urlencode

from PIL import Image, ImageDraw

from tos_book_excerpt_specs import BOOK_EXCERPTS


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "color-forward-manifest.json"
DATA = ROOT / "data" / "clockwork-coloring-correspondence.json"
PAGE = ROOT / "clockwork-coloring-correspondence.html"
IMAGE_DIR = ROOT / "output" / "clockwork-colorings"
CORRESPONDENCE_STYLE_SRC = "clockwork-coloring-correspondence.css?v=geometric-operations-directory"
CORRESPONDENCE_SCRIPT_SRC = "clockwork-coloring-correspondence.js?v=deep-link-canvas-fix"

SOURCE_SHA256 = "040eebe747815557014c1dbf1d4265d204aaae35c110595f2a15b94ee7f68ca0"
CATALOG_ROOT = "https://yaroslavvb.github.io/animated-groups-fable/catalog.html?time=forward"
CATALOG_DATA_URL = "https://yaroslavvb.github.io/animated-groups-fable/data/catalog.json"
BOOK_RECORD_URL = "https://books.google.com/books?id=EtQCk0TNafsC"
BOOK_PAGE_URL = BOOK_RECORD_URL + "&pg=PA{page}"
BOOK_EXCERPT_TARGET = "clockwork-book-excerpt"
BOOK_ERRATA_URL = "https://www.mit.edu/~hlb/Symmetries_of_Things/SoTerrors.html"
FARRIS_URL = "https://archive.bridgesmathart.org/2017/bridges2017-131.pdf#page=6"

IMAGE_WIDTH = 720
IMAGE_HEIGHT = 420
ANTIALIAS = 2
REFERENCE_STAGE_WIDTH_PX = 507
MIN_VISIBLE_MOTIF_DIAMETER_PX = 38
# At the reference card width, a radius of 36 output pixels gives the plate's
# asymmetric stamp a 38 CSS-pixel circumscribed diameter after image scaling.
PLATE_MIN_MOTIF_RADIUS_PX = 36
PLATE_MOTIF_DIAMETER_FACTOR = 1.5057224179774968
PLATE_MOTIF_SHAPE = (
    (-0.58, -0.44),
    (-0.03, -0.68),
    (0.56, -0.28),
    (0.25, 0.02),
    (0.48, 0.58),
    (-0.12, 0.40),
    (-0.64, 0.14),
)
PALETTE = (
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # green
    "#CC79A7",  # reddish purple
    "#D55E00",  # vermillion
    "#56B4E9",  # sky blue
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

WALLPAPER_SUMMARIES = {
    "p1": (
        "A torus; translations only.",
        "Its sole forward catalog row is the omitted C1 product, so this signature has no nontrivial colour action to display.",
    ),
    "p2": (
        "A sphere with four order-2 cone points.",
        "Both displayed lifts use two colours; their colour-fixing kernels are ◦ and 2222.",
    ),
    "pm": (
        "Two mirror-boundary components.",
        "The forward catalog contributes only the omitted C1 product, so this signature has no nontrivial colour action to display.",
    ),
    "pg": (
        "Two crosscaps; glide reflections but no mirror boundary.",
        "Each × is Conway's crosscap or ‘miracle’ symbol, not a mirror boundary; the sole forward row is the omitted C1 product.",
    ),
    "cm": (
        "One mirror boundary and one crosscap.",
        "Its single nontrivial lift exchanges two phases and has translation-only kernel K = ◦.",
    ),
    "pmm": (
        "A mirror quadrilateral with four order-2 corners.",
        "Its five nontrivial lifts all use two colours, with phase-zero kernels 2222, **, *2222, 22*, and 2*22.",
    ),
    "pmg": (
        "Two order-2 cone points and one mirror-boundary component.",
        "Its five nontrivial lifts use two colours; their kernels range through 2222, ××, **, 22*, and 22×.",
    ),
    "pgg": (
        "Two order-2 cone points and one crosscap.",
        "Among its three nontrivial lifts, one reaches four colours; its quarter-period glide has kernel K = 2222.",
    ),
    "cmm": (
        "One order-2 cone point and a mirror boundary with two order-2 corners.",
        "Its five two-colour lifts have kernels 2222, *×, *2222, 22×, and 22*.",
    ),
    "p4": (
        "A sphere with cone points of orders 4, 4, and 2.",
        "Three lifts use four colours; two form an inverse-clock pair with the same traditional colour type.",
    ),
    "p4m": (
        "A mirror triangle with corner orders 4, 4, and 2.",
        "All five nontrivial lifts use two colours, despite the fourfold centres; their kernels are *2222, 2*22, 442, *442, and 4*2.",
    ),
    "p4g": (
        "One order-4 cone point and a mirror boundary with one order-2 corner.",
        "Three lifts use two colours and two use four; the four-colour cases have different colour-fixing kernels.",
    ),
    "p3": (
        "A sphere with three order-3 cone points.",
        "Its three nontrivial lifts use three colours: two form an inverse-clock pair, while the third retains a kernel with signature 333.",
    ),
    "p3m1": (
        "A mirror triangle with three order-3 corners.",
        "There is one nontrivial two-colour lift; the odd-corner relation makes the mirror arcs change phase together.",
    ),
    "p31m": (
        "One order-3 cone point and a mirror boundary with one order-3 corner.",
        "Its displayed lifts have N = 2, 3, and 6; the six-colour action combines a third-period rotation with a half-period mirror shift.",
    ),
    "p6": (
        "A sphere with cone points of orders 6, 3, and 2.",
        "Its nontrivial lifts comprise one N = 2 group, an inverse-clock pair at N = 3, and another inverse-clock pair at N = 6.",
    ),
    "p6m": (
        "A mirror triangle with corner orders 6, 3, and 2.",
        "Its three nontrivial lifts all use two colours, with phase-zero kernels 3*3, 632, and *333.",
    ),
}

# Canonical first short color signature printed for each relevant type in
# Table 11.1.  The raised number is the order of the induced permutation on
# colors (p. 136), not a clock-screw numerator.  Several table rows give
# equivalent alternatives; choosing the first keeps each tab label stable.
BOOK_TWO_FOLD_SIGNATURE_BY_TYPE = {
    "*632/3*3": "*¹6²3²2",
    "*632/*333": "*²6¹3¹2",
    "*632/632": "*²6²3²2",
    "632/333": "²6¹3²2",
    "*442/*442": "*¹4¹4²2",
    "*442/4*2": "*¹4²4²2",
    "*442/*2222": "*¹4²4¹2",
    "*442/2*22": "*²4¹4²2",
    "*442/442": "*²4²4²2",
    "4*2/442": "¹4*²2",
    "4*2/2*22": "²4*¹2",
    "4*2/22×": "²4*²2",
    "442/442": "¹4²4²2",
    "442/2222": "²4²4¹2",
    "*333/333": "*²3²3²3",
    "3*3/333": "¹3*²3",
    "*2222/*2222": "*¹2¹2¹2²2",
    "*2222/2*22": "*¹2¹2²2²2",
    "*2222/**": "*¹2²2¹2²2",
    "*2222/22*": "*¹2²2²2²2",
    "*2222/2222": "*²2²2²2²2",
    "2*22/22*": "¹2*¹2²2",
    "2*22/2222": "¹2*²2²2",
    "2*22/*2222": "²2*¹2¹2",
    "2*22/*×": "²2*¹2²2",
    "2*22/22×": "²2*²2²2",
    "22*/2222": "¹2¹2*²",
    "22*/22*": "¹2²2*¹",
    "22*/22×": "¹2²2*²",
    "22*/**": "²2²2*¹",
    "22*/××": "²2²2*²",
    "22×/2222": "¹2¹2×²",
    "22×/××": "²2²2×¹",
    "2222/2222": "¹2¹2²2²2",
    "2222/◦": "²2²2²2²2",
    "*×/◦": "*²×²",
}

# Primefold signatures are checked against Tables 12.1 and 13.1 plus their
# intervening derivations.  g234, g244, and g245 retain explicit discrepancy
# records rather than pretending the book is internally uniform.  Composite
# C4/C6 cases extend the p. 155 convention from audited generator phases.
BOOK_HIGHER_SIGNATURE_BY_ID = {
    "g75": "¹2²2×⁴",
    "g96": "⁴4⁴4²2",
    "g97": "⁴4⁴4²2",
    "g99": "⁴4⁴4¹2",
    "g137": "⁴4*¹2",
    "g139": "⁴4*²2",
    "g225": "³3³3³3",
    "g226": "³3³3³3",
    "g227": "³3³3¹3",
    "g234": "³3*¹3",
    "g235": "³3*²3",
    "g244": "³6³3¹2",
    "g245": "³6³3¹2",
    "g247": "⁶6³3²2",
    "g248": "⁶6³3²2",
}

# K = ker(kappa), classified using zero-phase cosets plus Z^2 translations.
KERNEL_BASE_BY_ID = {
    "g1": "p1", "g5": "p2", "g6": "p1", "g7": "p2",
    "g8": "cm", "g9": "p1", "g10": "pm", "g11": "pg",
    "g54": "pmm", "g55": "p2", "g56": "pmg", "g57": "p2",
    "g58": "pgg", "g59": "p2", "g60": "pm", "g61": "pg",
    "g62": "pm", "g63": "pg", "g64": "pmm", "g65": "pmg",
    "g66": "pmg", "g67": "pgg", "g68": "cmm", "g69": "p2",
    "g70": "cm", "g71": "pmm", "g72": "pgg", "g73": "pmg",
    "g74": "cmm", "g75": "p2", "g94": "p4", "g95": "p2",
    "g96": "p1", "g97": "p1", "g98": "p4", "g99": "p2",
    "g128": "p4m", "g129": "pmm", "g130": "cmm", "g131": "p4",
    "g132": "p4g", "g133": "pgg", "g134": "cmm", "g135": "p4",
    "g136": "p4m", "g137": "pmm", "g138": "p4g", "g139": "pgg",
    "g224": "p3", "g225": "p1", "g226": "p1", "g227": "p3",
    "g230": "p3m1", "g231": "p3", "g232": "p31m", "g233": "p3",
    "g234": "p3m1", "g235": "p3", "g243": "p6", "g244": "p2",
    "g245": "p2", "g246": "p3", "g247": "p1", "g248": "p1",
    "g268": "p6m", "g269": "p31m", "g270": "p6", "g271": "p3m1",
}

# The two rows in each pair differ by inversion of the cyclic clock generator.
# A traditional colouring permits the corresponding global colour relabelling.
INVERSE_CLOCK_MATE = {
    "g96": "g97", "g97": "g96",
    "g225": "g226", "g226": "g225",
    "g244": "g245", "g245": "g244",
    "g247": "g248", "g248": "g247",
}

EXPECTED_ORDER_COUNTS = {1: 17, 2: 36, 3: 6, 4: 6, 5: 0, 6: 3}
DISPLAYED_GROUP_COUNT = 51
OMITTED_TRIVIAL_COUNT = 17
EXPECTED_BOOK_AUDIT_COUNTS = {
    "plane-group": 17,
    "direct-table": 39,
    "internal-discrepancy": 3,
    "composite-extension": 9,
}
BOOK_REPRESENTATIVE_MULTIPLICITY_BY_ID = {
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
EXPECTED_SIGNATURE_EVIDENCE_COUNTS = {
    "onefold": 17,
    "exact-printed": 26,
    "type-representative": 13,
    "book-internal-discrepancy": 3,
    "rule-extension": 9,
}
M_ID = ((1, 0), (0, 1))

# A positive turn is fixed by the catalog's own named rotation generator,
# rather than inferred from screen coordinates (whose y-axis points down).
# Every orientation-preserving point operation in these families is a power
# of the listed matrix.  The remaining represented families only use a
# half-turn, -I.
CANONICAL_TURN_BY_BASE = {
    "p4": (((0, -1), (1, 0)), 4),
    "p4m": (((0, -1), (1, 0)), 4),
    "p4g": (((0, -1), (1, 0)), 4),
    "p3": (((-1, 1), (-1, 0)), 3),
    "p3m1": (((-1, 1), (-1, 0)), 3),
    "p31m": (((-1, 1), (-1, 0)), 3),
    "p6": (((0, 1), (-1, 1)), 6),
    "p6m": (((0, 1), (-1, 1)), 6),
}

SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
SUPERSCRIPT_TO_ASCII = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

# The distinct G/K signatures in Table 11.1, pp. 140--141.  The book counts
# 46 types because **/** has two inequivalent variants; no forward row here
# has that exceptional pair.
TOS_TWO_FOLD_TYPES = {
    "*632/3*3", "*632/*333", "*632/632", "632/333",
    "*442/*442", "*442/4*2", "*442/*2222", "*442/2*22", "*442/442",
    "4*2/442", "4*2/2*22", "4*2/22×", "442/442", "442/2222",
    "*333/333", "3*3/333",
    "*2222/*2222", "*2222/2*22", "*2222/**", "*2222/22*", "*2222/2222",
    "2*22/22*", "2*22/2222", "2*22/*2222", "2*22/*×", "2*22/22×",
    "22*/2222", "22*/22*", "22*/22×", "22*/**", "22*/××",
    "22×/2222", "22×/××", "2222/2222", "2222/◦",
    "**/◦", "**/**", "**/*×", "**/××",
    "*×/**", "*×/××", "*×/◦", "××/××", "××/◦", "◦/◦",
}

TOS_TWO_FOLD_PAGE_BY_PARENT = {
    "*632": 140, "632": 140, "*442": 140, "4*2": 140,
    "442": 140, "*333": 140, "3*3": 140, "333": 140,
    "*2222": 140, "2*22": 140, "22*": 140,
    "22×": 141, "2222": 141, "**": 141, "*×": 141,
    "××": 141, "◦": 141,
}

TOS_THREE_FOLD_DIRECT_TYPES = {"333³/◦", "333³/333", "632³/2222"}

# Composite cyclic colourings are not enumerated by Chapters 11--13.  Each
# one is nevertheless checked through the prime-index layers that the book
# does tabulate.  The phase image check below is what distinguishes C4/C6
# from another extension of the same prime quotients.
COMPOSITE_BOOK_CHAINS = {
    "g75": {
        "intermediate": "2222",
        "steps": (("22×/2222", 2, 141), ("2222/2222", 2, 141)),
    },
    "g96": {
        "intermediate": "2222",
        "steps": (("442/2222", 2, 140), ("2222/◦", 2, 141)),
    },
    "g97": {
        "intermediate": "2222",
        "steps": (("442/2222", 2, 140), ("2222/◦", 2, 141)),
    },
    "g99": {
        "intermediate": "2222",
        "steps": (("442/2222", 2, 140), ("2222/2222", 2, 141)),
    },
    "g137": {
        "intermediate": "2*22",
        "steps": (("4*2/2*22", 2, 140), ("2*22/*2222", 2, 140)),
    },
    "g139": {
        "intermediate": "2*22",
        "steps": (("4*2/2*22", 2, 140), ("2*22/22×", 2, 140)),
    },
    "g235": {
        "intermediate": "333",
        "steps": (("3*3/333", 2, 140), ("333³/333", 3, 156)),
    },
    "g247": {
        "intermediate": "333",
        "steps": (("632/333", 2, 140), ("333³/◦", 3, 156)),
    },
    "g248": {
        "intermediate": "333",
        "steps": (("632/333", 2, 140), ("333³/◦", 3, 156)),
    },
}


def exact_fraction(value: Any) -> Fraction:
    """Recover a small exact catalog fraction from a JSON number."""

    raw = float(value) % 1.0
    candidate = Fraction(raw).limit_denominator(12)
    if abs(float(candidate) - raw) > 1e-8:
        raise ValueError(f"not a small catalog fraction: {value!r}")
    return candidate


def fraction_label(value: Fraction) -> str:
    value %= 1
    if value == 0:
        return "0"
    return f"{value.numerator}/{value.denominator}"


def tos_notation(parent: str, kernel: str, order: int) -> str:
    """Return the book's abbreviated notation for this regular action."""

    if order == 1:
        return parent
    if order == 2:
        return f"{parent}/{kernel}"
    return f"{parent}{str(order).translate(SUPERSCRIPT)}/{kernel}"


def book_color_signature(
    group_id: str,
    parent: str,
    notation: str,
    order: int,
) -> str:
    """Return the book's short generator-permutation signature.

    The superscripts are permutation orders.  They are deliberately stored
    separately from the catalog's clockwork subscripts and tildes.
    """

    if order == 1:
        return parent
    if order == 2:
        try:
            return BOOK_TWO_FOLD_SIGNATURE_BY_TYPE[notation]
        except KeyError as error:
            raise ValueError(f"missing Table 11.1 short signature: {notation}") from error
    try:
        return BOOK_HIGHER_SIGNATURE_BY_ID[group_id]
    except KeyError as error:
        raise ValueError(f"missing higher-fold short signature: {group_id}") from error


def signature_evidence(
    group_id: str,
    order: int,
    notation: str,
) -> dict[str, Any]:
    """Classify how literally the visible short signature follows the book."""

    if order == 1:
        return {
            "status": "onefold",
            "label": "ordinary onefold plane group",
            "summary": "No nontrivial short colour signature is needed.",
        }
    if group_id in BOOK_REPRESENTATIVE_MULTIPLICITY_BY_ID:
        multiplicity = BOOK_REPRESENTATIVE_MULTIPLICITY_BY_ID[group_id]
        return {
            "status": "type-representative",
            "label": "book-normalized representative",
            "summary": (
                f"Table 11.1 groups {multiplicity} equivalent generator signatures "
                f"under the same colour type {notation}. The page uses the first printed "
                "short signature as a stable representative; the G/K type, not this "
                "choice of generators, is the invariant correspondence."
            ),
            "variant_count": multiplicity,
        }
    if order == 2:
        return {
            "status": "exact-printed",
            "label": "unique Table 11.1 short signature",
            "summary": (
                "Table 11.1 prints one short generator signature for this colour type, "
                "and the page reproduces it."
            ),
        }
    if group_id == "g234":
        return {
            "status": "book-internal-discrepancy",
            "label": "signature and kernel split across book rows",
            "summary": (
                "No single book row contains both the displayed order-only signature and "
                "the computed kernel *333. Page 158 supports the short signature but gives "
                "kernel ◦; Table 13.1 supports the 3*3³/*333 type but prints a differently "
                "positioned full cycle label. The page therefore states the synthesis "
                "explicitly instead of calling it a direct book signature."
            ),
        }
    if group_id in {"g244", "g245"}:
        return {
            "status": "book-internal-discrepancy",
            "label": "p. 156 typo corrected by pp. 157 and 164",
            "summary": (
                "The displayed ³6³3¹2 is derived on p. 157 and printed with full "
                "permutations in Table 13.1. Table 12.1 instead has the inconsistent "
                "³6²3²2; the official errata does not list that typo."
            ),
        }
    if order == 3:
        return {
            "status": "exact-printed",
            "label": "exact Table 12.1 short signature",
            "summary": (
                "Table 12.1 prints this order-only short signature for the cited type."
            ),
        }
    if order in (4, 6):
        return {
            "status": "rule-extension",
            "label": f"Goodman–Strauss-style C{order} extension",
            "summary": (
                f"The book does not enumerate composite C{order} colourings. This short "
                "signature is derived from its rule: replace each generator permutation "
                "by its order."
            ),
        }
    raise ValueError(f"unsupported signature evidence for {group_id}")


def orbifold_html(value: str) -> str:
    """Escape notation while giving mirrors the book's baseline math glyph."""

    return escape(value).replace(
        "*",
        '<span class="orbifold-star">∗</span>',
    )


def superscript_html(value: str) -> str:
    """Render Unicode superscript digits as semantic HTML ``sup`` elements."""

    output: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if run:
            output.append(f"<sup>{''.join(run)}</sup>")
            run.clear()

    for character in value:
        if character in "⁰¹²³⁴⁵⁶⁷⁸⁹":
            run.append(character.translate(SUPERSCRIPT_TO_ASCII))
        else:
            flush()
            output.append(orbifold_html(character))
    flush()
    return "".join(output)


def color_type_html(parent: str, kernel: str, order: int) -> str:
    """Typeset G/K while keeping the higher-fold exponent on the whole G."""

    parent_html = orbifold_html(parent)
    if order == 1:
        return parent_html
    if order == 2:
        return f"{parent_html}/{orbifold_html(kernel)}"
    return f'<span class="color-type-group">{parent_html}</span><sup>{order}</sup>/{orbifold_html(kernel)}'


def book_reference(
    printed_page: int,
    label: str,
    *,
    role: str,
    excerpt_key: str,
) -> dict[str, Any]:
    excerpt = BOOK_EXCERPTS.get(excerpt_key)
    if not excerpt or excerpt["printed_page"] != printed_page:
        raise ValueError(f"invalid excerpt key for printed p. {printed_page}: {excerpt_key}")
    return {
        "label": label,
        "role": role,
        "printed_page": printed_page,
        "pdf_page": printed_page + 19,
        "url": BOOK_PAGE_URL.format(page=printed_page),
        "excerpt_key": excerpt_key,
    }


def book_audit(
    group_id: str,
    order: int,
    parent: str,
    kernel: str,
) -> dict[str, Any]:
    """Describe exactly what the attached book does and does not verify."""

    notation = tos_notation(parent, kernel, order)
    if order == 1:
        return {
            "status": "plane-group",
            "status_label": "ordinary plane-group table",
            "summary": (
                f"Table 3.2 lists {parent} among the 17 plane groups. The book calls "
                "this a onefold coloring; it does not write a G¹/G color type."
            ),
            "references": [
                book_reference(
                    40,
                    "Table 3.2 · the 17 plane groups",
                    role="primary",
                    excerpt_key=f"p40::{parent}",
                ),
                book_reference(
                    153,
                    "Onefold and n-fold colorings",
                    role="supporting",
                    excerpt_key="p153::onefold-nfold-definition",
                ),
            ],
            "prime_chain": [],
        }

    if order == 2:
        if notation not in TOS_TWO_FOLD_TYPES:
            raise ValueError(f"twofold type is absent from Table 11.1: {notation}")
        page = TOS_TWO_FOLD_PAGE_BY_PARENT[parent]
        return {
            "status": "direct-table",
            "status_label": "direct Table 11.1 match",
            "summary": (
                f"{notation} appears directly in Table 11.1. Its single slash is the "
                "book's G/K notation for a regular two-colour action."
            ),
            "references": [
                book_reference(
                    page,
                    "Table 11.1 · twofold color types",
                    role="primary",
                    excerpt_key=f"p{page}::{notation}",
                )
            ],
            "prime_chain": [],
        }

    if order == 3 and group_id in {"g244", "g245"}:
        if notation != "632³/2222":
            raise ValueError(
                f"unexpected later-table notation for {group_id}: {notation}"
            )
        return {
            "status": "internal-discrepancy",
            "status_label": "book typo resolved by pp. 157 and 164",
            "summary": (
                "The page's ³6³3¹2 is derived in the prose on p. 157 and Table "
                "13.1 assigns the three generators a 3-cycle, its inverse, and the "
                "identity for type 632³/2222. Table 12.1 on p. 156 instead prints "
                "³6²3²2 beside 632/2222. Those raised 2s denote transpositions and "
                "cannot describe a regular C3 action. We therefore treat p. 156 as "
                "a book error; it is not listed in the authors' online errata."
            ),
            "references": [
                book_reference(
                    164,
                    "Table 13.1 · exact later signature and type",
                    role="primary",
                    excerpt_key="p164::632³/2222-exact",
                ),
                book_reference(
                    157,
                    "Threefold derivation · correct short signature",
                    role="supporting",
                    excerpt_key="p157::632-regular-derivation",
                ),
                book_reference(
                    156,
                    "Table 12.1 · conflicting earlier short signature",
                    role="conflict",
                    excerpt_key="p156::632³/2222",
                ),
            ],
            "prime_chain": [],
        }

    if order == 3 and group_id != "g234":
        if notation not in TOS_THREE_FOLD_DIRECT_TYPES:
            raise ValueError(f"threefold type is absent from Table 12.1: {notation}")
        return {
            "status": "direct-table",
            "status_label": "direct Table 12.1 match",
            "summary": (
                f"{notation} appears as a regular cyclic case in Table 12.1. "
                "Here the stabilizer H of one colour equals the all-colours kernel K."
            ),
            "references": [
                book_reference(
                    156,
                    "Table 12.1 · threefold color types",
                    role="primary",
                    excerpt_key=f"p156::{notation}",
                )
            ],
            "prime_chain": [],
        }

    if group_id == "g234":
        if notation != "3*3³/*333":
            raise ValueError(f"unexpected exceptional notation for g234: {notation}")
        return {
            "status": "internal-discrepancy",
            "status_label": "book-internal discrepancy",
            "summary": (
                "No one book row contains both the displayed short generator signature "
                "and the computed kernel. Table 12.1 and the derivation on p. 158 pair "
                "the short form ³3*¹3 with type 3*3³/◦ (the exponent 3 is understood "
                "there), while Table 13.1 prints the computed type 3*3³/*333 beside a "
                "differently positioned full cycle label. The page keeps the kernel "
                "computed from the clock operations and links Frank Farris's independent "
                "p31m/3p3m1 construction as a check on that parent/kernel type."
            ),
            "references": [
                book_reference(
                    164,
                    "Table 13.1 · later primefold summary",
                    role="primary",
                    excerpt_key="p164::g234-single-slash-table",
                ),
                book_reference(
                    156,
                    "Table 12.1 · same short form, conflicting kernel",
                    role="conflict",
                    excerpt_key="p156::3*3³/◦-conflict",
                ),
                book_reference(
                    158,
                    "Threefold derivation · conflicting prose",
                    role="conflict",
                    excerpt_key="p158::g234-prose-conflict",
                ),
            ],
            "independent_reference": {
                "label": "Farris, Natural Color Symmetry, p. 136",
                "url": FARRIS_URL,
            },
            "prime_chain": [],
        }

    if order in (4, 6):
        chain = COMPOSITE_BOOK_CHAINS.get(group_id)
        if not chain:
            raise ValueError(f"composite coloring lacks a prime-chain audit: {group_id}")
        steps = [
            {
                "notation": step_notation,
                "index": index,
                "printed_page": page,
                "pdf_page": page + 19,
                "url": BOOK_PAGE_URL.format(page=page),
                "excerpt_key": f"p{page}::{step_notation}",
            }
            for step_notation, index, page in chain["steps"]
        ]
        for step in steps:
            if step["index"] == 2 and step["notation"] not in TOS_TWO_FOLD_TYPES:
                raise ValueError(f"composite twofold layer is absent: {step}")
            if step["index"] == 3 and step["notation"] not in TOS_THREE_FOLD_DIRECT_TYPES:
                raise ValueError(f"composite threefold layer is absent: {step}")
        layers = " then ".join(step["notation"] for step in steps)
        return {
            "status": "composite-extension",
            "status_label": f"regular cyclic C{order} extension",
            "summary": (
                f"The book stops after primefold enumeration, so it does not list {notation}. "
                f"Its prime-index layers {layers} are tabulated; the checked phase image "
                f"establishes that their extension is cyclic C{order}. The superscripted "
                "notation follows the rule on p. 155."
            ),
            "references": [
                book_reference(
                    155,
                    "Gⁿ/H/K notation and slash rule",
                    role="primary",
                    excerpt_key="p155::slash-rule",
                ),
                book_reference(
                    169,
                    "End of the book's primefold enumeration",
                    role="scope",
                    excerpt_key="p169::primefold-scope",
                ),
            ],
            "prime_chain": steps,
            "intermediate_orbifold": chain["intermediate"],
        }

    raise ValueError(f"unsupported book audit for {group_id}, order {order}")


def matrix(operation: dict[str, Any]) -> tuple[tuple[int, int], tuple[int, int]]:
    return tuple(tuple(int(x) for x in row) for row in operation["M"])  # type: ignore[return-value]


def det2(m: tuple[tuple[int, int], tuple[int, int]]) -> int:
    return m[0][0] * m[1][1] - m[0][1] * m[1][0]


def multiply2(
    a: tuple[tuple[int, int], tuple[int, int]],
    b: tuple[tuple[int, int], tuple[int, int]],
) -> tuple[tuple[int, int], tuple[int, int]]:
    return (
        (a[0][0] * b[0][0] + a[0][1] * b[1][0],
         a[0][0] * b[0][1] + a[0][1] * b[1][1]),
        (a[1][0] * b[0][0] + a[1][1] * b[1][0],
         a[1][0] * b[0][1] + a[1][1] * b[1][1]),
    )


def spatial_order(m: tuple[tuple[int, int], tuple[int, int]]) -> int:
    power = M_ID
    for order in range(1, 7):
        power = multiply2(power, m)
        if power == M_ID:
            return order
    raise ValueError(f"non-crystallographic spatial matrix: {m!r}")


def operation_kind(operation: dict[str, Any]) -> str:
    m = matrix(operation)
    v = tuple(exact_fraction(x) for x in operation["v"])
    tau = exact_fraction(operation["tau"])
    if m == M_ID:
        if v == (0, 0) and tau == 0:
            return "identity"
        return "translations"
    if det2(m) == -1:
        return "reflections / glides"
    order = spatial_order(m)
    return f"{order}-fold rotations"


def phase_order(operations: Iterable[dict[str, Any]]) -> int:
    result = 1
    for operation in operations:
        if operation["s"] != 1:
            raise ValueError("a forward correspondence cannot contain time reversal")
        result = math.lcm(result, exact_fraction(operation["tau"]).denominator)
    return result


def phase_profile(operations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    profile: dict[str, set[Fraction]] = defaultdict(set)
    for operation in operations:
        kind = operation_kind(operation)
        if kind == "identity":
            continue
        profile[kind].add(exact_fraction(operation["tau"]))

    rank = {
        "translations": 0,
        "2-fold rotations": 1,
        "3-fold rotations": 2,
        "4-fold rotations": 3,
        "6-fold rotations": 4,
        "reflections / glides": 5,
    }
    return [
        {
            "operation": kind,
            "phases": [fraction_label(x) for x in sorted(values)],
        }
        for kind, values in sorted(profile.items(), key=lambda item: rank[item[0]])
    ]


def _matrix_power(
    value: tuple[tuple[int, int], tuple[int, int]],
    exponent: int,
) -> tuple[tuple[int, int], tuple[int, int]]:
    result = M_ID
    for _ in range(exponent):
        result = multiply2(result, value)
    return result


def _rotation_turn(
    base: str,
    value: tuple[tuple[int, int], tuple[int, int]],
) -> Fraction:
    """Return the catalog-oriented fraction of one positive full turn."""

    canonical = CANONICAL_TURN_BY_BASE.get(base)
    if canonical:
        generator, order = canonical
        for exponent in range(1, order):
            if _matrix_power(generator, exponent) == value:
                return Fraction(exponent, order)
    if value == ((-1, 0), (0, -1)):
        return Fraction(1, 2)
    raise ValueError(f"cannot name rotation matrix {value!r} in {base}")


def _rotation_center(
    value: tuple[tuple[int, int], tuple[int, int]],
    translation: tuple[Fraction, Fraction],
) -> tuple[Fraction, Fraction]:
    """Solve (I-M)c=v and reduce the unique rotation centre modulo one cell."""

    a00 = 1 - value[0][0]
    a01 = -value[0][1]
    a10 = -value[1][0]
    a11 = 1 - value[1][1]
    determinant = a00 * a11 - a01 * a10
    if determinant == 0:
        raise ValueError(f"rotation has no unique centre: {value!r}")
    x = (translation[0] * a11 - a01 * translation[1]) / determinant
    y = (a00 * translation[1] - translation[0] * a10) / determinant
    return (x % 1, y % 1)


def _centered_fraction(value: Fraction) -> Fraction:
    value %= 1
    return value - 1 if value > Fraction(1, 2) else value


def _translation_description(translation: tuple[Fraction, Fraction]) -> str:
    x, y = (_centered_fraction(value) for value in translation)
    terms: list[tuple[Fraction, str]] = [
        (coefficient, name)
        for coefficient, name in ((x, "a"), (y, "b"))
        if coefficient
    ]
    if not terms:
        return "Pure time step"
    if len(terms) == 1:
        coefficient, name = terms[0]
        amount = fraction_label(abs(coefficient))
        direction = f"along {name}" if coefficient > 0 else f"opposite {name}"
        return f"{amount}-cell translation {direction}"

    pieces: list[str] = []
    for index, (coefficient, name) in enumerate(terms):
        amount = fraction_label(abs(coefficient))
        term = f"{amount} {name}"
        if index == 0:
            pieces.append(("−" if coefficient < 0 else "") + term)
        else:
            pieces.append((" − " if coefficient < 0 else " + ") + term)
    return "Translation by " + "".join(pieces)


def _turn_description(turn: Fraction) -> str:
    degrees = int(turn * 360)
    if turn == Fraction(1, 2):
        return "Half-turn rotation (180°)"
    return f"{fraction_label(turn)}-turn rotation ({degrees}°)"


def _time_shift_description(value: Fraction) -> str:
    value %= 1
    return "none" if value == 0 else f"+{fraction_label(value)} period"


def _operation_closure(seeds: Iterable[tuple[Any, ...]]) -> set[tuple[Any, ...]]:
    identity = (M_ID, (Fraction(0), Fraction(0)), 1, Fraction(0))
    seed_list = list(seeds)
    result = {identity}
    changed = True
    while changed:
        changed = False
        for known in tuple(result):
            for seed in seed_list:
                for product in (compose_keys(known, seed), compose_keys(seed, known)):
                    if product not in result:
                        result.add(product)
                        changed = True
    return result


def _minimal_operation_generators(
    operations: list[dict[str, Any]],
    all_keys: set[tuple[Any, ...]],
) -> tuple[tuple[Any, ...], ...]:
    """Choose a small, deterministic generating set for the finite cell action."""

    identity = (M_ID, (Fraction(0), Fraction(0)), 1, Fraction(0))
    if all_keys == {identity}:
        return ()

    priority = {"translation": 0, "mirror": 1, "rotation": 2, "glide": 3}
    candidates = sorted(
        operations,
        key=lambda operation: (
            priority[operation["kind"]],
            operation["matrix"],
            operation["translation"],
            operation["phase_fraction"],
        ),
    )
    candidate_keys = [operation["key"] for operation in candidates]
    for size in range(1, min(6, len(candidate_keys)) + 1):
        for seeds in combinations(candidate_keys, size):
            if _operation_closure(seeds) == all_keys:
                return seeds
    raise ValueError("could not find a compact generator set for the cell action")


def geometric_operations(
    render: dict[str, Any],
    base: str,
) -> list[dict[str, str]]:
    """Name a compact generating set and each generator's nonidentity powers.

    The finite action is taken modulo the two full-cell translations.  Unlike
    ``phase_profile``, this keeps inverse rotations, distinct mirror axes, and
    the exact numerator of every time shift visible without listing every
    product of different generators.
    """

    operations = []
    for source_index, operation in enumerate(render["ops"]):
        value = matrix(operation)
        translation = tuple(exact_fraction(x) for x in operation["v"])
        phase = exact_fraction(operation["tau"])
        if value == M_ID and translation == (Fraction(0), Fraction(0)) and phase == 0:
            continue
        determinant = det2(value)
        if value == M_ID:
            kind = "translation"
        elif determinant == 1:
            kind = "rotation"
        elif determinant == -1:
            square_translation = (
                translation[0]
                + value[0][0] * translation[0]
                + value[0][1] * translation[1],
                translation[1]
                + value[1][0] * translation[0]
                + value[1][1] * translation[1],
            )
            kind = "mirror" if square_translation == (0, 0) else "glide"
        else:
            raise ValueError(f"unsupported affine operation in {base}: {operation!r}")
        operations.append(
            {
                "source_index": source_index,
                "key": op_key(operation),
                "matrix": value,
                "translation": translation,
                "phase_fraction": phase,
                "kind": kind,
            }
        )

    rotation_centres = sorted(
        {
            _rotation_center(operation["matrix"], operation["translation"])
            for operation in operations
            if operation["kind"] == "rotation"
        }
    )
    centre_names = {
        centre: chr(ord("A") + index)
        for index, centre in enumerate(rotation_centres)
    }
    axis_matrices = sorted(
        {
            operation["matrix"]
            for operation in operations
            if operation["kind"] in {"mirror", "glide"}
        }
    )
    axis_names = {
        value: chr(ord("A") + index)
        for index, value in enumerate(axis_matrices)
    }

    rows: list[dict[str, str]] = []
    translations = sorted(
        (operation for operation in operations if operation["kind"] == "translation"),
        key=lambda operation: (operation["translation"], operation["phase_fraction"]),
    )
    for operation in translations:
        rows.append(
            {
                "kind": "translation",
                "source_index": operation["source_index"],
                "operation": _translation_description(operation["translation"]),
                "phase": fraction_label(operation["phase_fraction"]),
                "time_shift": _time_shift_description(operation["phase_fraction"]),
            }
        )

    rotations = []
    for operation in operations:
        if operation["kind"] != "rotation":
            continue
        centre = _rotation_center(operation["matrix"], operation["translation"])
        rotations.append(
            (
                _rotation_turn(base, operation["matrix"]),
                centre,
                operation,
            )
        )
    for turn, centre, operation in sorted(
        rotations,
        key=lambda item: (item[0], item[1], item[2]["phase_fraction"]),
    ):
        description = _turn_description(turn)
        if len(rotation_centres) > 1:
            description += f" about centre {centre_names[centre]}"
        rows.append(
            {
                "kind": "rotation",
                "source_index": operation["source_index"],
                "operation": description,
                "phase": fraction_label(operation["phase_fraction"]),
                "time_shift": _time_shift_description(operation["phase_fraction"]),
            }
        )

    axis_operations = sorted(
        (
            operation
            for operation in operations
            if operation["kind"] in {"mirror", "glide"}
        ),
        key=lambda operation: (
            axis_matrices.index(operation["matrix"]),
            0 if operation["kind"] == "mirror" else 1,
            operation["translation"],
            operation["phase_fraction"],
        ),
    )
    axis_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for operation in axis_operations:
        axis_groups[(operation["matrix"], operation["kind"])].append(operation)

    seen: dict[tuple[Any, ...], int] = defaultdict(int)
    for operation in axis_operations:
        group_key = (operation["matrix"], operation["kind"])
        seen[group_key] += 1
        ordinal = seen[group_key]
        count = len(axis_groups[group_key])
        noun = "Mirror reflection" if operation["kind"] == "mirror" else "Glide reflection"
        if count > 1:
            if ordinal > 1:
                noun = f"Parallel {noun.lower()} {ordinal}"
        if len(axis_matrices) > 1:
            noun += f" (axis direction {axis_names[operation['matrix']]})"
        rows.append(
            {
                "kind": operation["kind"],
                "source_index": operation["source_index"],
                "operation": noun,
                "phase": fraction_label(operation["phase_fraction"]),
                "time_shift": _time_shift_description(operation["phase_fraction"]),
            }
        )

    identity = (M_ID, (Fraction(0), Fraction(0)), 1, Fraction(0))
    all_keys = {identity, *(operation["key"] for operation in operations)}
    seeds = _minimal_operation_generators(operations, all_keys)
    row_by_key = {
        op_key(render["ops"][row["source_index"]]): row
        for row in rows
    }
    selected: list[dict[str, str]] = []
    selected_keys: set[tuple[Any, ...]] = set()
    for generator_index, seed in enumerate(seeds):
        generator_name = chr(ord("A") + generator_index)
        power_key = identity
        returned_to_identity = False
        for exponent in range(1, len(all_keys) + 1):
            power_key = compose_keys(power_key, seed)
            if power_key == identity:
                returned_to_identity = True
                break
            if power_key in selected_keys:
                continue
            source = row_by_key[power_key]
            selected_keys.add(power_key)
            selected.append(
                {
                    "generator": generator_name,
                    "power": str(exponent),
                    "role": "generator" if exponent == 1 else "power",
                    "kind": source["kind"],
                    "operation": source["operation"],
                    "phase": source["phase"],
                    "time_shift": source["time_shift"],
                }
            )
        if not returned_to_identity:
            raise ValueError(f"generator {generator_name} does not close in {base}")
    return selected


def op_key(operation: dict[str, Any]) -> tuple[Any, ...]:
    return (
        matrix(operation),
        tuple(exact_fraction(x) for x in operation["v"]),
        int(operation["s"]),
        exact_fraction(operation["tau"]),
    )


def compose_keys(left: tuple[Any, ...], right: tuple[Any, ...]) -> tuple[Any, ...]:
    m1, v1, s1, tau1 = left
    m2, v2, s2, tau2 = right
    m = multiply2(m1, m2)
    v = (
        (m1[0][0] * v2[0] + m1[0][1] * v2[1] + v1[0]) % 1,
        (m1[1][0] * v2[0] + m1[1][1] * v2[1] + v1[1]) % 1,
    )
    return (m, v, s1 * s2, (s1 * tau2 + tau1) % 1)


def validate_render(group_id: str, render: dict[str, Any], order: int) -> None:
    if set(render) != {"basis", "base", "ops"}:
        raise ValueError(f"unexpected render fields in {group_id}")
    operations = render["ops"]
    keys = {op_key(operation) for operation in operations}
    if len(keys) != len(operations):
        raise ValueError(f"duplicate operation in {group_id}")
    identity = (M_ID, (Fraction(0), Fraction(0)), 1, Fraction(0))
    if identity not in keys:
        raise ValueError(f"identity missing in {group_id}")
    for left in keys:
        for right in keys:
            if compose_keys(left, right) not in keys:
                raise ValueError(f"operation set is not closed in {group_id}")

    phases = {key[3] for key in keys}
    expected = {Fraction(j, order) for j in range(order)}
    if phases != expected:
        raise ValueError(f"phase image is not C_{order} in {group_id}: {phases}")

    spatial_phase: dict[tuple[Any, ...], Fraction] = {}
    for m, v, _s, tau in keys:
        spatial = (m, v)
        if spatial in spatial_phase and spatial_phase[spatial] != tau:
            raise ValueError(f"one spatial operation has conflicting phases in {group_id}")
        spatial_phase[spatial] = tau


def phase_character_signature(
    group: dict[str, Any], *, invert_clock: bool = False
) -> tuple[Any, ...]:
    """Coordinate signature of one embedded kernel, modulo clock inversion."""

    order = group["clock_order"]
    rows = []
    for operation in group["render"]["ops"]:
        phase = int(exact_fraction(operation["tau"]) * order) % order
        if invert_clock:
            phase = (-phase) % order
        rows.append(
            (
                matrix(operation),
                tuple(exact_fraction(x) for x in operation["v"]),
                phase,
            )
        )
    return (
        group["parent"]["hm"],
        group["kernel"]["hm"],
        order,
        tuple(sorted(rows)),
    )


def clockwork_description(group: dict[str, Any], order: int) -> str:
    parent = ORBIFOLD_BY_BASE[group["base"]]
    if order == 1:
        return (
            f"The direct-product lift over plane orbifold {parent} has trivial "
            "phase character: every spatial operation maps to phase 0."
        )
    profile = phase_profile(group["render"]["ops"])
    assignments = "; ".join(
        f"{row['operation']}: {', '.join(row['phases'])}" for row in profile
    )
    return (
        f"The phase character maps the plane orbifold {parent} onto C{order}. "
        f"The operation phases are {assignments}."
    )


def coloring_description(group: dict[str, Any], order: int, kernel_base: str) -> str:
    parent = ORBIFOLD_BY_BASE[group["base"]]
    kernel = ORBIFOLD_BY_BASE[kernel_base]
    notation = tos_notation(parent, kernel, order)
    if order == 1:
        return (
            f"The phase character is trivial, so K = G. In the book's terminology this is "
            f"the onefold plane group {notation}, not a G¹/G colour-type label. The static "
            "plate is monochrome."
        )
    if order == 2:
        type_opening = (
            f"The book colour type is {notation}: twofold is understood, so no "
            "exponent 2 is printed, and the orbifold signature after the slash is "
            f"the colour-fixing kernel K = {kernel}."
        )
    else:
        qualifier = "book-style" if order in (4, 6) else "book"
        type_opening = (
            f"The {qualifier} colour type is {notation}: the exponent {order} on G "
            "counts the colours, and the orbifold signature after the slash is the "
            f"colour-fixing kernel K = {kernel}."
        )
    return (
        f"{type_opening} Here [G:K] = {order} and G/K is isomorphic to C{order}. "
        "The one-slash form is valid because this cyclic colour action is regular, so "
        "the stabilizer H of one chosen colour equals K. "
        f"An operation at phase j/{order} sends colour k to k+j modulo {order}."
    )


def build_payload(source_catalog: Path) -> dict[str, Any]:
    raw = source_catalog.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(
            "unexpected source catalog digest; audit the source before changing the pin: "
            f"{digest}"
        )
    catalog = json.loads(raw)
    if catalog.get("meta", {}).get("total") != 275 or len(catalog.get("groups", [])) != 275:
        raise ValueError("the pinned source must contain 275 groups")
    source_groups = [group for group in catalog["groups"] if group["forward"]]
    if len(source_groups) != 68:
        raise ValueError("the pinned source must contain 68 forward groups")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_rows = manifest["groups"]
    if [group["id"] for group in source_groups] != [row["id"] for row in manifest_rows]:
        raise ValueError("forward source order differs from the checked-in manifest")

    records = []
    for ordinal, (group, manifest_row) in enumerate(zip(source_groups, manifest_rows), 1):
        group_id = group["id"]
        order = phase_order(group["render"]["ops"])
        if (
            group["symbol"] != manifest_row["symbol"]
            or group["base"] != manifest_row["base"]
            or order != manifest_row["canonical_clock_order"]
        ):
            raise ValueError(f"source differs from the compact manifest at {group_id}")
        kernel_base = KERNEL_BASE_BY_ID[group_id]
        parent_orbifold = ORBIFOLD_BY_BASE[group["base"]]
        kernel_orbifold = ORBIFOLD_BY_BASE[kernel_base]
        notation = tos_notation(parent_orbifold, kernel_orbifold, order)
        short_signature = book_color_signature(
            group_id, parent_orbifold, notation, order
        )
        validate_render(group_id, group["render"], order)
        residues = [
            {
                "index": j,
                "phase": fraction_label(Fraction(j, order)),
                "color": PALETTE[j],
            }
            for j in range(order)
        ]
        record = {
            "ordinal": ordinal,
            "id": group_id,
            "symbol": group["symbol"],
            "system": group["system"],
            "bravais": group["bravais"],
            "product": bool(group["product"]),
            "symmorphic": bool(group["symmorphic"]),
            "parent": {"orbifold": parent_orbifold, "hm": group["base"]},
            "kernel": {"orbifold": kernel_orbifold, "hm": kernel_base},
            "tos_notation": notation,
            "book_color_signature": short_signature,
            "signature_evidence": signature_evidence(group_id, order, notation),
            "clock_order": order,
            "cyclic_group": f"C_{order}",
            "phase_residues": residues,
            "phase_profile": phase_profile(group["render"]["ops"]),
            "geometric_operations": geometric_operations(group["render"], group["base"]),
            "clockwork_description": clockwork_description(group, order),
            "coloring_description": coloring_description(group, order, kernel_base),
            "book_audit": book_audit(
                group_id, order, parent_orbifold, kernel_orbifold
            ),
            "inverse_clock_mate": INVERSE_CLOCK_MATE.get(group_id),
            "catalog_url": f"{CATALOG_ROOT}#{group_id}",
            "image": f"output/clockwork-colorings/{group_id}.webp",
            "image_alt": (
                f"Static perfect {order}-colouring for group {group_id}: "
                f"asymmetric motifs carry phase colours for Conway type {notation}."
            ),
            "render": group["render"],
        }
        records.append(record)

    payload = {
        "meta": {
            "schema_version": 5,
            "title": "Clockwork/coloring correspondence",
            "source_catalog_url": CATALOG_DATA_URL,
            "source_catalog_sha256": digest,
            "source_catalog_total_groups": 275,
            "selection": "group.forward == true",
            "forward_groups": 68,
            "traditional_color_classes_after_clock_inversion": 64,
            "definition": (
                "kappa(M,v) = N*tau mod N; K = ker(kappa); regular action has H = K; "
                "ToS type is G for N=1, G/K for N=2, and G^N/K for N>2"
            ),
            "book_audit_counts": EXPECTED_BOOK_AUDIT_COUNTS,
            "signature_evidence_counts": EXPECTED_SIGNATURE_EVIDENCE_COUNTS,
            "book": {
                "title": "The Symmetries of Things",
                "authors": ["John H. Conway", "Heidi Burgiel", "Chaim Goodman-Strauss"],
                "edition": 2008,
                "record_url": BOOK_RECORD_URL,
                "errata_url": BOOK_ERRATA_URL,
                "note": (
                    "Printed-page links open local highlighted evidence crops with Google "
                    "Books as the no-JavaScript and complete-page fallback; attached-PDF "
                    "indices are stored separately for audit reproducibility."
                ),
                "annotated_excerpt_count": len(BOOK_EXCERPTS),
            },
            "kernel_method": (
                "Classify the tau=0 spatial operations plus their own translation lattice "
                "against the 17 canonical wallpaper groups."
            ),
            "image_palette": list(PALETTE),
            "image_size": [IMAGE_WIDTH, IMAGE_HEIGHT],
        },
        "groups": records,
    }
    validate_payload(payload)
    return payload


def refresh_derived_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Refresh prose and book-audit fields without rereading the source catalog.

    Geometry and classifications remain pinned in the checked-in extract. This
    narrow migration is useful when source-facing wording or book evidence is
    corrected without changing any group operation.
    """

    for record in payload.get("groups", []):
        order = record["clock_order"]
        group_id = record["id"]
        parent = record["parent"]["orbifold"]
        kernel = record["kernel"]["orbifold"]
        source_like = {
            "symbol": record["symbol"],
            "base": record["parent"]["hm"],
            "render": record["render"],
        }
        notation = tos_notation(parent, kernel, order)
        record["tos_notation"] = notation
        record["book_color_signature"] = book_color_signature(
            group_id, parent, notation, order
        )
        record["signature_evidence"] = signature_evidence(
            group_id, order, notation
        )
        record["phase_profile"] = phase_profile(record["render"]["ops"])
        record["geometric_operations"] = geometric_operations(
            record["render"], record["parent"]["hm"]
        )
        record["clockwork_description"] = clockwork_description(source_like, order)
        record["coloring_description"] = coloring_description(
            source_like, order, record["kernel"]["hm"]
        )
        record["book_audit"] = book_audit(group_id, order, parent, kernel)
        record["image_alt"] = (
            f"Static perfect {order}-colouring for group {group_id}: "
            f"asymmetric motifs carry phase colours for Conway type {notation}."
        )

    meta = payload["meta"]
    meta["schema_version"] = 5
    meta["book_audit_counts"] = EXPECTED_BOOK_AUDIT_COUNTS
    meta["signature_evidence_counts"] = EXPECTED_SIGNATURE_EVIDENCE_COUNTS
    meta["book"]["annotated_excerpt_count"] = len(BOOK_EXCERPTS)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    meta = payload.get("meta", {})
    groups = payload.get("groups", [])
    if meta.get("schema_version") != 5:
        raise ValueError("correspondence data must use schema version 5")
    if meta.get("source_catalog_sha256") != SOURCE_SHA256:
        raise ValueError("correspondence data does not identify the pinned source")
    if meta.get("forward_groups") != 68 or len(groups) != 68:
        raise ValueError("correspondence must contain exactly 68 groups")
    if set(KERNEL_BASE_BY_ID) != {group.get("id") for group in groups}:
        raise ValueError("kernel audit and correspondence ids differ")
    if [group["ordinal"] for group in groups] != list(range(1, 69)):
        raise ValueError("correspondence ordinals must be 1 through 68")
    if len({group["id"] for group in groups}) != 68:
        raise ValueError("correspondence ids must be unique")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["groups"]
    compact = [
        (group["id"], group["symbol"], group["parent"]["hm"], group["clock_order"])
        for group in groups
    ]
    expected_compact = [
        (row["id"], row["symbol"], row["base"], row["canonical_clock_order"])
        for row in manifest
    ]
    if compact != expected_compact:
        raise ValueError("correspondence does not match the audited forward manifest")

    counts = Counter(group["clock_order"] for group in groups)
    if {n: counts.get(n, 0) for n in range(1, 7)} != EXPECTED_ORDER_COUNTS:
        raise ValueError(f"unexpected clock-order distribution: {counts}")

    audit_counts = Counter(group["book_audit"]["status"] for group in groups)
    if dict(audit_counts) != EXPECTED_BOOK_AUDIT_COUNTS:
        raise ValueError(f"unexpected book-audit distribution: {audit_counts}")
    if meta.get("book_audit_counts") != EXPECTED_BOOK_AUDIT_COUNTS:
        raise ValueError("book-audit totals differ from the row statuses")

    signature_counts = Counter(
        group["signature_evidence"]["status"] for group in groups
    )
    if dict(signature_counts) != EXPECTED_SIGNATURE_EVIDENCE_COUNTS:
        raise ValueError(f"unexpected signature-evidence distribution: {signature_counts}")
    if meta.get("signature_evidence_counts") != EXPECTED_SIGNATURE_EVIDENCE_COUNTS:
        raise ValueError("signature-evidence totals differ from the row statuses")

    for group in groups:
        group_id = group["id"]
        order = group["clock_order"]
        if group["parent"]["orbifold"] != ORBIFOLD_BY_BASE[group["parent"]["hm"]]:
            raise ValueError(f"parent notation mismatch in {group_id}")
        if group["kernel"]["hm"] != KERNEL_BASE_BY_ID[group_id]:
            raise ValueError(f"kernel type mismatch in {group_id}")
        if group["kernel"]["orbifold"] != ORBIFOLD_BY_BASE[group["kernel"]["hm"]]:
            raise ValueError(f"kernel notation mismatch in {group_id}")
        expected_notation = tos_notation(
            group["parent"]["orbifold"], group["kernel"]["orbifold"], order
        )
        if group["tos_notation"] != expected_notation:
            raise ValueError(f"ToS notation mismatch in {group_id}")
        expected_short_signature = book_color_signature(
            group_id,
            group["parent"]["orbifold"],
            expected_notation,
            order,
        )
        if group.get("book_color_signature") != expected_short_signature:
            raise ValueError(f"book color signature mismatch in {group_id}")
        expected_signature_evidence = signature_evidence(
            group_id, order, expected_notation
        )
        if group.get("signature_evidence") != expected_signature_evidence:
            raise ValueError(f"signature evidence mismatch in {group_id}")
        if "//" in group["tos_notation"]:
            raise ValueError(f"regular cyclic action uses a double slash in {group_id}")
        if group["parent"]["hm"] == "p1" and "◦" not in group["parent"]["orbifold"]:
            raise ValueError(f"p1 does not use the ToS wonder-ring in {group_id}")
        expected_audit = book_audit(
            group_id,
            order,
            group["parent"]["orbifold"],
            group["kernel"]["orbifold"],
        )
        if group["book_audit"] != expected_audit:
            raise ValueError(f"book audit mismatch in {group_id}")
        primary_refs = [
            reference
            for reference in group["book_audit"]["references"]
            if reference["role"] == "primary"
        ]
        if len(primary_refs) != 1:
            raise ValueError(f"book audit needs one primary page in {group_id}")
        for reference in group["book_audit"]["references"]:
            excerpt = BOOK_EXCERPTS.get(reference.get("excerpt_key"))
            if not excerpt:
                raise ValueError(f"book reference lacks an excerpt asset in {group_id}")
            if (
                excerpt["printed_page"] != reference["printed_page"]
                or excerpt["pdf_page"] != reference["pdf_page"]
            ):
                raise ValueError(f"book reference page and excerpt differ in {group_id}")
        for step in group["book_audit"]["prime_chain"]:
            excerpt = BOOK_EXCERPTS.get(step.get("excerpt_key"))
            if not excerpt or excerpt["printed_page"] != step["printed_page"]:
                raise ValueError(f"prime-chain link lacks an excerpt asset in {group_id}")
        if group["catalog_url"] != f"{CATALOG_ROOT}#{group_id}":
            raise ValueError(f"catalog deep link mismatch in {group_id}")
        if [row["index"] for row in group["phase_residues"]] != list(range(order)):
            raise ValueError(f"phase legend mismatch in {group_id}")
        expected_operations = geometric_operations(group["render"], group["parent"]["hm"])
        if group.get("geometric_operations") != expected_operations:
            raise ValueError(f"geometric operations differ from render data in {group_id}")
        represented_phases = {
            exact_fraction(operation["tau"])
            for operation in group["render"]["ops"]
        }
        operation_phases = {
            Fraction(row["phase"])
            for row in expected_operations
        }
        if not operation_phases.issubset(represented_phases):
            raise ValueError(f"geometric operation phase mismatch in {group_id}")
        if order > 1:
            generated_order = 1
            for phase in operation_phases:
                generated_order = math.lcm(generated_order, phase.denominator)
            if generated_order != order:
                raise ValueError(f"geometric operation phases do not generate C_{order} in {group_id}")
        validate_render(group_id, group["render"], order)

    for group_id, mate_id in INVERSE_CLOCK_MATE.items():
        group = next(row for row in groups if row["id"] == group_id)
        mate = next(row for row in groups if row["id"] == mate_id)
        if group["inverse_clock_mate"] != mate_id or mate["inverse_clock_mate"] != group_id:
            raise ValueError("inverse-clock mate relation is not reciprocal")
        if (
            group["parent"] != mate["parent"]
            or group["kernel"] != mate["kernel"]
            or group["clock_order"] != mate["clock_order"]
        ):
            raise ValueError(f"inverse-clock pair differs as a traditional coloring: {group_id}")

    color_classes: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for group in groups:
        signature = min(
            phase_character_signature(group),
            phase_character_signature(group, invert_clock=True),
        )
        color_classes[signature].append(group["id"])
    repeated = {
        frozenset(ids) for ids in color_classes.values() if len(ids) > 1
    }
    expected_repeated = {
        frozenset((group_id, mate_id))
        for group_id, mate_id in INVERSE_CLOCK_MATE.items()
    }
    if len(color_classes) != 64 or repeated != expected_repeated:
        raise ValueError("traditional clock-inversion quotient must have 64 classes")
    if meta.get("traditional_color_classes_after_clock_inversion") != len(color_classes):
        raise ValueError("traditional color-class total does not match the operations")


def _mat_inv(a: list[list[float]]) -> list[list[float]]:
    determinant = a[0][0] * a[1][1] - a[0][1] * a[1][0]
    return [
        [a[1][1] / determinant, -a[0][1] / determinant],
        [-a[1][0] / determinant, a[0][0] / determinant],
    ]


def _mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [
        [a[0][0] * b[0][0] + a[0][1] * b[1][0],
         a[0][0] * b[0][1] + a[0][1] * b[1][1]],
        [a[1][0] * b[0][0] + a[1][1] * b[1][0],
         a[1][0] * b[0][1] + a[1][1] * b[1][1]],
    ]


def _site_geometry(
    spec: dict[str, Any], width: int, height: int
) -> tuple[list[float], list[float], float, tuple[range, range]]:
    basis = spec["basis"]
    minimum_side = min(width, height)
    if minimum_side == height:
        span = max(abs(basis[0][1]), abs(basis[1][1])) or 1
    else:
        span = max(abs(basis[0][0]), abs(basis[1][0])) or 1

    def cell_for(repeats: int) -> float:
        return max(minimum_side / (repeats * span), 24 * ANTIALIAS)

    cell = cell_for(4)
    spatial_sites = {
        (tuple(sum(operation["M"], [])),
         tuple(exact_fraction(x) for x in operation["v"]))
        for operation in spec["ops"]
    }
    basis_det = abs(
        basis[0][0] * basis[1][1] - basis[0][1] * basis[1][0]
    ) or 1
    columns = width / math.sqrt(basis_det * cell * cell / len(spatial_sites))
    if columns > 18:
        cell *= columns / 18

    def vectors(scale: float) -> tuple[list[float], list[float]]:
        return (
            [basis[0][0] * scale, -basis[0][1] * scale],
            [basis[1][0] * scale, -basis[1][1] * scale],
        )

    def radius_for(scale: float) -> tuple[list[float], list[float], float]:
        b1, b2 = vectors(scale)
        sites = []
        base = spec.get("base", [0.31, 0.17])
        for operation in spec["ops"]:
            m = operation["M"]
            bx = (m[0][0] * base[0] + m[0][1] * base[1] + operation["v"][0]) % 1
            by = (m[1][0] * base[0] + m[1][1] * base[1] + operation["v"][1]) % 1
            for i in (0, 1):
                for j in (0, 1):
                    sites.append((bx + i, by + j))
        min_distance = min(math.hypot(*b1), math.hypot(*b2))
        for index, left in enumerate(sites):
            for right in sites[index + 1:]:
                dx = (left[0] - right[0]) * b1[0] + (left[1] - right[1]) * b2[0]
                dy = (left[0] - right[0]) * b1[1] + (left[1] - right[1]) * b2[1]
                distance = math.hypot(dx, dy)
                if 1e-6 < distance < min_distance:
                    min_distance = distance
        radius = min(
            0.39 * min(math.hypot(*b1), math.hypot(*b2)),
            0.48 * min_distance,
        )
        return b1, b2, radius

    b1, b2, radius = radius_for(cell)
    minimum_radius = PLATE_MIN_MOTIF_RADIUS_PX * ANTIALIAS
    if 0 < radius < minimum_radius:
        cell *= minimum_radius / radius
        b1, b2, radius = radius_for(cell)
    if radius + 1e-6 < minimum_radius:
        raise ValueError(
            f"plate motif radius {radius / ANTIALIAS:.3f}px is below the minimum"
        )

    inverse = _mat_inv([[b1[0], b2[0]], [b1[1], b2[1]]])
    m1s: list[float] = []
    m2s: list[float] = []
    center_x, center_y = width / 2, height / 2
    for px, py in ((0, 0), (width, 0), (0, height), (width, height)):
        x, y = px - center_x, py - center_y
        m1s.append(inverse[0][0] * x + inverse[0][1] * y)
        m2s.append(inverse[1][0] * x + inverse[1][1] * y)
    pad = 2
    ranges = (
        range(math.floor(min(m1s) - pad), math.ceil(max(m1s) + pad) + 1),
        range(math.floor(min(m2s) - pad), math.ceil(max(m2s) + pad) + 1),
    )
    return b1, b2, radius, ranges


def render_plate(record: dict[str, Any]) -> bytes:
    width = IMAGE_WIDTH * ANTIALIAS
    height = IMAGE_HEIGHT * ANTIALIAS
    background = "#F7F4EC"
    outline = "#26332F"
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    spec = record["render"]
    b1, b2, radius, ranges = _site_geometry(spec, width, height)
    pixel_basis = [[b1[0], b2[0]], [b1[1], b2[1]]]
    inverse_basis = _mat_inv(pixel_basis)
    base = spec.get("base", [0.31, 0.17])
    center_x, center_y = width / 2, height / 2

    # A deliberately asymmetric, chiral stamp; its transformed copies make
    # rotations, reflections and glides visible without a clock overlay.
    local_mark = (0.16, -0.34)

    for operation in spec["ops"]:
        m = operation["M"]
        transform = _mat_mul(
            _mat_mul(pixel_basis, [[float(x) for x in row] for row in m]),
            inverse_basis,
        )
        bx = m[0][0] * base[0] + m[0][1] * base[1] + operation["v"][0]
        by = m[1][0] * base[0] + m[1][1] * base[1] + operation["v"][1]
        phase_index = int(exact_fraction(operation["tau"]) * record["clock_order"])
        color = PALETTE[phase_index]
        for lattice_x in ranges[0]:
            for lattice_y in ranges[1]:
                x = center_x + (bx + lattice_x) * b1[0] + (by + lattice_y) * b2[0]
                y = center_y + (bx + lattice_x) * b1[1] + (by + lattice_y) * b2[1]
                if not (-2 * radius <= x <= width + 2 * radius and
                        -2 * radius <= y <= height + 2 * radius):
                    continue
                points = []
                for local_x, local_y in PLATE_MOTIF_SHAPE:
                    dx = radius * (transform[0][0] * local_x + transform[0][1] * local_y)
                    dy = radius * (transform[1][0] * local_x + transform[1][1] * local_y)
                    points.append((x + dx, y + dy))
                draw.polygon(points, fill=color)
                draw.line(
                    points + [points[0]],
                    fill=outline,
                    width=max(2, round(1.25 * ANTIALIAS)),
                    joint="curve",
                )
                mark_x = x + radius * (
                    transform[0][0] * local_mark[0] + transform[0][1] * local_mark[1]
                )
                mark_y = y + radius * (
                    transform[1][0] * local_mark[0] + transform[1][1] * local_mark[1]
                )
                mark_radius = max(2.2 * ANTIALIAS, radius * 0.075)
                draw.ellipse(
                    (mark_x - mark_radius, mark_y - mark_radius,
                     mark_x + mark_radius, mark_y + mark_radius),
                    fill=background,
                    outline=outline,
                    width=max(1, ANTIALIAS),
                )

    image = image.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", lossless=True, method=6)
    return buffer.getvalue()


def _phase_legend(record: dict[str, Any]) -> str:
    items = []
    for residue in record["phase_residues"]:
        items.append(
            "<li>"
            f"<span class=\"swatch\" style=\"--swatch: {escape(residue['color'])}\"></span>"
            f"<span>colour {residue['index']} · phase {escape(residue['phase'])}</span>"
            "</li>"
        )
    return "\n".join(items)


def _phase_profile(record: dict[str, Any]) -> str:
    if not record["phase_profile"]:
        return "<p class=\"phase-trivial\">All operation cosets have phase 0.</p>"
    rows = []
    for profile in record["phase_profile"]:
        rows.append(
            "<li>"
            f"<span>{escape(profile['operation'])}</span>"
            f"<span>{escape(', '.join(profile['phases']))}</span>"
            "</li>"
        )
    return "<ul class=\"phase-profile\">" + "\n".join(rows) + "</ul>"


def _geometric_operations_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    rows = []
    for operation in record["geometric_operations"]:
        power = int(operation["power"])
        generator = escape(operation["generator"])
        generator_html = generator if power == 1 else f"{generator}<sup>{power}</sup>"
        rows.append(
            "<tr class=\"geometric-operation-row\">"
            f"<td><span class=\"generator-key\">{generator_html}</span>"
            f"<span>{escape(operation['operation'])}</span></td>"
            f"<td>{escape(operation['time_shift'])}</td>"
            "</tr>"
        )
    rows_html = "\n".join(rows)
    return f"""
              <section class="geometric-operations" aria-labelledby="{group_id}-geometric-operations-title">
                <h4 id="{group_id}-geometric-operations-title">Geometric generators and their powers</h4>
                <p>A, B, … form a minimal set for one repeating cell; superscripts mark powers. Full-cell translations and products of different generators are omitted.</p>
                <table data-geometric-operations="{group_id}">
                  <caption class="visually-hidden">Spatial operations and time shifts for {group_id}</caption>
                  <thead><tr><th scope="col">Geometric operation</th><th scope="col">Time shift</th></tr></thead>
                  <tbody>{rows_html}</tbody>
                </table>
              </section>"""


def _book_link(reference: dict[str, Any], css_class: str) -> str:
    excerpt = BOOK_EXCERPTS[reference["excerpt_key"]]
    viewer_url = "book-excerpt.html?" + urlencode(
        {
            "image": excerpt["image"],
            "title": excerpt["title"],
            "context": excerpt["context"],
            "alt": excerpt["alt"],
            "source": reference["url"],
        }
    )
    return (
        f'<a class="{css_class}" href="{escape(viewer_url)}" '
        f'data-printed-page="{reference["printed_page"]}" '
        f'data-pdf-page="{reference["pdf_page"]}" '
        f'data-book-excerpt="{escape(excerpt["key"])}" '
        f'data-book-image="{escape(excerpt["image"])}" '
        f'data-book-title="{escape(excerpt["title"])}" '
        f'data-book-context="{escape(excerpt["context"])}" '
        f'data-book-alt="{escape(excerpt["alt"])}" '
        f'data-book-source="{escape(reference["url"])}" '
        f'target="{BOOK_EXCERPT_TARGET}">'
        f'{escape(reference["label"])} · printed p. {reference["printed_page"]} '
        f'(attached PDF p. {reference["pdf_page"]}) · view annotated excerpt in the excerpt tab</a>'
    )


def _book_audit_html(record: dict[str, Any]) -> str:
    audit = record["book_audit"]
    primary = next(
        reference for reference in audit["references"] if reference["role"] == "primary"
    )
    supporting = [
        reference for reference in audit["references"] if reference["role"] != "primary"
    ]
    supporting_html = ""
    if supporting:
        links = "\n".join(
            f"<li>{_book_link(reference, 'book-cross-reference')}</li>"
            for reference in supporting
        )
        supporting_html = f'<ul class="book-reference-list">{links}</ul>'

    chain_html = ""
    if audit["prime_chain"]:
        steps = []
        for step in audit["prime_chain"]:
            step_reference = {
                "label": f"Table on p. {step['printed_page']}",
                "url": step["url"],
                "printed_page": step["printed_page"],
                "pdf_page": step["pdf_page"],
                "excerpt_key": step["excerpt_key"],
            }
            steps.append(
                "<li>"
                f"<span>{orbifold_html(step['notation'])} · index {step['index']}</span>"
                f"{_book_link(step_reference, 'book-chain-link')}"
                "</li>"
            )
        chain_html = (
            '<div class="prime-chain"><h3>Prime-index cross-check</h3><ol>'
            + "\n".join(steps)
            + "</ol></div>"
        )

    independent_html = ""
    if audit.get("independent_reference"):
        reference = audit["independent_reference"]
        independent_html = (
            '<p class="independent-reference"><strong>Independent check.</strong> '
            f'<a href="{escape(reference["url"])}">{escape(reference["label"])}</a>.</p>'
        )

    return f"""
              <aside class="book-audit book-audit--{escape(audit['status'])}">
                <p class="book-audit-label">Book audit · {escape(audit['status_label'])}</p>
                <p>{orbifold_html(audit['summary'])}</p>
                <p class="book-primary-reference">{_book_link(primary, 'book-page-link')}</p>
                {supporting_html}
                {chain_html}
                {independent_html}
              </aside>"""


def _film_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    return f"""
              <figure class="clockwork-film" data-clockwork-player data-group-id="{group_id}">
                <div class="clockwork-stage" data-film-stage data-state="loading">
                  <canvas class="clockwork-canvas" id="{group_id}-film" width="1" height="1" role="img" aria-describedby="{group_id}-film-caption">JavaScript is needed for this film; the static coloured plate remains available below.</canvas>
                  <p class="film-status" data-film-status>Loading local film data…</p>
                </div>
                <div class="animation-controls" data-film-controls data-state="loading">
                  <button class="animation-toggle" type="button" data-film-toggle aria-controls="{group_id}-film" aria-pressed="false" disabled>
                    <span class="animation-icon" aria-hidden="true">▶</span>
                    <span data-film-toggle-label>Play</span>
                  </button>
                  <label class="visually-hidden" for="{group_id}-phase">Phase for colour action {group_id}</label>
                  <input class="phase-slider" id="{group_id}-phase" data-film-slider type="range" min="0" max="1" step="0.001" value="0" aria-valuetext="phase 0.000 of one period" disabled>
                  <output class="phase-output" data-film-output for="{group_id}-phase">0.000</output>
                </div>
                <figcaption id="{group_id}-film-caption">Clockwork film · fixed phase ruler, smooth hand · paused by default</figcaption>
              </figure>"""


def _signature_source_label(record: dict[str, Any]) -> str:
    """Say exactly how the visible short signature is sourced."""

    return f"Short colour signature · {record['signature_evidence']['label']}"


def _notation_crosswalk_html(record: dict[str, Any]) -> str:
    """Keep the short-signature and full colour-type numerals distinct."""

    order = record["clock_order"]
    parent = record["parent"]["orbifold"]
    kernel = record["kernel"]["orbifold"]
    short_signature = superscript_html(record["book_color_signature"])
    colour_type = color_type_html(parent, kernel, order)
    evidence = record["signature_evidence"]
    signature_source = evidence["summary"]
    if order == 2:
        type_term = "Book colour type"
        type_explanation = (
            "Twofold is understood, so the book omits an exponent 2; the group "
            "after the slash is K, the all-colours kernel."
        )
    else:
        type_term = (
            "Book-style colour type" if order in (4, 6) else "Book colour type"
        )
        type_explanation = (
            f"The exponent {order} counts colours; the group after the slash is K, "
            "the all-colours kernel."
        )
    lossy_note = (
        " For three or more colours this order-only summary can lose permutation "
        "information; the full colour type disambiguates it."
        if order >= 3
        else ""
    )
    return f"""
              <dl class="notation-crosswalk" aria-label="Notation crosswalk">
                <div>
                  <dt>Short colour signature</dt>
                  <dd><span class="notation-mark book-color-signature">{short_signature}</span><span class="notation-explanation">Superscripts are permutation orders. A reduced clock phase a/b induces permutation order b.{escape(lossy_note)} {orbifold_html(signature_source)}</span></dd>
                </div>
                <div>
                  <dt>{escape(type_term)}</dt>
                  <dd><span class="notation-mark color-type">{colour_type}</span><span class="notation-explanation">{escape(type_explanation)}</span></dd>
                </div>
              </dl>"""


def _entry_html(
    record: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    display_ordinal: int,
) -> str:
    group_id = escape(record["id"])
    order = record["clock_order"]
    parent = record["parent"]
    kernel = record["kernel"]
    short_signature = record["book_color_signature"]
    short_signature_html = superscript_html(short_signature)
    type_html = color_type_html(parent["orbifold"], kernel["orbifold"], order)
    signature_source_label = _signature_source_label(record)
    mate_note = ""
    if record["inverse_clock_mate"]:
        mate = by_id[record["inverse_clock_mate"]]
        mate_note = (
            "<aside class=\"orientation-note\">"
            "<strong>Clock orientation.</strong> This has the same traditional colour group as "
            f"<a href=\"#{escape(mate['id'])}\">{escape(mate['id'])}</a>, "
            "but traverses the cyclic palette in the opposite "
            "time order.</aside>"
        )
    entry = f"""
      <li class="correspondence-item">
        <section class="correspondence-entry" id="{group_id}" aria-labelledby="{group_id}-title" data-clockwork-tabpanel data-clock-order="{order}">
          <header class="entry-header">
            <p class="entry-number">{display_ordinal:02d} / {DISPLAYED_GROUP_COUNT}</p>
            <div>
              <p class="entry-kicker">{escape(signature_source_label)}</p>
              <h3 id="{group_id}-title"><span class="book-color-signature" aria-label="{escape(signature_source_label)} {escape(short_signature)}">{short_signature_html}</span> <span class="group-id">{group_id}</span></h3>
              <p class="entry-identity">Base orbifold {orbifold_html(parent['orbifold'])} · regular colour action C<sub>{order}</sub></p>
            </div>
            <div class="entry-badges" aria-label="Correspondence summary">
              <span>C<sub>{order}</sub></span>
              <span class="color-type">{type_html}</span>
            </div>
          </header>

          <div class="entry-grid">
            <div class="entry-visuals">
              {_film_html(record)}
              <figure class="colour-plate">
                <img src="{escape(record['image'])}" width="{IMAGE_WIDTH}" height="{IMAGE_HEIGHT}" loading="lazy" decoding="async" alt="{escape(record['image_alt'])}">
                <figcaption>
                  <span>Static perfect-colouring plate</span>
                  <ol class="colour-key" aria-label="Colour and phase key">
                    {_phase_legend(record)}
                  </ol>
                </figcaption>
              </figure>
            </div>

            <div class="entry-copy">
              <p class="pair-label">Conway–Burgiel–Goodman-Strauss colour type</p>
              <p class="orbifold-pair">{type_html}</p>
              <dl class="group-data">
                <div><dt>Projected group G</dt><dd>{orbifold_html(parent['orbifold'])}</dd></div>
                <div><dt>Colour-fixing subgroup K</dt><dd>{orbifold_html(kernel['orbifold'])}</dd></div>
                <div><dt>Regular quotient</dt><dd>G/K ≅ C<sub>{order}</sub>; [G:K] = {order}</dd></div>
              </dl>
              {_geometric_operations_html(record)}
              {_notation_crosswalk_html(record)}
              <p class="phase-description">{orbifold_html(record['clockwork_description'])}</p>
              <p class="coloring-description">{orbifold_html(record['coloring_description'])}</p>
              {_book_audit_html(record)}
              {mate_note}
              <p class="catalog-action"><a href="{escape(record['catalog_url'])}" aria-label="Open {group_id} in the forward catalog">forward catalog · {group_id} ↗</a></p>
            </div>
          </div>
        </section>
      </li>"""
    return "\n".join(line.rstrip() for line in entry.splitlines())


def _tab_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    signature = record["book_color_signature"]
    return (
        f'<a class="clockwork-tab" id="tab-{group_id}" href="#{group_id}" '
        f'data-clockwork-tab data-panel-id="{group_id}" '
        f'aria-label="{escape(signature)}, colour action {group_id}">'
        f'<span class="tab-signature">{superscript_html(signature)}</span>'
        f'<span class="tab-meta">{group_id} · C<sub>{record["clock_order"]}</sub></span>'
        "</a>"
    )


def _order_census_html(rows: list[dict[str, Any]]) -> str:
    counts = Counter(row["clock_order"] for row in rows)
    parts = [
        f'C<sub>{order}</sub>: {counts[order]}'
        for order in sorted(counts)
    ]
    return " · ".join(parts)


def _trivial_product_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    orbifold = orbifold_html(record["parent"]["orbifold"])
    return (
        f'<aside class="trivial-product" id="{group_id}" data-trivial-product '
        'aria-label="Trivial time group">'
        "<p><strong>Trivial time group · C<sub>1</sub>.</strong> "
        f"The inherited one-colour lift {orbifold} ({group_id}) has κ = 0 and K = G; "
        "it remains in the 68-record audit data but is not included in the tabs above.</p>"
        "</aside>"
    )


def _directory_group_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    signature = superscript_html(record["book_color_signature"])
    swatches = "".join(
        f'<span style="--directory-colour: {escape(residue["color"])}"></span>'
        for residue in record["phase_residues"]
    )
    return (
        f'<a class="directory-group" href="#{group_id}" data-directory-group="{group_id}" '
        f'aria-label="{escape(record["book_color_signature"])}; '
        f'{record["clock_order"]} colours; open {group_id}">'
        f'<span class="directory-signature book-color-signature">{signature}</span>'
        f'<span class="directory-palette" aria-hidden="true">{swatches}</span>'
        f'<span class="directory-group-id">{group_id}</span>'
        '</a>'
    )


def _directory_family_html(base: str, rows: list[dict[str, Any]]) -> str:
    orbifold = orbifold_html(ORBIFOLD_BY_BASE[base])
    cards = "\n".join(_directory_group_html(record) for record in rows)
    return f"""        <section class="directory-family" aria-labelledby="directory-{escape(base)}-title">
          <h2 id="directory-{escape(base)}-title"><a class="directory-family-link" href="#wallpaper-{escape(base)}">{orbifold}</a><span>{len(rows)} forward groups</span></h2>
          <div class="directory-groups">{cards}</div>
        </section>"""


def _family_html(
    base: str,
    rows: list[dict[str, Any]],
    trivial_record: dict[str, Any],
    family_index: int,
    by_id: dict[str, dict[str, Any]],
    display_ordinals: dict[str, int],
) -> str:
    orbifold = ORBIFOLD_BY_BASE[base]
    summary, note = WALLPAPER_SUMMARIES[base]
    lift_word = "lift" if len(rows) == 1 else "lifts"
    tabs = "\n".join(_tab_html(row) for row in rows)
    entries = "\n".join(
        _entry_html(row, by_id, display_ordinals[row["id"]])
        for row in rows
    )
    family_class = "wallpaper-family" + (" is-empty" if not rows else "")
    census = (
        f"Nontrivial orders · {_order_census_html(rows)}"
        if rows
        else "Nontrivial orders · none"
    )
    if rows:
        contents = f"""
      <div class="clockwork-tabs" data-clockwork-tabs>
        <nav class="clockwork-tabbar" data-clockwork-tablist aria-label="Nontrivial colour actions over orbifold {escape(orbifold)}">
          {tabs}
        </nav>
        <ol class="correspondence-list">
{entries}
        </ol>
      </div>"""
    else:
        contents = """
      <div class="family-empty" role="note">
        <p><strong>No nontrivial forward lift occurs.</strong> After removing the inherited one-colour product, this orbifold signature contributes no entry to the 51-group atlas.</p>
      </div>"""
    return f"""
    <section class="{family_class}" id="wallpaper-{escape(base)}" aria-labelledby="wallpaper-{escape(base)}-title" data-wallpaper-family>
      <header class="family-header">
        <p class="section-number">Orbifold family {family_index:02d} / 17</p>
        <h2 id="wallpaper-{escape(base)}-title"><span class="family-orbifold">{orbifold_html(orbifold)}</span> <span class="family-count">{len(rows)} nontrivial {lift_word}</span></h2>
        <p class="family-summary">{orbifold_html(summary)}</p>
        <p class="family-note"><strong>Forward note.</strong> {orbifold_html(note)}</p>
        <p class="family-census">{census}</p>
      </header>
{contents}
      {_trivial_product_html(trivial_record)}
    </section>"""


def page_html(payload: dict[str, Any]) -> str:
    groups = payload["groups"]
    by_id = {group["id"]: group for group in groups}
    displayed_groups = [group for group in groups if group["clock_order"] > 1]
    trivial_groups = [group for group in groups if group["clock_order"] == 1]
    if len(displayed_groups) != DISPLAYED_GROUP_COUNT:
        raise ValueError(f"expected {DISPLAYED_GROUP_COUNT} nontrivial display groups")
    if len(trivial_groups) != OMITTED_TRIVIAL_COUNT:
        raise ValueError(f"expected {OMITTED_TRIVIAL_COUNT} trivial product groups")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in displayed_groups:
        grouped[group["parent"]["hm"]].append(group)
    trivial_by_base = {group["parent"]["hm"]: group for group in trivial_groups}
    if set(trivial_by_base) != set(BASE_ORDER):
        raise ValueError("expected one trivial product for every wallpaper group")
    ordered_display_groups = [
        group
        for base in BASE_ORDER
        for group in grouped[base]
    ]
    display_ordinals = {
        group["id"]: ordinal
        for ordinal, group in enumerate(ordered_display_groups, 1)
    }
    families = "\n".join(
        _family_html(
            base,
            grouped[base],
            trivial_by_base[base],
            index,
            by_id,
            display_ordinals,
        )
        for index, base in enumerate(BASE_ORDER, 1)
    )
    directory = "\n".join(
        _directory_family_html(base, grouped[base])
        for base in BASE_ORDER
        if grouped[base]
    )
    if sum(bool(grouped[base]) for base in BASE_ORDER) != 14:
        raise ValueError("expected 14 projected orbifold families with nontrivial actions")
    digest = payload["meta"]["source_catalog_sha256"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="An audited atlas of 51 nontrivial forward clockwork groups and their regular cyclic plane colourings, organized by Euclidean orbifold signature.">
  <meta name="theme-color" content="#ffffff">
  <title>Clockwork/coloring correspondence</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="site-controls-v2.css">
  <link rel="stylesheet" href="{CORRESPONDENCE_STYLE_SRC}">
</head>
<body>
  <a class="skip-link" href="#correspondences">Skip to correspondences</a>

  <header class="site-header">
    <div class="header-inner">
      <a class="site-name" href="./">Spacetime-group visualizations</a>
      <nav aria-label="Project links">
        <a href="./">Gallery</a>
        <a href="future-directions.html">Colours</a>
        <a href="clockwork-coloring-correspondence.html" aria-current="page">Correspondence</a>
        <a href="docs/orbifold_notation.html">Notation</a>
        <a href="data/clockwork-coloring-correspondence.json">Data</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>

  <main class="correspondence-page">
    <nav class="directory" aria-labelledby="page-title">
      <p class="section-number">51 nontrivial forward groups · 14 projected orbifold families</p>
      <h1 id="page-title">Clockwork/coloring correspondence</h1>
      <p class="directory-legend">Each block is the displayed phase palette. Raised numbers in the signature give colour-permutation orders, not time shifts.</p>
      <div class="directory-families">
        {directory}
      </div>
    </nav>

    <div class="correspondence-atlas" id="correspondences">
{families}
    </div>

    <section class="provenance" aria-labelledby="provenance-title">
      <p class="section-number">Audit trail</p>
      <h2 id="provenance-title">Data and reproduction</h2>
      <p>
        The <a href="data/clockwork-coloring-correspondence.json">68-record JSON</a> and all 68
        lossless WebP plates retain the complete audited source, including the 17 omitted products.
        This HTML displays its 51 nontrivial rows; {len(BOOK_EXCERPTS)} annotated book excerpts and the local paused-film
        controller are generated or tracked in this repository. The data and page come from the
        <a href="scripts/generate_clockwork_coloring_correspondence.py">correspondence generator</a>;
        the <a href="scripts/tos_book_excerpt_specs.py">excerpt coordinates</a> and
        <a href="scripts/generate_tos_book_excerpts.py">crop renderer</a> are checked in separately.
        The audit also checks the <a href="{BOOK_ERRATA_URL}">authors' published errata</a>.
        The read-only source snapshot has SHA-256 <code>{escape(digest)}</code>. Each tab links to
        its exact entry in the external forward catalog; no runtime data or code is loaded from
        that site. Film canvases read only the checked-in correspondence JSON.
      </p>
      <pre><code>python3 scripts/generate_clockwork_coloring_correspondence.py
python3 scripts/generate_clockwork_coloring_correspondence.py --check
python3 scripts/generate_tos_book_excerpts.py --source-pdf "/path/to/The Symmetries of Things.pdf"
python3 scripts/generate_tos_book_excerpts.py --source-pdf "/path/to/The Symmetries of Things.pdf" --check</code></pre>
    </section>

    <footer>
      <p><a href="./">Visualization gallery</a> · <a href="future-directions.html">Colour census</a> · <a href="README.md">README</a> · <a href="https://github.com/yaroslavvb/animated-groups">GitHub source</a></p>
    </footer>
  </main>

  <script type="module" src="{CORRESPONDENCE_SCRIPT_SRC}"></script>
</body>
</html>
"""


def data_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def expected_outputs(payload: dict[str, Any]) -> tuple[dict[Path, str], dict[Path, bytes]]:
    text_outputs = {
        DATA: data_text(payload),
        PAGE: page_html(payload),
    }
    binary_outputs = {
        IMAGE_DIR / f"{group['id']}.webp": render_plate(group)
        for group in payload["groups"]
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
        stale.extend(path for path in IMAGE_DIR.glob("*.webp") if path not in expected_images)
    return stale


def write_outputs(payload: dict[str, Any]) -> None:
    text_outputs, binary_outputs = expected_outputs(payload)
    for path, text in text_outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for path, data in binary_outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-catalog",
        type=Path,
        help="read-only path to the pinned 275-group source catalog",
    )
    parser.add_argument(
        "--refresh-derived-data",
        action="store_true",
        help="refresh descriptions and book evidence in the checked-in extract",
    )
    parser.add_argument("--check", action="store_true", help="fail if generated outputs are stale")
    args = parser.parse_args(argv)

    if args.source_catalog and args.refresh_derived_data:
        parser.error("choose either --source-catalog or --refresh-derived-data")

    if args.source_catalog:
        payload = build_payload(args.source_catalog)
        if args.check and DATA.exists():
            tracked = json.loads(DATA.read_text(encoding="utf-8"))
            if tracked != payload:
                print(f"stale: {DATA.relative_to(ROOT)}", file=sys.stderr)
                return 1
    else:
        if not DATA.exists():
            parser.error("correspondence data is missing; provide --source-catalog to create it")
        payload = json.loads(DATA.read_text(encoding="utf-8"))
        if args.refresh_derived_data:
            payload = refresh_derived_payload(payload)
            DATA.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        validate_payload(payload)

    if args.check:
        stale = check_outputs(payload)
        if stale:
            for path in stale:
                print(f"stale: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("clockwork/colouring correspondence: tracked outputs are current")
        return 0

    write_outputs(payload)
    print("wrote 68 correspondence records, 51 displayed rows, and static colour plates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
