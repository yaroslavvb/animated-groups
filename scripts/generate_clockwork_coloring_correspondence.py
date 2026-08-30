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
    python3 scripts/generate_clockwork_coloring_correspondence.py --text-only
    python3 scripts/generate_clockwork_coloring_correspondence.py \
        --source-catalog /path/to/catalog.json
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from functools import cache
from html import escape
import hashlib
import io
from itertools import combinations
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable
from urllib.parse import urlencode

from PIL import Image, ImageDraw

from chaim_short_signatures import TWO_FOLD_SHORT_SIGNATURE_BY_TYPE
from colour_generator_actions import (
    GENERATOR_GEOMETRY,
    THREE_COLOUR_ACTION_CODES,
    generator_colour_actions,
    group_presentation,
    permutation_group,
    presentation_relations_hold,
)
from tos_book_excerpt_specs import BOOK_EXCERPTS
from wallpaper_affine_generators import affine_generators_for, generator_visualization


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "color-forward-manifest.json"
DATA = ROOT / "data" / "clockwork-coloring-correspondence.json"
PAGE = ROOT / "clockwork-coloring-correspondence.html"
IMAGE_DIR = ROOT / "output" / "clockwork-colorings"
SPACE_GROUP_DATA = ROOT / "data" / "space-group-correspondence.json"
CORRESPONDENCE_STYLE_SRC = "clockwork-coloring-correspondence.css?v=crystallographic-symbol-index"
CORRESPONDENCE_SCRIPT_SRC = "clockwork-coloring-correspondence.js?v=deep-link-canvas-fix"
BOOK_EXCERPT_VIEWER_VERSION = "whole-tables"
COLOR_PATTERN_DATA = ROOT / "data" / "color-pattern-catalog.json"

SOURCE_SHA256 = "040eebe747815557014c1dbf1d4265d204aaae35c110595f2a15b94ee7f68ca0"
CATALOG_ROOT = "https://yaroslavvb.github.io/animated-groups-fable/catalog.html?time=forward"
CATALOG_DATA_URL = "https://yaroslavvb.github.io/animated-groups-fable/data/catalog.json"
BOOK_RECORD_URL = "https://books.google.com/books?id=EtQCk0TNafsC"
BOOK_PAGE_URL = BOOK_RECORD_URL + "&pg=PA{page}"
BOOK_EXCERPT_TARGET = "clockwork-book-excerpt"
BOOK_ERRATA_URL = "https://www.mit.edu/~hlb/Symmetries_of_Things/SoTerrors.html"
FARRIS_URL = "https://archive.bridgesmathart.org/2017/bridges2017-131.pdf#page=6"
IUCR_DIAGRAM_SYMBOLS_URL = (
    "https://journals.iucr.org/j/issues/2010/05/02/kk5061/kk5061fig12.html"
)
UCL_P31C_DIAGRAM_URL = "http://img.chem.ucl.ac.uk/sgp/large/159az1.htm"

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

# The canonical affine presentations use the coordinates in
# ``wallpaper_affine_generators.py``.  Static plates use a record-specific
# colour-fixing lattice instead.  For every nontrivial plate this audited map
# sends a canonical point x to render-lattice coordinates q = Lx + d.  Keeping
# the signed conjugacy explicit is important: an order-only search can silently
# exchange the two directed rotations and consequently choose the complementary
# clock shift while leaving the marker looking plausible.
_R3 = 1 / math.sqrt(3)
CANONICAL_TO_RENDER_CONJUGACY_BY_ID: dict[
    str, tuple[list[list[float]], tuple[float, float]]
] = {}


def _add_plate_conjugacy(
    group_ids: str,
    linear: list[list[float]],
    offset: tuple[float, float] = (0, 0),
) -> None:
    for group_id in group_ids.split():
        CANONICAL_TO_RENDER_CONJUGACY_BY_ID[group_id] = (linear, offset)


_add_plate_conjugacy("g6", [[1, -1], [0, -1]])
_add_plate_conjugacy("g7", [[0, 1], [-1 / 2, 0]])
_add_plate_conjugacy("g9", [[-1, -1 / 2], [-1, 1 / 2]])
_add_plate_conjugacy("g55 g60", [[1, 0], [0, 1]])
_add_plate_conjugacy("g57 g61 g62", [[1, 0], [0, -1]])
_add_plate_conjugacy("g59 g63", [[0, 1], [-1, 0]], (-1 / 4, 1 / 4))
_add_plate_conjugacy("g64", [[1, 0], [0, -1 / 2]])
_add_plate_conjugacy("g65", [[0, 1], [1 / 2, 0]], (0, -1 / 4))
_add_plate_conjugacy("g66 g67", [[0, -1], [1 / 2, 0]])
_add_plate_conjugacy("g69 g70 g71 g72", [[1, 0], [0, 1]])
_add_plate_conjugacy("g73", [[0, 1], [1, 0]], (-1 / 4, -1 / 4))
_add_plate_conjugacy("g74", [[1 / 2, 0], [0, 1 / 2]])
_add_plate_conjugacy("g75", [[0, 1 / 2], [1 / 2, 0]], (0, -1 / 8))
_add_plate_conjugacy("g95 g96 g97", [[0, -1], [-1, 0]])
_add_plate_conjugacy("g98", [[-1 / 2, 1 / 2], [1 / 2, 1 / 2]])
_add_plate_conjugacy("g99", [[1 / 2, 1 / 2], [-1 / 2, 1 / 2]], (-1 / 4, 0))
_add_plate_conjugacy("g129 g130", [[-1, 0], [0, -1]])
_add_plate_conjugacy("g131", [[-1, 1], [1, 1]])
_add_plate_conjugacy("g133 g134 g135", [[-1, -1], [1, -1]])
_add_plate_conjugacy("g136 g138", [[-1 / 2, 1 / 2], [1 / 2, 1 / 2]])
_add_plate_conjugacy("g137", [[-1, 0], [0, -1]], (0, 1 / 4))
_add_plate_conjugacy("g139", [[1, 0], [0, 1]], (0, -1 / 4))
_add_plate_conjugacy("g225 g226", [[-1, _R3], [-1, -_R3]])
_add_plate_conjugacy("g227", [[2 / 3, 0], [1 / 3, _R3]], (-1 / 3, 0))
_add_plate_conjugacy("g231", [[-_R3, -1], [_R3, -1]])
_add_plate_conjugacy("g233", [[-1, -_R3], [-1, _R3]])
_add_plate_conjugacy("g234 g235", [[-2 / 3, 0], [-1 / 3, _R3]])
_add_plate_conjugacy("g244 g245 g246 g247 g248", [[-1, _R3], [-1, -_R3]])
_add_plate_conjugacy("g269 g270 g271", [[-1, -_R3], [-1, _R3]])

BASE_ORDER = (
    "p1", "p2", "pm", "pg", "cm", "pmm", "pmg", "pgg", "cmm",
    "p4", "p4m", "p4g", "p3", "p3m1", "p31m", "p6", "p6m",
)

PLANE_GROUP_NUMBER_BY_HM = {
    "p1": 1,
    "p2": 2,
    "pm": 3,
    "pg": 4,
    "cm": 5,
    "pmm": 6,
    "pmg": 7,
    "pgg": 8,
    "cmm": 9,
    "p4": 10,
    "p4m": 11,
    "p4g": 12,
    "p3": 13,
    "p3m1": 14,
    "p31m": 15,
    "p6": 16,
    "p6m": 17,
}
PLANE_GROUP_FULL_HM = {
    "p1": "p1",
    "p2": "p2",
    "pm": "p1m1",
    "pg": "p1g1",
    "cm": "c1m1",
    "pmm": "p2mm",
    "pmg": "p2mg",
    "pgg": "p2gg",
    "cmm": "c2mm",
    "p4": "p4",
    "p4m": "p4mm",
    "p4g": "p4gm",
    "p3": "p3",
    "p3m1": "p3m1",
    "p31m": "p31m",
    "p6": "p6",
    "p6m": "p6mm",
}
IUCR_PLANE_GROUP_URL = (
    "https://it.iucr.org/Ac/ch2o2v0001/sgtable2o2o{number:03d}/"
)
HIERARCHY_CHIRALITY_URL = (
    "https://yaroslavvb.github.io/animated-groups-fable/hierarchy.html#splits"
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
    "p1": "A torus; translations only.",
    "p2": "A sphere with four order-2 cone points.",
    "pm": "Two mirror-boundary components.",
    "pg": "Two crosscaps; glide reflections but no mirror boundary.",
    "cm": "One mirror boundary and one crosscap.",
    "pmm": "A mirror quadrilateral with four order-2 corners.",
    "pmg": "Two order-2 cone points and one mirror-boundary component.",
    "pgg": "Two order-2 cone points and one crosscap.",
    "cmm": "One order-2 cone point and a mirror boundary with two order-2 corners.",
    "p4": "A sphere with cone points of orders 4, 4, and 2.",
    "p4m": "A mirror triangle with corner orders 4, 4, and 2.",
    "p4g": "One order-4 cone point and a mirror boundary with one order-2 corner.",
    "p3": "A sphere with three order-3 cone points.",
    "p3m1": "A mirror triangle with three order-3 corners.",
    "p31m": "One order-3 cone point and a mirror boundary with one order-3 corner.",
    "p6": "A sphere with cone points of orders 6, 3, and 2.",
    "p6m": "A mirror triangle with corner orders 6, 3, and 2.",
}

# Conway--Burgiel--Goodman-Strauss fibrifold names, transcribed from
# The Symmetries of Things, Chapter 25, Tables 25.1--25.17 (pp. 370--374).
# The chosen alias is always the one whose horizontal plane group is this
# record's projected wallpaper group.  Parentheses are part of the notation.
FIBRIFOLD_BY_ID = {
    "g1": "(◦)",
    "g5": "(2₀2₀2₀2₀)", "g6": "(2₁2₁2₁2₁)", "g7": "(2₀2₀2₁2₁)",
    "g8": "(∗·×)", "g9": "(∗:×)", "g10": "(∗·∗·)", "g11": "(××₀)",
    "g54": "(∗·2·2·2·2)", "g55": "(∗:2:2:2:2)",
    "g56": "(2₀2₀∗·)", "g57": "(2₀2₀∗:)",
    "g58": "(2₀2₀×₀)", "g59": "(2₀2₀×₁)",
    "g60": "(∗·2:2·2:2)", "g61": "(2₁2₁∗:)",
    "g62": "(2₁2₁∗·)", "g63": "(2₁2₁×)",
    "g64": "(∗·2·2·2:2)", "g65": "(∗·2:2:2:2)",
    "g66": "(2₀2₁∗·)", "g67": "(2₀2₁∗:)",
    "g68": "(2₀∗·2·2)", "g69": "(2₀∗:2:2)",
    "g70": "(2₁∗·2:2)", "g71": "(2₁∗·2·2)",
    "g72": "(2₁∗:2:2)", "g73": "(2₀∗·2:2)",
    "g74": "(∗·2·2:2:2)", "g75": "(2₀2₁×)",
    "g94": "(4₀4₀2₀)", "g95": "(4₂4₂2₀)",
    "g96": "(4₁4₁2₁)", "g97": "(4₁4₁2₁)",
    "g98": "(4₂4₀2₁)", "g99": "(4₃4₁2₀)",
    "g128": "(∗·4·4·2)", "g129": "(∗·4:4·2)",
    "g130": "(∗:4·4:2)", "g131": "(∗:4:4:2)",
    "g132": "(4₀∗·2)", "g133": "(4₂∗:2)",
    "g134": "(4₂∗·2)", "g135": "(4₀∗:2)",
    "g136": "(∗·4·4:2)", "g137": "(4₁∗·2)",
    "g138": "(∗·4:4:2)", "g139": "(4₁∗:2)",
    "g224": "(3₀3₀3₀)", "g225": "(3₁3₁3₁)",
    "g226": "(3₁3₁3₁)", "g227": "(3₀3₁3₂)",
    "g230": "(∗·3·3·3)", "g231": "(∗:3:3:3)",
    "g232": "(3₀∗·3)", "g233": "(3₀∗:3)",
    "g234": "(3₁∗·3)", "g235": "(3₁∗:3)",
    "g243": "(6₀3₀2₀)", "g244": "(6₂3₂2₀)",
    "g245": "(6₂3₂2₀)", "g246": "(6₃3₀2₁)",
    "g247": "(6₁3₁2₁)", "g248": "(6₁3₁2₁)",
    "g268": "(∗·6·3·2)", "g269": "(∗·6:3:2)",
    "g270": "(∗:6:3:2)", "g271": "(∗:6·3·2)",
}

# The book classifies these enantiomorphic space-group pairs with one
# unoriented fibrifold name.  The Hermann--Mauguin row selects the handed
# member; the Conway symbol should not be embellished with an invented sign.
FIBRIFOLD_ENANTIOMORPHIC_IDS = frozenset({
    "g96", "g97", "g225", "g226", "g244", "g245", "g247", "g248",
})

TERM_HELP = {
    "Book type audit": (
        "The book page or table used to audit the parent/kernel colour type; the "
        "clickable short form in the heading uses its own signature-cell crop."
    ),
    "Catalog instance": (
        "The matching animated example in the forward-time catalog; gN is this "
        "project's record identifier."
    ),
    "Colour-fixing plane-group type K": (
        "The normal subgroup K ≤ G whose operations leave every colour class "
        "unchanged: the kernel of G → C_N."
    ),
    "Conway fibrifold notation": (
        "Conway's decorated orbifold name for this lift. It records the horizontal "
        "base orbifold and the fractional height translations coupled to its "
        "generators; this page uses the alias for the chosen height direction."
    ),
    "Height-lift space-group type": (
        "Treat colour phase as a periodic height z. A planar operation with phase "
        "shift τ lifts to (x, y, z) ↦ (M(x, y) + v, z + τ), producing this "
        "three-dimensional space-group type."
    ),
    "Complementary forward skips": (
        "The paired entry replaces every +k/N period skip by +(N−k)/N modulo "
        "one period. Both entries preserve the same fixed forward time direction."
    ),
}

# Canonical first short color signature printed for each relevant type in
# Table 11.1.  The raised number is the order of the induced permutation on
# colors (p. 136), not a clock-screw numerator.  Several table rows give
# equivalent alternatives; choosing the first keeps each tab label stable.
BOOK_TWO_FOLD_SIGNATURE_BY_TYPE = TWO_FOLD_SHORT_SIGNATURE_BY_TYPE

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

# The two rows in each pair use complementary nonnegative powers of the fixed
# forward clock generator. A traditional colouring identifies them by a global
# colour relabelling even though the clockwork catalog keeps time fixed.
COMPLEMENTARY_SKIP_MATE = {
    "g96": "g97", "g97": "g96",
    "g225": "g226", "g226": "g225",
    "g244": "g245", "g245": "g244",
    "g247": "g248", "g248": "g247",
}

# These are the displayed rows whose Chaim colour signature has a second
# preimage.  Keep this name separate from the fibrifold map: both unoriented
# notations happen to have the same four fibres, but they classify different
# objects.
COLOUR_SIGNATURE_COLLISION_IDS = frozenset(COMPLEMENTARY_SKIP_MATE)

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

# The book stops at primefold colourings.  These seven action representatives
# are the regular C4/C6 extensions used by the checked local patterns catalog.
# A dot separates disjoint cycles, so ``AB.CD`` means (AB)(CD).
COMPOSITE_COLOUR_ACTION_CODES = {
    "g75": ("1", "AB.CD", "ACBD"),
    "g96": ("ABDC", "ABDC", "AD.BC"),
    "g97": ("ABDC", "ABDC", "AD.BC"),
    "g99": ("ACBD", "ADBC", "1"),
    "g137": ("ACBD", "1"),
    "g139": ("ACBD", "AB.CD"),
    "g235": ("ABD.CEF", "AC.BE.DF"),
    "g247": ("ABDFEC", "ADE.BFC", "AF.BE.CD"),
    "g248": ("ABDFEC", "ADE.BFC", "AF.BE.CD"),
}

SHORT_FORM_EXACT_IDS = frozenset({
    "g225", "g226", "g227",
})


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


@cache
def _colour_group_records() -> tuple[dict[str, Any], ...]:
    payload = json.loads(COLOR_PATTERN_DATA.read_text(encoding="utf-8"))
    return tuple(payload["colour_groups"])


def _catalogue_short_form(
    notation: str,
    signature: str | None = None,
    colours: int | None = None,
) -> dict[str, Any]:
    """Resolve one regular colour-group row without relying on catalog order."""

    matches = [
        row
        for row in _colour_group_records()
        if row["regular"]
        and row["chaim_notation"] == notation
        and (signature is None or row["chaim_short_signature"] == signature)
        and (colours is None or row["number_of_colours"] == colours)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one regular colour-catalog row for {notation}, "
            f"signature={signature!r}, colours={colours!r}; found {len(matches)}"
        )
    return matches[0]


def _catalogue_excerpt(row: dict[str, Any]) -> dict[str, Any]:
    excerpt = dict(row["book_excerpt"])
    excerpt.update({
        "pdf_page": excerpt["printed_page"] + 19,
        "highlight_target": "short-signature",
    })
    return excerpt


def _mapped_book_excerpt(excerpt_key: str, printed_page: int) -> dict[str, Any]:
    source = BOOK_EXCERPTS[excerpt_key]
    if source["printed_page"] != printed_page:
        raise ValueError(f"book excerpt page mismatch for {excerpt_key}")
    return {
        "work": "The Symmetries of Things",
        "image": source["image"],
        "title": source["title"],
        "context": source["context"],
        "alt": source["alt"],
        "printed_page": printed_page,
        "pdf_page": printed_page + 19,
        "source_url": BOOK_PAGE_URL.format(page=printed_page),
        "highlight_target": "short-signature-and-type",
        "excerpt_key": excerpt_key,
    }


def signature_evidence(
    group_id: str,
    order: int,
    notation: str,
) -> dict[str, Any]:
    """Classify and attach the crop that supports the visible short form."""

    signature = (
        notation
        if order == 1
        else BOOK_TWO_FOLD_SIGNATURE_BY_TYPE[notation]
        if order == 2
        else BOOK_HIGHER_SIGNATURE_BY_ID[group_id]
    )
    common: dict[str, Any] = {
        "displayed_signature": signature,
        "printed_signature": None,
        "printed_type": None,
        "source_colour_group_id": None,
        "excerpt": None,
        "generator_relabeling": None,
        "conflicts": [],
    }

    if order == 1:
        return common | {
            "status": "onefold",
            "label": "ordinary onefold plane group",
            "summary": "No nontrivial short colour signature is needed.",
        }

    # Every twofold row and the three unproblematic direct C3 rows have a
    # unique crop of the *short-signature* cell in the sibling colour catalog.
    direct_catalogue_row: dict[str, Any] | None = None
    if order == 2 or group_id in SHORT_FORM_EXACT_IDS or group_id == "g234":
        direct_catalogue_row = _catalogue_short_form(notation, signature, order)
        common.update({
            "printed_signature": direct_catalogue_row["chaim_short_signature"],
            "printed_type": direct_catalogue_row["chaim_notation"],
            "source_colour_group_id": direct_catalogue_row["id"],
            "excerpt": _catalogue_excerpt(direct_catalogue_row),
        })

    if group_id in BOOK_REPRESENTATIVE_MULTIPLICITY_BY_ID:
        multiplicity = BOOK_REPRESENTATIVE_MULTIPLICITY_BY_ID[group_id]
        return common | {
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
        return common | {
            "status": "exact-printed",
            "label": "unique Table 11.1 short signature",
            "summary": (
                "Table 11.1 prints one short generator signature for this colour type, "
                "and the page reproduces it."
            ),
        }
    if group_id == "g234":
        common.update({
            "printed_type": "3*3³/◦",
            "conflicts": [{
                "printed_signature": signature,
                "printed_type": "3*3³/◦",
                "note": "Table 12.1 prints the displayed short form beside the wrong kernel.",
            }],
        })
        return common | {
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
        conflicting_row = _catalogue_short_form(notation, signature, order)
        common.update({
            "printed_signature": signature,
            "printed_type": notation,
            "excerpt": _mapped_book_excerpt("p164::632³/2222-exact", 164),
            "conflicts": [{
                "printed_signature": "³6²3²2",
                "printed_type": notation,
                "source_colour_group_id": conflicting_row["id"],
                "excerpt": _catalogue_excerpt(conflicting_row),
                "note": "Table 12.1 has transposition orders that cannot define C3.",
            }],
        })
        return common | {
            "status": "book-internal-discrepancy",
            "label": "p. 156 typo corrected by pp. 157 and 164",
            "summary": (
                "The displayed ³6³3¹2 is derived on p. 157 and printed with full "
                "permutations in Table 13.1. Table 12.1 instead has the inconsistent "
                "³6²3²2; the official errata does not list that typo."
            ),
        }
    if order == 3:
        evidence = common | {
            "status": "exact-printed",
            "label": "exact Table 12.1 short signature",
            "summary": (
                "Table 12.1 prints this order-only short signature for the cited type."
            ),
        }
        if group_id == "g227":
            evidence["generator_relabeling"] = {
                "α": "fable β",
                "β": "fable γ",
                "γ": "fable α",
            }
        return evidence
    if order in (4, 6):
        return common | {
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

    return escape(value.replace("∗", "*")).replace(
        "*",
        '<span class="orbifold-star">∗</span>',
    )


def fibrifold_html(value: str) -> str:
    """Render Conway's mirror glyph and fibre-turn subscripts semantically."""

    subscript_digits = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    output: list[str] = []
    run: list[str] = []
    for character in value:
        if character in "₀₁₂₃₄₅₆₇₈₉":
            run.append(character.translate(subscript_digits))
            continue
        if run:
            output.append(f"<sub>{''.join(run)}</sub>")
            run.clear()
        output.append(orbifold_html(character))
    if run:
        output.append(f"<sub>{''.join(run)}</sub>")
    return "".join(output)


def clockwork_symbol_html(value: str) -> str:
    """Render the catalog's clockwork orbifold symbol semantically."""

    subscript_digits = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    superscript_letters = str.maketrans("ᵃᵇ", "ab")
    output: list[str] = []
    subscript_run: list[str] = []

    def flush_subscript() -> None:
        if subscript_run:
            output.append(f"<sub>{''.join(subscript_run)}</sub>")
            subscript_run.clear()

    for character in value:
        if character in "₀₁₂₃₄₅₆₇₈₉":
            subscript_run.append(character.translate(subscript_digits))
            continue
        flush_subscript()
        if character in "ᵃᵇ":
            output.append(f"<sup>{character.translate(superscript_letters)}</sup>")
        else:
            output.append(orbifold_html(character))
    flush_subscript()
    return "".join(output)


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


def _hm_html(value: str) -> str:
    """Typeset Hermann--Mauguin screw-axis subscripts."""

    return re.sub(r"_([0-9]+)", r"<sub>\1</sub>", escape(value))


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
                "13.1 assigns the three generators the two nonzero powers C₃ and "
                "C₃², and the identity for type 632³/2222. Table 12.1 on p. "
                "156 instead prints "
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
        steps = []
        for step_notation, index, page in chain["steps"]:
            source_group = _catalogue_short_form(
                step_notation,
                colours=index,
            )
            steps.append({
                "notation": step_notation,
                "index": index,
                "printed_page": page,
                "pdf_page": page + 19,
                "url": BOOK_PAGE_URL.format(page=page),
                "excerpt_key": f"p{page}::{step_notation}",
                "short_signature": source_group["chaim_short_signature"],
                "source_colour_group_id": source_group["id"],
                "short_signature_excerpt": _catalogue_excerpt(source_group),
            })
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


def _presentation_operation_description(value: str) -> str:
    """Remove internal centre/axis labels that are not drawn in the atlas."""

    return value.split(" about centre ", 1)[0].split(" (axis direction ", 1)[0]


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


CELL_PRESENTATION_TEMPLATES = (
    ({"g6", "g9"}, "cyclic_2", "A² = 1", 2),
    ({"g7", "g55", "g57", "g59", "g60", "g61", "g62", "g63"},
     "elementary_2_2", "A² = B² = 1; AB = BA", 4),
    ({"g64", "g65", "g66", "g67", "g69", "g70", "g71", "g72", "g73"},
     "elementary_2_3", "A² = B² = C² = 1; AB = BA, AC = CA, BC = CB", 8),
    ({"g74"}, "elementary_2_4",
     "A² = B² = C² = D² = 1; AB = BA, AC = CA, AD = DA, BC = CB, BD = DB, CD = DC",
     16),
    ({"g75", "g137", "g139"}, "exceptional_16",
     "A² = B⁴ = (AB)⁴ = 1; AB² = B²A", 16),
    ({"g95", "g96", "g97"}, "cyclic_4", "A⁴ = 1", 4),
    ({"g98", "g99"}, "cyclic_2_x_4", "A² = B⁴ = 1; AB = BA", 8),
    ({"g129", "g130", "g131"}, "dihedral_4_reflections",
     "A² = B² = (AB)⁴ = 1", 8),
    ({"g133", "g134", "g135"}, "dihedral_4_rotation",
     "A² = B⁴ = (AB)² = 1", 8),
    ({"g136", "g138"}, "cyclic_2_x_dihedral_4",
     "A² = B² = C² = (BC)⁴ = 1; AB = BA, AC = CA", 16),
    ({"g225", "g226"}, "cyclic_3", "A³ = 1", 3),
    ({"g227"}, "elementary_3_2", "A³ = B³ = 1; AB = BA", 9),
    ({"g231", "g233"}, "dihedral_3", "A² = B² = (AB)³ = 1", 6),
    ({"g234", "g235"}, "exceptional_18",
     "A² = B³ = 1; B(ABA) = (ABA)B", 18),
    ({"g244", "g245", "g246", "g247", "g248"}, "cyclic_6", "A⁶ = 1", 6),
    ({"g269", "g270", "g271"}, "dihedral_6", "A² = B² = (AB)⁶ = 1", 12),
)


def _cell_presentation_template(group_id: str) -> tuple[str, str, int]:
    for group_ids, template, relations, quotient_order in CELL_PRESENTATION_TEMPLATES:
        if group_id in group_ids:
            return template, relations, quotient_order
    raise ValueError(f"missing cell-action presentation template for {group_id}")


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


def cell_action_presentation(
    group_id: str,
    render: dict[str, Any],
    base: str,
) -> dict[str, Any]:
    """Present the finite action after full-cell translations are collapsed."""

    operations = geometric_operations(render, base)
    generators = [
        {
            "name": row["generator"],
            "kind": row["kind"],
            "operation": _presentation_operation_description(row["operation"]),
            "phase": row["phase"],
            "time_shift": row["time_shift"],
        }
        for row in operations
        if row["role"] == "generator"
    ]
    for kind in ("mirror", "glide"):
        matching = [generator for generator in generators if generator["kind"] == kind]
        if len(matching) > 1:
            noun = "Mirror reflection" if kind == "mirror" else "Glide reflection"
            for index, generator in enumerate(matching, 1):
                generator["operation"] = f"{noun} in axis direction {index}"
    # The 17 direct-product rows are retained in the data but omitted from the
    # page.  Their cell presentations are not needed for this nontrivial atlas.
    if group_id not in {
        group for group_ids, _template, _relations, _order in CELL_PRESENTATION_TEMPLATES
        for group in group_ids
    }:
        return {
            "quotient": "G/Λ",
            "quotient_order": len(render["ops"]),
            "template": "omitted_trivial_time_action",
            "generators": generators,
            "relations": "omitted",
        }
    template, relations, quotient_order = _cell_presentation_template(group_id)
    if quotient_order != len(render["ops"]):
        raise ValueError(f"cell-action presentation order differs in {group_id}")
    expected_names = [chr(ord("A") + index) for index in range(len(generators))]
    if [generator["name"] for generator in generators] != expected_names:
        raise ValueError(f"cell-action generator names are not consecutive in {group_id}")
    _validate_cell_presentation_relations(group_id, template, render, base)
    return {
        "quotient": "G/Λ",
        "quotient_order": quotient_order,
        "template": template,
        "generators": generators,
        "relations": relations,
    }


def _permutation_from_cycle_code(code: str, colours: int) -> tuple[int, ...]:
    permutation = list(range(colours))
    if code == "1":
        return tuple(permutation)
    for cycle in code.split("."):
        indices = [ord(letter) - ord("A") for letter in cycle]
        if len(indices) < 2 or any(index < 0 or index >= colours for index in indices):
            raise ValueError(f"invalid {colours}-colour cycle code: {code}")
        for index, image in zip(indices, indices[1:] + indices[:1], strict=True):
            if permutation[index] != index:
                raise ValueError(f"overlapping cycles in code: {code}")
            permutation[index] = image
    return tuple(permutation)


def _permutation_order(permutation: Iterable[int]) -> int:
    values = tuple(permutation)
    result = 1
    for start in range(len(values)):
        cursor = values[start]
        length = 1
        while cursor != start:
            cursor = values[cursor]
            length += 1
            if length > len(values):
                raise ValueError(f"not a permutation: {values}")
        result = math.lcm(result, length)
    return result


def _cycle_notation(code: str) -> str:
    return "1" if code == "1" else "".join(f"({cycle})" for cycle in code.split("."))


def _permutation_notation(permutation: Iterable[int]) -> str:
    values = tuple(permutation)
    visited: set[int] = set()
    cycles: list[str] = []
    for start in range(len(values)):
        if start in visited:
            continue
        cursor = start
        cycle: list[int] = []
        while cursor not in visited:
            visited.add(cursor)
            cycle.append(cursor)
            cursor = values[cursor]
        if cursor != start:
            raise ValueError(f"not a permutation: {values}")
        if len(cycle) > 1:
            cycles.append("(" + "".join(chr(ord("A") + index) for index in cycle) + ")")
    return "".join(cycles) or "1"


def _permutation_code(permutation: Iterable[int]) -> str:
    notation = _permutation_notation(permutation)
    if notation == "1":
        return notation
    return ".".join(re.findall(r"\(([^)]+)\)", notation))


def _compose_colour_permutations(
    left: tuple[int, ...], right: tuple[int, ...]
) -> tuple[int, ...]:
    """Return ``left`` after ``right`` for permutations stored by images."""

    return tuple(left[right[index]] for index in range(len(left)))


def _colour_permutation_power(
    permutation: tuple[int, ...], exponent: int
) -> tuple[int, ...]:
    result = tuple(range(len(permutation)))
    for _ in range(exponent):
        result = _compose_colour_permutations(permutation, result)
    return result


def _short_signature_orders(signature: str) -> tuple[int, ...]:
    runs = re.findall(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", signature)
    return tuple(int(run.translate(SUPERSCRIPT_TO_ASCII)) for run in runs)


def _source_phase_labeling(
    group_id: str,
    colours: int,
    source_actions: list[dict[str, Any]],
    clock_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Audit one simultaneous relabeling from fixed phases to source letters."""

    candidates = []
    for candidate in permutation_group(source_actions):
        cycle = tuple(candidate)
        if _permutation_order(cycle) != colours:
            continue
        if all(
            _colour_permutation_power(cycle, action["clock_power"])
            == tuple(source["colour_permutation"])
            for source, action in zip(source_actions, clock_actions, strict=True)
        ):
            candidates.append(cycle)
    if len(candidates) != 1:
        raise ValueError(
            f"fixed/source colour relabeling is not unique in {group_id}: {candidates}"
        )
    source_cycle = candidates[0]
    labels_by_fixed_phase = [
        _colour_permutation_power(source_cycle, phase)[0]
        for phase in range(colours)
    ]
    for source, action in zip(source_actions, clock_actions, strict=True):
        source_permutation = tuple(source["colour_permutation"])
        clock_permutation = tuple(action["colour_permutation"])
        if any(
            source_permutation[labels_by_fixed_phase[index]]
            != labels_by_fixed_phase[clock_permutation[index]]
            for index in range(colours)
        ):
            raise ValueError(
                f"source action is not one simultaneous relabeling in "
                f"{group_id}:{action['generator']}"
            )
    return {
        "labels_by_fixed_phase": [
            chr(ord("A") + index) for index in labels_by_fixed_phase
        ],
        "forward_step_permutation": list(source_cycle),
        "forward_step_cycle": _permutation_notation(source_cycle),
    }


def chaim_presentation(
    group_id: str,
    parent: str,
    colours: int,
    notation: str,
    short_signature: str,
    render: dict[str, Any],
) -> dict[str, Any]:
    """Build the full-Γ presentation in Chaim's named geometric generators."""

    if colours <= 3:
        chaim_actions = generator_colour_actions(
            parent,
            colours,
            notation,
            short_signature,
        )
        action_source = "book-canonical"
    else:
        try:
            codes = COMPOSITE_COLOUR_ACTION_CODES[group_id]
        except KeyError as error:
            raise ValueError(f"missing composite colour action for {group_id}") from error
        geometry = GENERATOR_GEOMETRY[parent]
        if len(codes) != len(geometry):
            raise ValueError(f"composite generator/action mismatch in {group_id}")
        chaim_actions = [
            {
                "generator": generator,
                "geometry": description,
                "permutation_code": code,
                "colour_permutation": list(
                    _permutation_from_cycle_code(code, colours)
                ),
            }
            for (generator, description), code in zip(geometry, codes, strict=True)
        ]
        action_source = "regular-cyclic-rule-extension"

    if len(permutation_group(chaim_actions)) != colours:
        raise ValueError(f"Chaim action does not generate C_{colours} in {group_id}")
    if not presentation_relations_hold(parent, chaim_actions):
        raise ValueError(f"Chaim action violates the {parent} relations in {group_id}")

    signature_orders = _short_signature_orders(short_signature)
    action_orders = tuple(
        _permutation_order(action["colour_permutation"])
        for action in chaim_actions
    )
    if colours > 1 and action_orders != signature_orders:
        raise ValueError(
            f"short-form/action order mismatch in {group_id}: "
            f"{signature_orders} != {action_orders}"
        )

    affine_by_name = {
        row["generator"]: row
        for row in affine_generators_for(parent)["generators"]
    }
    aligned_by_name = {
        row["generator"]: row
        for row in _canonical_generator_alignment(group_id, parent, render)
    } if colours > 1 else {}
    clock_cycle = tuple((index + 1) % colours for index in range(colours))
    rendered_actions = []
    for action in chaim_actions:
        affine = affine_by_name[action["generator"]]
        alignment = aligned_by_name.get(action["generator"])
        visualization = (
            alignment["visualization"] if alignment else affine["visualization"]
        )
        time_shift = alignment["phase"] if alignment else Fraction(0)
        exponent = time_shift * colours
        if exponent.denominator != 1:
            raise ValueError(f"nonintegral clock power in {group_id}")
        clock_power = exponent.numerator % colours
        colour_permutation = _colour_permutation_power(clock_cycle, clock_power)
        permutation_code = _permutation_code(colour_permutation)
        marker: dict[str, Any] = {"kind": visualization["kind"]}
        if visualization["kind"] == "rotation":
            marker["order"] = {
                "half-turn": 2,
                "one-third turn": 3,
                "quarter-turn": 4,
                "one-sixth turn": 6,
            }[action["geometry"]]
        rendered = {
            "generator": action["generator"],
            "geometry": action["geometry"],
            "permutation_code": permutation_code,
            "colour_permutation": list(colour_permutation),
            "cycle_notation": _cycle_notation(permutation_code),
            "clock_power": clock_power,
            "time_shift": fraction_label(time_shift),
            "time_shift_label": _time_shift_description(time_shift),
            "source_permutation_code": action["permutation_code"],
            "source_colour_permutation": action["colour_permutation"],
            "source_cycle_notation": _cycle_notation(action["permutation_code"]),
            "marker": marker,
        }
        if alignment:
            rendered |= {
                "plate_source_index": alignment["source_index"],
                "plate_lattice_shift": list(alignment["lattice_shift"]),
                "plate_visualization": alignment["visualization"],
            }
        rendered_actions.append(rendered)

    if len(permutation_group(rendered_actions)) != colours:
        raise ValueError(f"clock action does not generate C_{colours} in {group_id}")
    if not presentation_relations_hold(parent, rendered_actions):
        raise ValueError(f"clock action violates the {parent} relations in {group_id}")
    clock_action_orders = tuple(
        _permutation_order(action["colour_permutation"])
        for action in rendered_actions
    )
    if colours > 1 and clock_action_orders != signature_orders:
        raise ValueError(
            f"short-form/clock-action order mismatch in {group_id}: "
            f"{signature_orders} != {clock_action_orders}"
        )

    presentation = group_presentation(parent)
    if presentation["generators"] != [
        action["generator"] for action in rendered_actions
    ]:
        raise ValueError(f"presentation generator order mismatch in {group_id}")
    return {
        "ambient_group": "Γ",
        "generators": rendered_actions,
        "relations": presentation["relations"],
        "action_source": action_source,
        "cyclic_image": f"C_{colours}",
        "colour_order": "fixed-forward-phase",
        "colour_labels": [
            chr(ord("A") + index) for index in range(colours)
        ],
        "clock_cycle": {
            "symbol": f"C_{colours}",
            "permutation": list(clock_cycle),
            "cycle_notation": _permutation_notation(clock_cycle),
            "time_shift": fraction_label(Fraction(1, colours)),
        },
        "source_labeling": _source_phase_labeling(
            group_id,
            colours,
            chaim_actions,
            rendered_actions,
        ),
    }


def _key_power(value: tuple[Any, ...], exponent: int) -> tuple[Any, ...]:
    result = (M_ID, (Fraction(0), Fraction(0)), 1, Fraction(0))
    for _ in range(exponent):
        result = compose_keys(result, value)
    return result


def _validate_cell_presentation_relations(
    group_id: str,
    template: str,
    render: dict[str, Any],
    base: str,
) -> None:
    identity = (M_ID, (Fraction(0), Fraction(0)), 1, Fraction(0))
    operations = []
    for source_index, operation in enumerate(render["ops"]):
        value = matrix(operation)
        translation = tuple(exact_fraction(x) for x in operation["v"])
        phase = exact_fraction(operation["tau"])
        key = op_key(operation)
        if key == identity:
            continue
        determinant = det2(value)
        if value == M_ID:
            kind = "translation"
        elif determinant == 1:
            kind = "rotation"
        else:
            square_translation = (
                translation[0] + value[0][0] * translation[0] + value[0][1] * translation[1],
                translation[1] + value[1][0] * translation[0] + value[1][1] * translation[1],
            )
            kind = "mirror" if square_translation == (0, 0) else "glide"
        operations.append(
            {
                "source_index": source_index,
                "key": key,
                "matrix": value,
                "translation": translation,
                "phase_fraction": phase,
                "kind": kind,
            }
        )
    all_keys = {identity, *(operation["key"] for operation in operations)}
    generators = _minimal_operation_generators(operations, all_keys)

    def product(*values: tuple[Any, ...]) -> tuple[Any, ...]:
        result = identity
        for value in values:
            result = compose_keys(result, value)
        return result

    def closes(value: tuple[Any, ...], exponent: int) -> bool:
        return _key_power(value, exponent) == identity

    def commute(left: tuple[Any, ...], right: tuple[Any, ...]) -> bool:
        return compose_keys(left, right) == compose_keys(right, left)

    valid = False
    cyclic_orders = {"cyclic_2": 2, "cyclic_3": 3, "cyclic_4": 4, "cyclic_6": 6}
    if template in cyclic_orders:
        valid = len(generators) == 1 and closes(generators[0], cyclic_orders[template])
    elif template in {"elementary_2_2", "elementary_2_3", "elementary_2_4"}:
        count = int(template[-1])
        valid = (
            len(generators) == count
            and all(closes(generator, 2) for generator in generators)
            and all(commute(left, right) for left, right in combinations(generators, 2))
        )
    elif template == "exceptional_16" and len(generators) == 2:
        a, b = generators
        valid = closes(a, 2) and closes(b, 4) and closes(product(a, b), 4) and commute(a, _key_power(b, 2))
    elif template in {"cyclic_2_x_4", "elementary_3_2"} and len(generators) == 2:
        a, b = generators
        orders = (2, 4) if template == "cyclic_2_x_4" else (3, 3)
        valid = closes(a, orders[0]) and closes(b, orders[1]) and commute(a, b)
    elif template in {"dihedral_4_reflections", "dihedral_3", "dihedral_6"} and len(generators) == 2:
        a, b = generators
        order = {"dihedral_4_reflections": 4, "dihedral_3": 3, "dihedral_6": 6}[template]
        valid = closes(a, 2) and closes(b, 2) and closes(product(a, b), order)
    elif template == "dihedral_4_rotation" and len(generators) == 2:
        a, b = generators
        valid = closes(a, 2) and closes(b, 4) and closes(product(a, b), 2)
    elif template == "cyclic_2_x_dihedral_4" and len(generators) == 3:
        a, b, c = generators
        valid = all(closes(generator, 2) for generator in generators) and closes(product(b, c), 4) and commute(a, b) and commute(a, c)
    elif template == "exceptional_18" and len(generators) == 2:
        a, b = generators
        aba = product(a, b, a)
        valid = closes(a, 2) and closes(b, 3) and commute(b, aba)
    if not valid:
        raise ValueError(f"cell-action relations fail in {group_id}")


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
    group: dict[str, Any], *, complement_skips: bool = False
) -> tuple[Any, ...]:
    """Coordinate signature used for the traditional unoriented colour quotient."""

    order = group["clock_order"]
    rows = []
    for operation in group["render"]["ops"]:
        phase = int(exact_fraction(operation["tau"]) * order) % order
        if complement_skips:
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
        presentation = chaim_presentation(
            group_id,
            group["base"],
            order,
            notation,
            short_signature,
            group["render"],
        )
        residues = [
            {
                "index": j,
                "phase": fraction_label(Fraction(j, order)),
                "color": PALETTE[j],
                "colour_label": presentation["colour_labels"][j],
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
            "cell_action_presentation": cell_action_presentation(
                group_id, group["render"], group["base"]
            ),
            "chaim_presentation": presentation,
            "clockwork_description": clockwork_description(group, order),
            "coloring_description": coloring_description(group, order, kernel_base),
            "book_audit": book_audit(
                group_id, order, parent_orbifold, kernel_orbifold
            ),
            "complementary_skip_mate": COMPLEMENTARY_SKIP_MATE.get(group_id),
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
            "schema_version": 9,
            "title": "Clockwork/coloring correspondence",
            "source_catalog_url": CATALOG_DATA_URL,
            "source_catalog_sha256": digest,
            "source_catalog_total_groups": 275,
            "selection": "group.forward == true",
            "forward_groups": 68,
            "traditional_colour_classes_after_identifying_complementary_skips": 64,
            "definition": (
                "kappa(M,v) = N*tau mod N; K = ker(kappa); regular action has H = K; "
                "ToS type is G for N=1, G/K for N=2, and G^N/K for N>2; "
                "each named generator has fixed chronological colour action "
                "C_N^(N*tau), where C_N=(ABC...) is one positive phase step; "
                "Chaim's source permutation labels remain separate provenance"
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
        record["cell_action_presentation"] = cell_action_presentation(
            group_id, record["render"], record["parent"]["hm"]
        )
        record["chaim_presentation"] = chaim_presentation(
            group_id,
            record["parent"]["hm"],
            order,
            notation,
            record["book_color_signature"],
            record["render"],
        )
        record["phase_residues"] = [
            {
                "index": index,
                "phase": fraction_label(Fraction(index, order)),
                "color": PALETTE[index],
                "colour_label": record["chaim_presentation"]["colour_labels"][index],
            }
            for index in range(order)
        ]
        record.pop("geometric_operations", None)
        record["clockwork_description"] = clockwork_description(source_like, order)
        record["coloring_description"] = coloring_description(
            source_like, order, record["kernel"]["hm"]
        )
        record["book_audit"] = book_audit(group_id, order, parent, kernel)
        record["complementary_skip_mate"] = COMPLEMENTARY_SKIP_MATE.get(group_id)
        record.pop("inverse_clock_mate", None)
        record["image_alt"] = (
            f"Static perfect {order}-colouring for group {group_id}: "
            f"asymmetric motifs carry phase colours for Conway type {notation}."
        )

    meta = payload["meta"]
    meta["schema_version"] = 9
    meta["definition"] = (
        "kappa(M,v) = N*tau mod N; K = ker(kappa); regular action has H = K; "
        "ToS type is G for N=1, G/K for N=2, and G^N/K for N>2; "
        "each named generator has fixed chronological colour action "
        "C_N^(N*tau), where C_N=(ABC...) is one positive phase step; "
        "Chaim's source permutation labels remain separate provenance"
    )
    meta["traditional_colour_classes_after_identifying_complementary_skips"] = 64
    meta.pop("traditional_color_classes_after_clock_inversion", None)
    meta["book_audit_counts"] = EXPECTED_BOOK_AUDIT_COUNTS
    meta["signature_evidence_counts"] = EXPECTED_SIGNATURE_EVIDENCE_COUNTS
    meta["book"]["annotated_excerpt_count"] = len(BOOK_EXCERPTS)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    meta = payload.get("meta", {})
    groups = payload.get("groups", [])
    if meta.get("schema_version") != 9:
        raise ValueError("correspondence data must use schema version 9")
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
    nontrivial_ids = {
        group["id"] for group in groups if group["clock_order"] > 1
    }
    if set(CANONICAL_TO_RENDER_CONJUGACY_BY_ID) != nontrivial_ids:
        raise ValueError("canonical plate conjugacies must cover the 51 displayed groups")

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
        signature_excerpt = expected_signature_evidence.get("excerpt")
        if expected_signature_evidence["status"] == "rule-extension":
            if signature_excerpt is not None:
                raise ValueError(f"derived short form claims a direct crop in {group_id}")
        elif order > 1:
            if not signature_excerpt or signature_excerpt.get("highlight_target") not in {
                "short-signature", "short-signature-and-type",
            }:
                raise ValueError(f"short form lacks matching crop metadata in {group_id}")
            if not (ROOT / signature_excerpt["image"]).is_file():
                raise ValueError(f"short-form crop is missing in {group_id}")
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
            short_excerpt = step.get("short_signature_excerpt")
            if (
                not short_excerpt
                or short_excerpt.get("highlight_target") != "short-signature"
                or short_excerpt.get("printed_page") != step["printed_page"]
            ):
                raise ValueError(f"prime-chain short-form crop mismatch in {group_id}")
        if group["catalog_url"] != f"{CATALOG_ROOT}#{group_id}":
            raise ValueError(f"catalog deep link mismatch in {group_id}")
        if [row["index"] for row in group["phase_residues"]] != list(range(order)):
            raise ValueError(f"phase legend mismatch in {group_id}")
        expected_presentation = cell_action_presentation(
            group_id, group["render"], group["parent"]["hm"]
        )
        if group.get("cell_action_presentation") != expected_presentation:
            raise ValueError(f"cell-action presentation differs from render data in {group_id}")
        expected_chaim_presentation = chaim_presentation(
            group_id,
            group["parent"]["hm"],
            order,
            group["tos_notation"],
            group["book_color_signature"],
            group["render"],
        )
        if group.get("chaim_presentation") != expected_chaim_presentation:
            raise ValueError(f"Chaim presentation differs from source data in {group_id}")
        expected_residues = [
            {
                "index": index,
                "phase": fraction_label(Fraction(index, order)),
                "color": PALETTE[index],
                "colour_label": expected_chaim_presentation["colour_labels"][index],
            }
            for index in range(order)
        ]
        if group["phase_residues"] != expected_residues:
            raise ValueError(f"phase palette/book-letter mapping differs in {group_id}")
        clock_cycle = tuple(expected_chaim_presentation["clock_cycle"]["permutation"])
        if _permutation_order(clock_cycle) != order:
            raise ValueError(f"one positive phase does not generate C_{order} in {group_id}")
        for action in expected_chaim_presentation["generators"]:
            exponent = Fraction(action["time_shift"]) * order
            if (
                exponent.denominator != 1
                or action["clock_power"] != exponent.numerator % order
                or _colour_permutation_power(clock_cycle, action["clock_power"])
                != tuple(action["colour_permutation"])
            ):
                raise ValueError(
                    f"colour permutation and directed phase differ in "
                    f"{group_id}:{action['generator']}"
                )
        represented_phases = {
            exact_fraction(operation["tau"])
            for operation in group["render"]["ops"]
        }
        operation_phases = {
            Fraction(row["phase"])
            for row in expected_presentation["generators"]
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

    for group_id, mate_id in COMPLEMENTARY_SKIP_MATE.items():
        group = next(row for row in groups if row["id"] == group_id)
        mate = next(row for row in groups if row["id"] == mate_id)
        if (
            group["complementary_skip_mate"] != mate_id
            or mate["complementary_skip_mate"] != group_id
        ):
            raise ValueError("complementary-skip mate relation is not reciprocal")
        if (
            group["parent"] != mate["parent"]
            or group["kernel"] != mate["kernel"]
            or group["clock_order"] != mate["clock_order"]
        ):
            raise ValueError(
                f"complementary-skip pair differs as a traditional coloring: {group_id}"
            )

    color_classes: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for group in groups:
        signature = min(
            phase_character_signature(group),
            phase_character_signature(group, complement_skips=True),
        )
        color_classes[signature].append(group["id"])
    repeated = {
        frozenset(ids) for ids in color_classes.values() if len(ids) > 1
    }
    expected_repeated = {
        frozenset((group_id, mate_id))
        for group_id, mate_id in COMPLEMENTARY_SKIP_MATE.items()
    }
    if len(color_classes) != 64 or repeated != expected_repeated:
        raise ValueError("traditional complementary-skip quotient must have 64 classes")
    if (
        meta.get("traditional_colour_classes_after_identifying_complementary_skips")
        != len(color_classes)
    ):
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


OverlayMotion = tuple[
    tuple[tuple[int, int], tuple[int, int]],
    tuple[float, float],
]


def _overlay_physical_motion(
    value: OverlayMotion,
    basis: list[list[float]],
) -> tuple[tuple[tuple[float, float], tuple[float, float]], tuple[float, float]]:
    """Conjugate a lattice-coordinate motion into the plate's Euclidean plane."""

    matrix_value, vector_value = value
    physical_basis = [
        [float(basis[0][0]), float(basis[1][0])],
        [float(basis[0][1]), float(basis[1][1])],
    ]
    physical_matrix = _mat_mul(
        _mat_mul(
            physical_basis,
            [[float(component) for component in row] for row in matrix_value],
        ),
        _mat_inv(physical_basis),
    )
    physical_vector = (
        physical_basis[0][0] * float(vector_value[0])
        + physical_basis[0][1] * float(vector_value[1]),
        physical_basis[1][0] * float(vector_value[0])
        + physical_basis[1][1] * float(vector_value[1]),
    )
    return (
        tuple(tuple(component for component in row) for row in physical_matrix),
        physical_vector,
    )  # type: ignore[return-value]


def _canonical_generator_alignment(
    group_id: str,
    parent: str,
    render: dict[str, Any],
) -> list[dict[str, Any]]:
    """Match each signed canonical generator to one exact rendered operation.

    Geometry determines the render coset; the matched coset then supplies its
    directed clock phase.  Matching modulo integer lattice translations keeps
    the unmodded canonical lift available for an accurately positioned marker.
    """

    try:
        linear, offset = CANONICAL_TO_RENDER_CONJUGACY_BY_ID[group_id]
    except KeyError as error:
        raise ValueError(f"missing canonical plate conjugacy for {group_id}") from error
    inverse = _mat_inv(linear)
    result = []
    for affine in affine_generators_for(parent)["generators"]:
        canonical_matrix = affine["matrix"]
        canonical_vector = affine["translation"]
        raw_matrix = _mat_mul(_mat_mul(linear, canonical_matrix), inverse)
        snapped_matrix = tuple(
            tuple(round(component) for component in row) for row in raw_matrix
        )
        if any(
            abs(raw_matrix[row][column] - snapped_matrix[row][column]) > 1e-8
            for row in range(2)
            for column in range(2)
        ):
            raise ValueError(
                f"canonical generator matrix does not snap in {group_id}: "
                f"{affine['generator']}"
            )
        linear_vector = (
            linear[0][0] * canonical_vector[0]
            + linear[0][1] * canonical_vector[1],
            linear[1][0] * canonical_vector[0]
            + linear[1][1] * canonical_vector[1],
        )
        transformed_offset = (
            snapped_matrix[0][0] * offset[0]
            + snapped_matrix[0][1] * offset[1],
            snapped_matrix[1][0] * offset[0]
            + snapped_matrix[1][1] * offset[1],
        )
        raw_vector = (
            linear_vector[0] + offset[0] - transformed_offset[0],
            linear_vector[1] + offset[1] - transformed_offset[1],
        )
        snapped_vector = tuple(
            float(Fraction(component).limit_denominator(48))
            for component in raw_vector
        )
        if any(
            abs(raw_vector[index] - snapped_vector[index]) > 1e-8
            for index in range(2)
        ):
            raise ValueError(
                f"canonical generator vector does not snap in {group_id}: "
                f"{affine['generator']}"
            )
        matches = []
        for source_index, operation in enumerate(render["ops"]):
            if matrix(operation) != snapped_matrix:
                continue
            differences = tuple(
                snapped_vector[index] - float(operation["v"][index])
                for index in range(2)
            )
            shifts = tuple(round(component) for component in differences)
            if all(
                abs(differences[index] - shifts[index]) <= 1e-8
                for index in range(2)
            ):
                matches.append((source_index, operation, shifts))
        if len(matches) != 1:
            raise ValueError(
                f"canonical generator does not have one rendered coset in "
                f"{group_id}:{affine['generator']}: {len(matches)}"
            )
        source_index, operation, lattice_shift = matches[0]
        motion: OverlayMotion = (snapped_matrix, snapped_vector)  # type: ignore[assignment]
        result.append(
            {
                "generator": affine["generator"],
                "motion": motion,
                "phase": exact_fraction(operation["tau"]),
                "source_index": source_index,
                "lattice_shift": lattice_shift,
                "visualization": generator_visualization(
                    _overlay_physical_motion(motion, render["basis"])
                ),
            }
        )
    return result


def _plate_cell_scale(render: dict[str, Any]) -> float:
    b1, _b2, _radius, _ranges = _site_geometry(
        render,
        IMAGE_WIDTH * ANTIALIAS,
        IMAGE_HEIGHT * ANTIALIAS,
    )
    basis_length = math.hypot(*render["basis"][0])
    if basis_length <= 1e-9:
        raise ValueError("plate basis has a zero first vector")
    return math.hypot(*b1) / basis_length / ANTIALIAS


def _plate_generator_assignment(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the deterministic, signed placement stored with each action."""

    actions = record["chaim_presentation"]["generators"]
    return [
        {
            "generator": action["generator"],
            "geometry": action["geometry"],
            "marker": action["marker"],
            "visualization": action["plate_visualization"],
            "phase": Fraction(action["time_shift"]),
        }
        for action in actions
    ]


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
            f"<span>{escape(residue['colour_label'])} · "
            f"phase {escape(residue['phase'])}</span>"
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


def _rotation_screw_step(
    order: int,
    time_shift: str | Fraction,
    angle_degrees: float,
) -> int:
    """Return the crystallographic screw-axis subscript of a polar rotation.

    In the polar height lift, a spatial n-fold rotation with clock shift tau
    is the screw axis n_m.  The sign of the displayed elementary turn matters:
    m = s*n*tau modulo n, with s=+1 for +360/n and s=-1 for -360/n.  This makes
    inverse operations on the same crystallographic axis share its n_m mark.
    """

    indexed_shift = order * Fraction(time_shift)
    if indexed_shift.denominator != 1:
        raise ValueError(
            f"rotation of order {order} has incompatible time shift {time_shift}"
        )
    elementary_angle = 360 / order
    normalized_angle = angle_degrees % 360
    if math.isclose(normalized_angle, elementary_angle, abs_tol=1e-7):
        orientation = 1
    elif math.isclose(
        normalized_angle,
        (360 - elementary_angle) % 360,
        abs_tol=1e-7,
    ):
        orientation = -1
    else:
        raise ValueError(
            f"rotation of order {order} has non-elementary angle {angle_degrees}"
        )
    return (orientation * indexed_shift.numerator) % order


def _rotation_symbol_key(
    order: int,
    time_shift: str | Fraction,
    angle_degrees: float,
) -> str:
    return (
        f"rotation-{order}-"
        f"{_rotation_screw_step(order, time_shift, angle_degrees)}"
    )


def _rotation_symbol_body_html(order: int, screw_step: int) -> str:
    """Draw one origin-centred crystallographic rotation/screw-axis symbol.

    Filled lenses, triangles, diamonds and hexagons follow the International
    Tables projection vocabulary.  For n_m, gcd(n, m) selects the evenly
    spaced arm starts, while m versus n-m reverses their handedness.
    """

    if order not in {2, 3, 4, 6}:
        raise ValueError(f"unsupported rotation marker order: {order}")
    if not 0 <= screw_step < order:
        raise ValueError(f"invalid {order}-fold screw step: {screw_step}")

    radii = {2: 8.8, 3: 9.6, 4: 9.6, 6: 9.2}
    radius = radii[order]
    if order == 2:
        core = (
            '<path class="generator-symbol-core" '
            'd="M0 -9.6 C-4.6 -6.2 -4.6 6.2 0 9.6 '
            'C4.6 6.2 4.6 -6.2 0 -9.6Z"></path>'
        )
    else:
        points = []
        for index in range(order):
            angle = -math.pi / 2 + 2 * math.pi * index / order
            points.append(
                f"{_svg_number(radius * math.cos(angle))},"
                f"{_svg_number(radius * math.sin(angle))}"
            )
        core = (
            '<polygon class="generator-symbol-core" '
            f'points="{" ".join(points)}"></polygon>'
        )

    if screw_step == 0:
        arms = ""
    else:
        spacing = math.gcd(order, screw_step)
        handedness = -1 if screw_step <= order / 2 else 1
        commands = []
        for index in range(0, order, spacing):
            angle = -math.pi / 2 + 2 * math.pi * index / order
            radial = (math.cos(angle), math.sin(angle))
            tangent = (-math.sin(angle), math.cos(angle))
            start = (radius * radial[0], radius * radial[1])
            end = (
                start[0] + 4.3 * radial[0] + handedness * 4.1 * tangent[0],
                start[1] + 4.3 * radial[1] + handedness * 4.1 * tangent[1],
            )
            commands.append(
                f"M{_svg_number(start[0])} {_svg_number(start[1])}"
                f"L{_svg_number(end[0])} {_svg_number(end[1])}"
            )
        arms = (
            '<path class="generator-symbol-arms" '
            f'd="{" ".join(commands)}"></path>'
        )
    return core + arms


# The four named planar glides require conventional-setting information that
# cannot be inferred from the plotted 2D glide vector alone.  The classification
# records the chosen lifted operation in the constructed polar coordinates,
# rather than collapsing centring-related representatives into one conventional
# symmetry-element set.  All canonical mirror generators have zero in-plane
# glide and are classified directly by their polar (c-axis) shift below.
_PLANE_LIFT_OVERRIDE_BY_GENERATOR: dict[
    tuple[str, str], tuple[str, Fraction]
] = {
    ("g9", "Z"): ("n", Fraction(1, 2)),
    ("g59", "Z"): ("n", Fraction(1, 2)),
    ("g63", "Z"): ("axial", Fraction(0)),
    ("g75", "Z"): ("d", Fraction(1, 4)),
}

_PLANE_LIFT_KIND = {
    "m": "mirror-plane",
    "c": "c-glide-plane",
    "axial": "axial-glide-plane",
    "n": "n-glide-plane",
    "d": "d-glide-plane",
}


def _polar_plane_symbol(
    group_id: str,
    generator: dict[str, Any],
) -> str:
    """Classify one orientation-reversing lift in projection along time."""

    marker_kind = generator["marker"]["kind"]
    phase = Fraction(generator["phase"])
    if marker_kind == "mirror":
        if phase == 0:
            return "m"
        if phase == Fraction(1, 2):
            return "c"
        raise ValueError(
            f"unsupported polar mirror shift in {group_id}:"
            f"{generator['generator']}={phase}"
        )
    if marker_kind != "glide":
        raise ValueError(
            f"unsupported polar plane generator in {group_id}: {marker_kind}"
        )
    try:
        plane_symbol, expected_phase = _PLANE_LIFT_OVERRIDE_BY_GENERATOR[
            (group_id, generator["generator"])
        ]
    except KeyError as error:
        raise ValueError(
            f"unclassified planar glide lift in {group_id}:"
            f"{generator['generator']}"
        ) from error
    if phase != expected_phase:
        raise ValueError(
            f"polar glide phase drift in {group_id}:{generator['generator']}: "
            f"{phase} != {expected_phase}"
        )
    return plane_symbol


def _svg_number(value: float) -> str:
    rendered = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if rendered == "-0" else rendered


def _plate_screen_point(point: Iterable[float], scale: float) -> tuple[float, float]:
    x, y = point
    return IMAGE_WIDTH / 2 + scale * x, IMAGE_HEIGHT / 2 - scale * y


def _clipped_plate_axis(
    axis_point: Iterable[float],
    axis_direction: Iterable[float],
    scale: float,
) -> dict[str, tuple[float, float]] | None:
    point = _plate_screen_point(axis_point, scale)
    world_dx, world_dy = axis_direction
    screen_direction = (world_dx, -world_dy)
    length = math.hypot(*screen_direction)
    if length <= 1e-9:
        raise ValueError("plate generator has a zero axis direction")
    unit = (screen_direction[0] / length, screen_direction[1] / length)
    lower = -math.inf
    upper = math.inf
    for coordinate, component, minimum, maximum in (
        (point[0], unit[0], 9, IMAGE_WIDTH - 9),
        (point[1], unit[1], 9, IMAGE_HEIGHT - 9),
    ):
        if abs(component) <= 1e-9:
            if not minimum <= coordinate <= maximum:
                return None
            continue
        first = (minimum - coordinate) / component
        second = (maximum - coordinate) / component
        lower = max(lower, min(first, second))
        upper = min(upper, max(first, second))
    if lower > upper:
        return None
    return {
        "start": (point[0] + lower * unit[0], point[1] + lower * unit[1]),
        "end": (point[0] + upper * unit[0], point[1] + upper * unit[1]),
        "direction": unit,
        "normal": (-unit[1], unit[0]),
    }


def _plate_generator_label_html(
    generator: str,
    x: float,
    y: float,
) -> str:
    return (
        f'<text class="plate-generator-label" x="{_svg_number(x)}" '
        f'y="{_svg_number(y)}" text-anchor="middle" '
        f'dominant-baseline="central">{escape(generator)}</text>'
    )


def _plate_rotation_glyph_html(order: int, screw_step: int) -> str:
    def layers(drawing: str) -> str:
        return (
            f'<g class="plate-generator-glyph-halo">{drawing}</g>'
            f'<g class="plate-generator-glyph">{drawing}</g>'
        )

    drawing = (
        '<g class="generator-symbol-body">'
        f'{_rotation_symbol_body_html(order, screw_step)}'
        '</g>'
    )
    return layers(drawing)


def _plate_d_glide_arrows_html(
    axis: dict[str, tuple[float, float]],
    glide_distance: float,
    time_shift: Fraction,
) -> str:
    """Draw the paired arrows used by the International Tables d-glide mark."""

    paths = _d_glide_arrow_paths(axis, glide_distance, time_shift)
    return "".join(
        f'<path class="plate-generator-quarter-arrow-halo" d="{path}"></path>'
        f'<path class="plate-generator-quarter-arrow" d="{path}"></path>'
        for path in paths
    )


def _d_glide_arrow_paths(
    axis: dict[str, tuple[float, float]],
    glide_distance: float,
    time_shift: Fraction,
) -> tuple[str, str]:
    """Return the two arrow paths shared by plate and legend d-glide marks."""

    start = axis["start"]
    end = axis["end"]
    direction = axis["direction"]
    signed_shift = time_shift if time_shift <= Fraction(1, 2) else time_shift - 1
    if abs(signed_shift) != Fraction(1, 4):
        raise ValueError(f"d-glide requires a quarter polar shift, got {time_shift}")
    if glide_distance * signed_shift < 0:
        direction = (-direction[0], -direction[1])
    normal = (-direction[1], direction[0])
    paths: list[str] = []
    for fraction in (0.43, 0.57):
        anchor = (
            start[0] + (end[0] - start[0]) * fraction,
            start[1] + (end[1] - start[1]) * fraction,
        )
        tip = (
            anchor[0] + 5.5 * direction[0],
            anchor[1] + 5.5 * direction[1],
        )
        base = (
            anchor[0] - 4.5 * direction[0],
            anchor[1] - 4.5 * direction[1],
        )
        wings = (
            (base[0] + 4.2 * normal[0], base[1] + 4.2 * normal[1]),
            (base[0] - 4.2 * normal[0], base[1] - 4.2 * normal[1]),
        )
        paths.append(
            f'M {_svg_number(wings[0][0])} {_svg_number(wings[0][1])} '
            f'L {_svg_number(tip[0])} {_svg_number(tip[1])} '
            f'L {_svg_number(wings[1][0])} {_svg_number(wings[1][1])}'
        )
    return paths[0], paths[1]


def _diagram_rotation_symbol_html(order: int, screw_step: int) -> str:
    """Render one legend-sized example through the plate's SVG glyph source."""

    key = f"rotation-{order}-{screw_step}"
    return (
        '<svg class="diagram-symbol-icon diagram-symbol-icon--rotation" '
        f'data-legend-icon="{key}" viewBox="0 0 68 32" '
        'aria-hidden="true" focusable="false">'
        '<g class="generator-symbol-body" transform="translate(34 16)">'
        f'{_rotation_symbol_body_html(order, screw_step)}'
        '</g></svg>'
    )


def _diagram_plane_symbol_html(plane_symbol: str) -> str:
    """Render one legend-sized International Tables plane/glide line."""

    if plane_symbol not in _PLANE_LIFT_KIND:
        raise ValueError(f"unsupported legend plane symbol: {plane_symbol}")
    axis = {
        "start": (6.0, 16.0),
        "end": (62.0, 16.0),
        "direction": (1.0, 0.0),
        "normal": (0.0, 1.0),
    }
    drawing = (
        '<line class="diagram-symbol-plane '
        f'plate-generator-axis--plane-{plane_symbol}" '
        'x1="6" y1="16" x2="62" y2="16"></line>'
    )
    if plane_symbol == "d":
        drawing += "".join(
            f'<path class="diagram-symbol-quarter-arrow" d="{path}"></path>'
            for path in _d_glide_arrow_paths(
                axis,
                glide_distance=1.0,
                time_shift=Fraction(1, 4),
            )
        )
    return (
        '<svg class="diagram-symbol-icon diagram-symbol-icon--plane" '
        f'data-legend-icon="plane-{plane_symbol}" viewBox="0 0 68 32" '
        'aria-hidden="true" focusable="false">'
        f'{drawing}</svg>'
    )


def _diagram_symbol_legend_html() -> str:
    """Build the scan-friendly, one-symbol-per-row crystallographic key."""

    rotation_rows = (
        (
            "rotation-2-0",
            _diagram_rotation_symbol_html(2, 0),
            "2-fold rotation axis",
            "Filled lens; half-turn with no clock-axis rise.",
        ),
        (
            "rotation-2-1",
            _diagram_rotation_symbol_html(2, 1),
            '<span role="img" aria-label="two-one screw axis">2<sub>1</sub> screw axis</span>',
            "Two-arm lens; half-turn with a +1/2-period rise.",
        ),
        (
            "rotation-3-0",
            _diagram_rotation_symbol_html(3, 0),
            "3-fold rotation axis",
            "Filled triangle; one-third turn with no clock-axis rise.",
        ),
        (
            "rotation-3-1",
            _diagram_rotation_symbol_html(3, 1),
            '<span role="img" aria-label="three-one screw axis">3<sub>1</sub> screw axis</span>',
            "Three-stroke triangle; positive one-third turn with a +1/3-period rise.",
        ),
        (
            "rotation-3-2",
            _diagram_rotation_symbol_html(3, 2),
            '<span role="img" aria-label="three-two screw axis">3<sub>2</sub> screw axis</span>',
            "Opposite three-stroke triangle; positive one-third turn with a +2/3-period rise.",
        ),
        (
            "rotation-4-0",
            _diagram_rotation_symbol_html(4, 0),
            "4-fold rotation axis",
            "Filled diamond; quarter-turn with no clock-axis rise.",
        ),
        (
            "rotation-4-1",
            _diagram_rotation_symbol_html(4, 1),
            '<span role="img" aria-label="four-one screw axis">4<sub>1</sub> screw axis</span>',
            "Four-arm diamond; positive quarter-turn with a +1/4-period rise.",
        ),
        (
            "rotation-4-2",
            _diagram_rotation_symbol_html(4, 2),
            '<span role="img" aria-label="four-two screw axis">4<sub>2</sub> screw axis</span>',
            "Two-arm diamond; quarter-turn with a +1/2-period rise.",
        ),
        (
            "rotation-4-3",
            _diagram_rotation_symbol_html(4, 3),
            '<span role="img" aria-label="four-three screw axis">4<sub>3</sub> screw axis</span>',
            "Opposite four-arm diamond; positive quarter-turn with a +3/4-period rise.",
        ),
        (
            "rotation-6-1",
            _diagram_rotation_symbol_html(6, 1),
            '<span role="img" aria-label="six-one screw axis">6<sub>1</sub> screw axis</span>',
            "Six-arm hexagon; positive one-sixth turn with a +1/6-period rise.",
        ),
        (
            "rotation-6-2",
            _diagram_rotation_symbol_html(6, 2),
            '<span role="img" aria-label="six-two screw axis">6<sub>2</sub> screw axis</span>',
            "Three-arm hexagon; positive one-sixth turn with a +1/3-period rise.",
        ),
        (
            "rotation-6-3",
            _diagram_rotation_symbol_html(6, 3),
            '<span role="img" aria-label="six-three screw axis">6<sub>3</sub> screw axis</span>',
            "Two-arm hexagon; one-sixth turn with a +1/2-period rise.",
        ),
        (
            "rotation-6-4",
            _diagram_rotation_symbol_html(6, 4),
            '<span role="img" aria-label="six-four screw axis">6<sub>4</sub> screw axis</span>',
            "Opposite three-arm hexagon; positive one-sixth turn with a +2/3-period rise.",
        ),
        (
            "rotation-6-5",
            _diagram_rotation_symbol_html(6, 5),
            '<span role="img" aria-label="six-five screw axis">6<sub>5</sub> screw axis</span>',
            "Opposite six-arm hexagon; positive one-sixth turn with a +5/6-period rise.",
        ),
    )
    plane_rows = (
        (
            "plane-m",
            _diagram_plane_symbol_html("m"),
            "Mirror plane (m)",
            "Solid line; reflection with no glide component.",
        ),
        (
            "plane-axial",
            _diagram_plane_symbol_html("axial"),
            "In-plane axial glide",
            "Dashed line; reflection plus a half-cell step in the picture.",
        ),
        (
            "plane-c",
            _diagram_plane_symbol_html("c"),
            "Clock-axis glide (c)",
            "Dotted line; reflection plus a half-period step perpendicular to the picture.",
        ),
        (
            "plane-n",
            _diagram_plane_symbol_html("n"),
            "Diagonal n-glide",
            "Dash–dot line; half-steps in the picture and along the clock axis.",
        ),
        (
            "plane-d",
            _diagram_plane_symbol_html("d"),
            "Quarter-diagonal d-glide",
            "Arrowed dash–dot line; arrows select the sign of the quarter-period component.",
        ),
    )

    def items_html(rows: tuple[tuple[str, str, str, str], ...]) -> str:
        return "".join(
            '<li class="diagram-symbol-item" '
            f'data-legend-symbol="{escape(key)}">'
            f'<span class="diagram-symbol-image">{symbol}</span>'
            '<span class="diagram-symbol-explanation">'
            f'<strong>{label}</strong><span>{description}</span>'
            '</span></li>'
            for key, symbol, label, description in rows
        )

    return (
        '<section class="diagram-symbol-group" '
        'aria-labelledby="diagram-rotation-symbols-title">'
        '<h3 id="diagram-rotation-symbols-title">'
        'Rotation and screw axes (along the clock axis)</h3>'
        '<ul class="diagram-symbol-list" role="list">'
        f'{items_html(rotation_rows)}</ul></section>'
        '<section class="diagram-symbol-group" '
        'aria-labelledby="diagram-plane-symbols-title">'
        '<h3 id="diagram-plane-symbols-title">'
        'Mirror and glide planes (seen edge-on)</h3>'
        '<ul class="diagram-symbol-list" role="list">'
        f'{items_html(plane_rows)}</ul></section>'
    )


def _plate_generator_overlay_html(record: dict[str, Any]) -> str:
    placement = _plate_generator_assignment(record)
    scale = _plate_cell_scale(record["render"])
    markers: list[str] = []
    rotation_label_offsets = ((21, -17), (21, 18), (-21, 18), (-21, -17))
    axis_label_fractions = (0.18, 0.78, 0.42, 0.64)
    for index, generator in enumerate(placement):
        name = generator["generator"]
        marker = generator["marker"]
        kind = marker["kind"]
        order_attribute = ""
        symbol_key = kind
        classes = f"plate-generator plate-generator--{kind}"
        phase_attribute = escape(str(generator["phase"]))
        if kind == "rotation":
            order = marker["order"]
            angle_degrees = generator["visualization"]["angle_degrees"]
            screw_step = _rotation_screw_step(
                order,
                generator["phase"],
                angle_degrees,
            )
            symbol_key = _rotation_symbol_key(
                order,
                generator["phase"],
                angle_degrees,
            )
            classes += f" plate-generator--rotation-{order}"
            lift_kind = "rotation-axis" if screw_step == 0 else "screw-axis"
            order_attribute = (
                f' data-rotation-order="{order}" data-screw-step="{screw_step}"'
            )
            centre_x, centre_y = _plate_screen_point(
                generator["visualization"]["centre"], scale
            )
            label_dx, label_dy = rotation_label_offsets[
                index % len(rotation_label_offsets)
            ]
            drawing = (
                f'<g transform="translate({_svg_number(centre_x)} '
                f'{_svg_number(centre_y)})">'
                f'{_plate_rotation_glyph_html(order, screw_step)}'
                f'{_plate_generator_label_html(name, label_dx, label_dy)}'
                '</g>'
            )
        else:
            plane_symbol = _polar_plane_symbol(record["id"], generator)
            symbol_key = f"plane-{plane_symbol}"
            lift_kind = _PLANE_LIFT_KIND[plane_symbol]
            classes += f" plate-generator--plane-{plane_symbol}"
            order_attribute = f' data-plane-symbol="{plane_symbol}"'
            axis = _clipped_plate_axis(
                generator["visualization"]["axis_point"],
                generator["visualization"]["axis_direction"],
                scale,
            )
            if axis is None:
                raise ValueError(f"plate generator axis misses {record['id']}: {name}")
            start = axis["start"]
            end = axis["end"]
            line_coordinates = (
                f'x1="{_svg_number(start[0])}" y1="{_svg_number(start[1])}" '
                f'x2="{_svg_number(end[0])}" y2="{_svg_number(end[1])}"'
            )
            drawing = (
                f'<line class="plate-generator-axis-halo" {line_coordinates}></line>'
                f'<line class="plate-generator-axis '
                f'plate-generator-axis--plane-{plane_symbol}" '
                f'{line_coordinates}></line>'
            )
            if plane_symbol == "d":
                drawing += _plate_d_glide_arrows_html(
                    axis,
                    generator["visualization"]["glide_distance"],
                    generator["phase"],
                )
            label_fraction = axis_label_fractions[index % len(axis_label_fractions)]
            label_normal = 14 if index % 2 == 0 else -14
            label_x = (
                start[0]
                + (end[0] - start[0]) * label_fraction
                + axis["normal"][0] * label_normal
            )
            label_y = (
                start[1]
                + (end[1] - start[1]) * label_fraction
                + axis["normal"][1] * label_normal
            )
            label_x = max(15, min(IMAGE_WIDTH - 15, label_x))
            label_y = max(15, min(IMAGE_HEIGHT - 15, label_y))
            drawing += _plate_generator_label_html(name, label_x, label_y)
        markers.append(
            f'<g class="{classes}" data-generator="{escape(name)}" '
            f'data-generator-kind="{kind}" data-generator-symbol="{symbol_key}"'
            f' data-lift-kind="{lift_kind}" data-time-shift="{phase_attribute}"'
            f'{order_attribute}>{drawing}</g>'
        )
    return (
        f'<svg class="plate-generator-overlay" '
        f'data-generator-overlay="{escape(record["id"])}" '
        f'viewBox="0 0 {IMAGE_WIDTH} {IMAGE_HEIGHT}" '
        'preserveAspectRatio="xMidYMid meet" aria-hidden="true" '
        'focusable="false">'
        + "".join(markers)
        + "</svg>"
    )


def _clock_power_html(order: int, power: int) -> str:
    exponent = "" if power == 1 else f"<sup>{power}</sup>"
    return (
        f'<span class="clock-power clock-power--{power}" '
        f'aria-label="C {order} to power {power}">'
        f'<var>C</var><sub>{order}</sub>{exponent}</span>'
    )


def _presentation_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    presentation = record["chaim_presentation"]
    rows = []
    for generator in presentation["generators"]:
        power = generator["clock_power"]
        rows.append(
            '<tr class="presentation-generator-row">'
            '<th scope="row"><span class="presentation-generator-identity">'
            f'<span class="generator-key">{escape(generator["generator"])}</span>'
            f'<span class="generator-geometry">{escape(generator["geometry"])}</span>'
            "</span></th>"
            f'<td class="presentation-colour-action" '
            f'data-clock-power="{power}" '
            f'data-fixed-cycle="{escape(generator["cycle_notation"])}" '
            f'data-source-cycle="{escape(generator["source_cycle_notation"])}">'
            f'{_clock_power_html(record["clock_order"], power)}</td>'
            f'<td class="presentation-time-action" data-time-shift="{escape(generator["time_shift"])}">'
            f'{escape(generator["time_shift_label"])}</td>'
            "</tr>"
        )
    rows_html = "\n".join(rows)
    palette = "".join(
        '<span class="presentation-colour">'
        f'<i style="--presentation-colour: {escape(PALETTE[index])}"></i>'
        f'{chr(ord("A") + index)}</span>'
        for index in range(record["clock_order"])
    )
    positive_step = fraction_label(Fraction(1, record["clock_order"]))
    cyclic_key = (
        '<p class="presentation-cyclic-key"><strong>Forward clock</strong> '
        f'{_clock_power_html(record["clock_order"], 1)} = '
        f'+{escape(positive_step)} period = '
        f'<code>{escape(presentation["clock_cycle"]["cycle_notation"])}</code>. '
        f'A row with Time +k/{record["clock_order"]} has Color '
        f'C<sub>{record["clock_order"]}</sub><sup>k</sup>: k forward ticks '
        f'modulo {record["clock_order"]}. C<sub>{record["clock_order"]}</sub>'
        '<sup>0</sup> is shown as “none.”</p>'
    )
    source_differences = [
        generator
        for generator in presentation["generators"]
        if generator["cycle_notation"] != generator["source_cycle_notation"]
    ]
    source_audit = ""
    if source_differences:
        source_kind = (
            "Book"
            if presentation["action_source"] == "book-canonical"
            else "Derived source"
        )
        source_rows = "".join(
            f'<li><span>{escape(generator["generator"])}</span> '
            f'<code>{escape(generator["source_cycle_notation"])}</code></li>'
            for generator in source_differences
        )
        source_audit = (
            '<details class="presentation-source-audit">'
            f'<summary>{source_kind} cycle labels</summary><ul>{source_rows}</ul>'
            '<p>The source letters are an independent simultaneous relabelling; '
            'they do not change the fixed phase colors above.</p></details>'
        )
    source_note = ""
    if presentation["action_source"] == "regular-cyclic-rule-extension":
        source_note = (
            '<p class="presentation-source-note">Cyclic extension: these clock powers '
            "come from the audited time shifts; the book does not print a "
            "composite-colour row.</p>"
        )
    elif source_differences:
        source_note = (
            '<p class="presentation-source-note">Clock normalization: A, B, … stay '
            "in forward phase order. The book’s independently lettered cycles are "
            "available in the source audit; the short-form orders are unchanged.</p>"
        )
    generator_names = ", ".join(
        generator["generator"] for generator in presentation["generators"]
    )
    return f"""
              <section class="group-presentation" aria-labelledby="{group_id}-presentation-title">
                <div class="presentation-heading">
                  <h4 id="{group_id}-presentation-title">Presentation</h4>
                  <p class="presentation-palette"><span>forward phase order</span>{palette}</p>
                </div>
                <table data-presentation="{group_id}">
                  <caption class="visually-hidden">Chaim’s named geometric generators with fixed-clock powers and directed time shifts for {group_id}</caption>
                  <thead><tr><th scope="col">Generator</th><th scope="col">Color</th><th scope="col">Time</th></tr></thead>
                  <tbody>{rows_html}</tbody>
                </table>
                {cyclic_key}
                <p class="presentation-relations"><strong>Relations</strong> <span>Γ = ⟨{escape(generator_names)} | {escape(presentation['relations'])}⟩</span></p>
                {source_note}
                {source_audit}
              </section>"""


def _excerpt_link(
    excerpt: dict[str, Any],
    excerpt_id: str,
    css_class: str,
    label_html: str,
    *,
    short_signature: bool = False,
) -> str:
    source_url = excerpt.get("source_url") or excerpt.get("source")
    if not source_url:
        raise ValueError(f"excerpt lacks a source URL: {excerpt_id}")
    viewer_url = f"book-excerpt.html?v={BOOK_EXCERPT_VIEWER_VERSION}&" + urlencode(
        {
            "image": excerpt["image"],
            "title": excerpt["title"],
            "context": excerpt["context"],
            "alt": excerpt["alt"],
            "source": source_url,
        }
    )
    short_attribute = " data-short-signature-excerpt" if short_signature else ""
    return (
        f'<a class="{css_class}" href="{escape(viewer_url)}" '
        f'data-printed-page="{excerpt["printed_page"]}" '
        f'data-pdf-page="{excerpt["pdf_page"]}" '
        f'data-book-excerpt="{escape(excerpt_id)}" '
        f'data-book-image="{escape(excerpt["image"])}" '
        f'data-book-title="{escape(excerpt["title"])}" '
        f'data-book-context="{escape(excerpt["context"])}" '
        f'data-book-alt="{escape(excerpt["alt"])}" '
        f'data-book-source="{escape(source_url)}"{short_attribute} '
        f'target="{BOOK_EXCERPT_TARGET}">{label_html}</a>'
    )


def _book_link(
    reference: dict[str, Any],
    css_class: str,
    label: str,
) -> str:
    excerpt = BOOK_EXCERPTS[reference["excerpt_key"]]
    resolved = {
        **excerpt,
        "source_url": reference["url"],
    }
    return _excerpt_link(
        resolved,
        excerpt["key"],
        css_class,
        escape(label),
    )


def _film_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    return f"""
              <figure class="clockwork-film" data-clockwork-player data-group-id="{group_id}">
                <div class="clockwork-stage" data-film-stage data-state="loading">
                  <canvas class="clockwork-canvas" id="{group_id}-film" width="1" height="1" role="img" aria-label="Animated clockwork action for {group_id}">JavaScript is needed for this film; the static coloured plate remains available below.</canvas>
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
              </figure>"""


def _space_groups_by_id() -> dict[str, dict[str, Any]]:
    payload = json.loads(SPACE_GROUP_DATA.read_text(encoding="utf-8"))
    groups = payload.get("groups", [])
    by_id = {record["id"]: record["space_group"] for record in groups}
    if len(groups) != 68 or len(by_id) != 68:
        raise ValueError("expected 68 uniquely identified space-group records")
    return by_id


def _plane_group_name_html(hm: str) -> str:
    number = PLANE_GROUP_NUMBER_BY_HM[hm]
    full_hm = PLANE_GROUP_FULL_HM[hm]
    short_alias = f" · {escape(hm)}" if full_hm != hm else ""
    return f"No. {number} {escape(full_hm)}{short_alias}"


def _term_help_html(label: str) -> str:
    """Render a non-latching hover definition."""

    help_text = TERM_HELP[label]
    return (
        f'<span class="term-help" aria-label="{escape(label)}: {escape(help_text)}">'
        f'<span class="term-help-label" aria-hidden="true">{escape(label)}</span>'
        f'<span class="term-help-copy" aria-hidden="true">{escape(help_text)}</span>'
        '</span>'
    )


def _clockwork_disambiguator_html(
    record: dict[str, Any],
    *,
    context: str,
) -> str:
    """Show the oriented spacetime name only where the colour name collides."""

    if record["id"] not in COLOUR_SIGNATURE_COLLISION_IDS:
        return ""
    symbol = record["symbol"]
    return (
        f'<span class="clockwork-disambiguator clockwork-disambiguator--{context}" '
        f'aria-label="Project-specific clockwork symbol {escape(symbol)}">'
        f'{clockwork_symbol_html(symbol)}</span>'
    )


def _short_form_support_html(record: dict[str, Any]) -> str:
    links: list[str] = []
    for step in record["book_audit"]["prime_chain"]:
        excerpt = step["short_signature_excerpt"]
        links.append(
            _excerpt_link(
                excerpt,
                f'short-form::{step["source_colour_group_id"]}',
                "short-form-support-link",
                (
                    f'C<sub>{step["index"]}</sub> layer '
                    f'{superscript_html(step["short_signature"])} · '
                    f'p. {step["printed_page"]}'
                ),
                short_signature=True,
            )
        )
    for conflict in record["signature_evidence"]["conflicts"]:
        excerpt = conflict.get("excerpt")
        if not excerpt:
            continue
        links.append(
            _excerpt_link(
                excerpt,
                f'conflict::{conflict.get("source_colour_group_id", record["id"])}',
                "short-form-support-link short-form-support-link--conflict",
                (
                    "conflicting row "
                    f'{superscript_html(conflict["printed_signature"])} · '
                    f'p. {excerpt["printed_page"]}'
                ),
                short_signature=True,
            )
        )
    if not links:
        return ""
    return (
        '<li class="short-form-support"><span class="other-name-category">'
        'Short-form evidence</span><span class="short-form-support-links">'
        + '<span aria-hidden="true"> · </span>'.join(links)
        + "</span></li>"
    )


def _other_names_html(record: dict[str, Any], space_group: dict[str, Any]) -> str:
    """Link exact catalog, plane-group, and height-lift identities."""

    group_id = escape(record["id"])
    parent_hm = record["parent"]["hm"]
    kernel_hm = record["kernel"]["hm"]
    parent_url = IUCR_PLANE_GROUP_URL.format(
        number=PLANE_GROUP_NUMBER_BY_HM[parent_hm]
    )
    kernel_url = IUCR_PLANE_GROUP_URL.format(
        number=PLANE_GROUP_NUMBER_BY_HM[kernel_hm]
    )
    space_number = space_group["it_number"]
    space_hm = _hm_html(space_group["hm_short"])
    fibrifold = FIBRIFOLD_BY_ID[record["id"]]
    fibrifold_orientation_note = ""
    if record["id"] in FIBRIFOLD_ENANTIOMORPHIC_IDS:
        fibrifold_orientation_note = (
            '<small class="fibrifold-orientation-note">Two orientations share this '
            'fibrifold name; the space-group name below selects this handed form.</small>'
        )
    primary_book_reference = next(
        reference
        for reference in record["book_audit"]["references"]
        if reference["role"] == "primary"
    )
    book_link = _book_link(
        primary_book_reference,
        "book-page-link",
        f"The Symmetries of Things · p. {primary_book_reference['printed_page']}",
    )
    mate_html = ""
    if record["complementary_skip_mate"]:
        mate_id = escape(record["complementary_skip_mate"])
        mate_html = (
            f'<li>{_term_help_html("Complementary forward skips")}<a href="#{mate_id}">{mate_id}</a></li>'
        )
    short_form_support = _short_form_support_html(record)
    parent_reference = (
        f'Plane group {_plane_group_name_html(parent_hm)} — '
        'International Tables for Crystallography'
    )
    space_reference = f'Space group No. {space_number} {space_hm} — UCL'
    return f"""
              <section class="other-names" aria-labelledby="{group_id}-other-names-title">
                <h4 id="{group_id}-other-names-title">Identifications</h4>
                <ul>
                  <li>{_term_help_html("Book type audit")}{book_link}</li>
                  <li>{_term_help_html("Catalog instance")}<a href="{escape(record['catalog_url'])}">{group_id}</a></li>
                  <li class="crystallographic-references" data-crystallographic-references="{group_id}"><span class="other-name-category">Crystallographic</span><span class="other-name-value"><a class="international-tables-reference" href="{escape(parent_url)}">{parent_reference}</a><a class="ucl-reference" href="{escape(space_group['ucl_reference_url'])}" target="_blank" rel="noopener">{space_reference}</a></span></li>
                  <li>{_term_help_html("Colour-fixing plane-group type K")}<a href="{escape(kernel_url)}">{_plane_group_name_html(kernel_hm)}</a></li>
                  <li>{_term_help_html("Conway fibrifold notation")}<span class="other-name-value"><span class="fibrifold-name" aria-label="{escape(fibrifold)}">{fibrifold_html(fibrifold)}</span>{fibrifold_orientation_note}</span></li>
                  <li>{_term_help_html("Height-lift space-group type")}<span class="other-name-value"><a href="space-group-correspondence.html#{group_id}">No. {space_number} {space_hm}</a><code>Hall {escape(space_group['hall'])}</code></span></li>
                  {short_form_support}
                  {mate_html}
                </ul>
              </section>"""


def _short_signature_heading_html(record: dict[str, Any]) -> tuple[str, str]:
    signature = record["book_color_signature"]
    signature_span = (
        f'<span class="book-color-signature" aria-label="Chaim notation '
        f'{escape(signature)}">{superscript_html(signature)}</span>'
    )
    evidence = record["signature_evidence"]
    excerpt = evidence.get("excerpt")
    if excerpt:
        excerpt_id = (
            evidence.get("source_colour_group_id")
            or excerpt.get("excerpt_key")
            or f'{record["id"]}-short-form'
        )
        signature_html = _excerpt_link(
            excerpt,
            f"short-form::{excerpt_id}",
            "short-signature-link",
            signature_span,
            short_signature=True,
        )
    else:
        signature_html = signature_span

    status_html = ""
    if evidence["status"] == "rule-extension":
        status_html = (
            '<p class="signature-evidence-note signature-evidence-note--derived">'
            f'<span>Derived C<sub>{record["clock_order"]}</sub> short form</span>'
            " — no literal book row</p>"
        )
    elif evidence["status"] == "book-internal-discrepancy":
        status_html = (
            '<p class="signature-evidence-note signature-evidence-note--discrepancy">'
            f'{escape(evidence["label"])}</p>'
        )
    return signature_html, status_html


def _entry_html(
    record: dict[str, Any],
    space_group: dict[str, Any],
) -> str:
    group_id = escape(record["id"])
    order = record["clock_order"]
    short_signature_html, signature_status_html = _short_signature_heading_html(record)
    clockwork_disambiguator = _clockwork_disambiguator_html(
        record,
        context="heading",
    )
    entry = f"""
      <li class="correspondence-item">
        <section class="correspondence-entry" id="{group_id}" aria-labelledby="{group_id}-title" data-clockwork-tabpanel data-clock-order="{order}">
          <header class="entry-header">
            <h3 id="{group_id}-title">{short_signature_html} <span class="group-id">{group_id}</span></h3>
            {signature_status_html}
            {clockwork_disambiguator}
          </header>

          <div class="entry-grid">
            <div class="entry-visuals">
              {_film_html(record)}
              <figure class="colour-plate">
                <div class="colour-plate-graphic">
                  <img src="{escape(record['image'])}" width="{IMAGE_WIDTH}" height="{IMAGE_HEIGHT}" loading="lazy" decoding="async" alt="{escape(record['image_alt'])}">
                  {_plate_generator_overlay_html(record)}
                </div>
                <figcaption>
                  <ol class="colour-key" aria-label="Colour and phase key">
                    {_phase_legend(record)}
                  </ol>
                </figcaption>
              </figure>
            </div>

            <div class="entry-copy">
              {_presentation_html(record)}
              {_other_names_html(record, space_group)}
            </div>
          </div>
        </section>
      </li>"""
    return "\n".join(line.rstrip() for line in entry.splitlines())


def _tab_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    signature = record["book_color_signature"]
    disambiguator = _clockwork_disambiguator_html(record, context="tab")
    aria_label = f"{signature}, colour action {group_id}"
    if record["id"] in COLOUR_SIGNATURE_COLLISION_IDS:
        aria_label += f"; project-specific clockwork symbol {record['symbol']}"
    return (
        f'<a class="clockwork-tab" id="tab-{group_id}" href="#{group_id}" '
        f'data-clockwork-tab data-panel-id="{group_id}" '
        f'aria-label="{escape(aria_label)}">'
        f'<span class="tab-signature">{superscript_html(signature)}</span>'
        f'{disambiguator}'
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
    fibrifold = fibrifold_html(FIBRIFOLD_BY_ID[record["id"]])
    return (
        f'<aside class="trivial-product" id="{group_id}" data-trivial-product '
        'aria-label="Trivial time group">'
        "<p><strong>C<sub>1</sub> product.</strong> "
        f"{orbifold} · {group_id} · κ = 0 · K = G</p>"
        '<div class="trivial-fibrifold">'
        f'{_term_help_html("Conway fibrifold notation")}'
        f'<span class="fibrifold-name" aria-label="{escape(FIBRIFOLD_BY_ID[record["id"]])}">{fibrifold}</span>'
        "</div>"
        "</aside>"
    )


def _directory_group_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    signature = superscript_html(record["book_color_signature"])
    disambiguator = _clockwork_disambiguator_html(record, context="directory")
    aria_label = (
        f'{record["book_color_signature"]}; {record["clock_order"]} colours; '
        f'open {group_id}'
    )
    if record["id"] in COLOUR_SIGNATURE_COLLISION_IDS:
        aria_label += f"; project-specific clockwork symbol {record['symbol']}"
    swatches = "".join(
        f'<span style="--directory-colour: {escape(residue["color"])}"></span>'
        for residue in record["phase_residues"]
    )
    return (
        f'<a class="directory-group" href="#{group_id}" data-directory-group="{group_id}" '
        f'aria-label="{escape(aria_label)}">'
        f'<span class="directory-signature book-color-signature">{signature}</span>'
        f'{disambiguator}'
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
    space_groups_by_id: dict[str, dict[str, Any]],
) -> str:
    orbifold = ORBIFOLD_BY_BASE[base]
    summary = WALLPAPER_SUMMARIES[base]
    lift_word = "lift" if len(rows) == 1 else "lifts"
    tabs = "\n".join(_tab_html(row) for row in rows)
    entries = "\n".join(
        _entry_html(
            row,
            space_groups_by_id[row["id"]],
        )
        for row in rows
    )
    family_class = "wallpaper-family" + (" is-empty" if not rows else "")
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
        contents = ""
    return f"""
    <section class="{family_class}" id="wallpaper-{escape(base)}" aria-labelledby="wallpaper-{escape(base)}-title" data-wallpaper-family>
      <header class="family-header">
        <h2 id="wallpaper-{escape(base)}-title"><span class="family-orbifold">{orbifold_html(orbifold)}</span> <span class="family-count">{len(rows)} nontrivial {lift_word}</span></h2>
        <p class="family-summary">{orbifold_html(summary)}</p>
      </header>
{contents}
      {_trivial_product_html(trivial_record)}
    </section>"""


def page_html(payload: dict[str, Any]) -> str:
    groups = payload["groups"]
    group_ids = {group["id"] for group in groups}
    if group_ids != set(FIBRIFOLD_BY_ID):
        missing = sorted(group_ids - set(FIBRIFOLD_BY_ID))
        extra = sorted(set(FIBRIFOLD_BY_ID) - group_ids)
        raise ValueError(
            f"fibrifold mapping mismatch; missing={missing}, extra={extra}"
        )
    space_groups_by_id = _space_groups_by_id()
    displayed_groups = [group for group in groups if group["clock_order"] > 1]
    trivial_groups = [group for group in groups if group["clock_order"] == 1]
    three_plus_colour_groups = [
        group for group in displayed_groups if group["clock_order"] >= 3
    ]
    if len(displayed_groups) != DISPLAYED_GROUP_COUNT:
        raise ValueError(f"expected {DISPLAYED_GROUP_COUNT} nontrivial display groups")
    if len(trivial_groups) != OMITTED_TRIVIAL_COUNT:
        raise ValueError(f"expected {OMITTED_TRIVIAL_COUNT} trivial product groups")
    colour_signature_fibres: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in displayed_groups:
        colour_signature_fibres[group["book_color_signature"]].append(group)
    repeated_colour_fibres = {
        signature: fibre
        for signature, fibre in colour_signature_fibres.items()
        if len(fibre) > 1
    }
    repeated_colour_ids = frozenset(
        group["id"]
        for fibre in repeated_colour_fibres.values()
        for group in fibre
    )
    if repeated_colour_ids != COLOUR_SIGNATURE_COLLISION_IDS:
        raise ValueError(
            "colour-signature collisions no longer match the complementary-skip pairs"
        )
    if any(len(fibre) != 2 for fibre in repeated_colour_fibres.values()):
        raise ValueError("expected every repeated colour signature to be a pair")
    if len({group["symbol"] for group in displayed_groups}) != len(displayed_groups):
        raise ValueError("clockwork symbols must disambiguate every display row")
    colour_class_count = len(colour_signature_fibres)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in displayed_groups:
        grouped[group["parent"]["hm"]].append(group)
    trivial_by_base = {group["parent"]["hm"]: group for group in trivial_groups}
    if set(trivial_by_base) != set(BASE_ORDER):
        raise ValueError("expected one trivial product for every wallpaper group")
    families = "\n".join(
        _family_html(
            base,
            grouped[base],
            trivial_by_base[base],
            space_groups_by_id,
        )
        for base in BASE_ORDER
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
        <a href="brownian.html">brownian</a>
        <a href="future-directions.html">Colours</a>
        <a href="color-pattern-catalog.html">Patterns</a>
        <a href="clockwork-coloring-correspondence.html" aria-current="page">Correspondence</a>
        <a href="space-group-correspondence.html">Space groups</a>
        <a href="dihedral-interactive.html">Dihedral</a>
        <a href="docs/orbifold_notation.html">Notation</a>
        <a href="data/clockwork-coloring-correspondence.json">Data</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>

  <main class="correspondence-page">
    <nav class="directory" aria-labelledby="page-title">
      <h1 id="page-title">Clockwork/coloring correspondence</h1>
      <p class="directory-legend">Colors follow one fixed clock: A = phase 0, B = phase 1/N, C = phase 2/N, and so on. C<sub>N</sub> = (ABC…) is one forward +1/N-period tick, so a row with Time +k/N has Color C<sub>N</sub><sup>k</sup>. Every action is a forward time skip; none reverses time. Raised numbers in the signature give colour-permutation orders, not time shifts.</p>
      <aside class="diagram-symbol-legend" aria-labelledby="diagram-symbol-legend-title">
        <h2 id="diagram-symbol-legend-title">Crystallographic generator symbols: visual index</h2>
        <p>Projected along the clock axis, these are the actual symbols used on the static 2D diagrams. The filled core shows the 2-, 3-, 4-, or 6-fold spatial order. For a forward skip τ, the screw subscript is <i>m</i> ≡ <i>n</i>τ (mod <i>n</i>) for a positive 1/<i>n</i>-turn and <i>m</i> ≡ −<i>n</i>τ (mod <i>n</i>) for the opposite turn, with 0 ≤ <i>m</i> &lt; <i>n</i>. Mirrored blades record spatial turn sense—not backward time.</p>
        {_diagram_symbol_legend_html()}
        <p class="diagram-symbol-note">The burgundy α, β, γ, … or P, Q, … beside a diagram symbol identifies its Generator row. The Color and Time columns state the same forward clock action directly.</p>
        <p class="diagram-symbol-sources">Notation: <a href="{IUCR_DIAGRAM_SYMBOLS_URL}" target="_blank" rel="noopener"><cite>International Tables for Crystallography</cite> projection symbols</a> · <a href="{UCL_P31C_DIAGRAM_URL}" target="_blank" rel="noopener">UCL P 3 1 c example</a>.</p>
      </aside>
      <aside class="notation-caveat" aria-labelledby="notation-caveat-title">
        <h2 id="notation-caveat-title">Notation</h2>
        <p>The displayed names use Chaim Goodman–Strauss’s coloured-orbifold notation. Across all {len(trivial_groups) + len(displayed_groups)} forward groups it gives {len(trivial_groups) + colour_class_count} cyclic plane-colouring classes. Four types leave the two orientations of the polar fibre unresolved: 442<sup>4</sup>/◦, 333<sup>3</sup>/◦, 632<sup>6</sup>/◦, and 632<sup>3</sup>/2222. These are four two-to-one fibres, not missing colourings; standard fibrifold notation also identifies each pair under fibre reversal. <a href="docs/orbifold_notation.html#uncovered-cases">Four uncovered cases ↗</a> · <a href="{HIERARCHY_CHIRALITY_URL}">hierarchy ↗</a></p>
      </aside>
      <aside class="directory-census" aria-label="Forward group count overview">
        <p><strong><span class="census-number">{len(trivial_groups)}</span> trivial groups</strong><span>Time is an independent direct-product factor.</span></p>
        <p><strong><span class="census-number">{len(displayed_groups)}</span> nontrivial groups</strong><span>Some spatial symmetries advance time phase.</span></p>
        <p><strong><span class="census-number">{len(three_plus_colour_groups)}</span> groups with 3 or more colours</strong><span>{_order_census_html(three_plus_colour_groups)}</span></p>
      </aside>
      <div class="directory-families">
        {directory}
      </div>
    </nav>

    <div class="correspondence-atlas" id="correspondences">
{families}
    </div>

    <section class="provenance" aria-labelledby="provenance-title">
      <h2 id="provenance-title">Data</h2>
      <p><a href="data/clockwork-coloring-correspondence.json">68-record JSON</a> · <a href="scripts/generate_clockwork_coloring_correspondence.py">generator</a> · <a href="scripts/tos_book_excerpt_specs.py">book-excerpt map</a> · <a href="{BOOK_ERRATA_URL}">errata</a> · SHA-256 <code>{escape(digest)}</code></p>
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


def expected_text_outputs(payload: dict[str, Any]) -> dict[Path, str]:
    return {
        DATA: data_text(payload),
        PAGE: page_html(payload),
    }


def expected_binary_outputs(payload: dict[str, Any]) -> dict[Path, bytes]:
    return {
        IMAGE_DIR / f"{group['id']}.webp": render_plate(group)
        for group in payload["groups"]
    }


def expected_outputs(payload: dict[str, Any]) -> tuple[dict[Path, str], dict[Path, bytes]]:
    return expected_text_outputs(payload), expected_binary_outputs(payload)


def check_outputs(
    payload: dict[str, Any],
    *,
    include_images: bool = True,
) -> list[Path]:
    stale: list[Path] = []
    for path, expected in expected_text_outputs(payload).items():
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            stale.append(path)
    if not include_images:
        return stale
    binary_outputs = expected_binary_outputs(payload)
    for path, expected in binary_outputs.items():
        if not path.exists() or path.read_bytes() != expected:
            stale.append(path)
    expected_images = set(binary_outputs)
    if IMAGE_DIR.exists():
        stale.extend(path for path in IMAGE_DIR.glob("*.webp") if path not in expected_images)
    return stale


def write_outputs(payload: dict[str, Any], *, include_images: bool = True) -> None:
    for path, text in expected_text_outputs(payload).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if not include_images:
        return
    for path, data in expected_binary_outputs(payload).items():
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
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="write or check JSON and HTML without rendering colour plates",
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
        validate_payload(payload)

    if args.check:
        stale = check_outputs(payload, include_images=not args.text_only)
        if stale:
            for path in stale:
                print(f"stale: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("clockwork/colouring correspondence: tracked outputs are current")
        return 0

    write_outputs(payload, include_images=not args.text_only)
    suffix = "JSON and HTML" if args.text_only else "JSON, HTML, and static colour plates"
    print(f"wrote 68 correspondence records and 51 displayed rows; outputs: {suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
