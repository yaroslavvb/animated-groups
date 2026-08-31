#!/usr/bin/env python3
"""Generate the cyclic-colouring to polar-space-group atlas.

The input is the checked-in 68-record clockwork/colouring correspondence.
For every planar operation ``(M, v, tau)`` this generator uses the height
lift

    (x, y, z) -> (M (x, y) + v, z + tau).

The resulting ordinary three-dimensional crystallographic groups are the 68
polar space-group types.  ``SPACE_GROUP_BY_ID`` is deliberately explicit:
the International Tables number, Hermann--Mauguin names, Schoenflies name,
Hall symbol, and setting choice are pinned data rather than a runtime spglib
dependency.

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
from fractions import Fraction
import hashlib
from html import escape
import io
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont

import generate_clockwork_coloring_correspondence as clockwork


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATA = ROOT / "data" / "clockwork-coloring-correspondence.json"
DATA = ROOT / "data" / "space-group-correspondence.json"
PAGE = ROOT / "space-group-correspondence.html"
IMAGE_DIR = ROOT / "output" / "space-groups"

STYLE_SRC = "space-group-correspondence.css?v=concise-catalog"
SCRIPT_SRC = "space-group-correspondence.js?v=compact-tabs"
SOURCE_SHA256 = "09229e1718947210c1c54f09cb5d7b31933f7557a83218711df4fd5723df9410"
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

# Audited human-facing catalogue targets.  CrystalSymmetry dates and attachment
# slugs are pinned because they are not safely derivable (No. 33 is ``33-3``;
# several diagram slugs carry a numeric suffix, and rhombohedral groups have
# separate axis choices).
CRYSTAL_SYMMETRY_POST_DATE_BY_NUMBER = {
    1: "2014/06/03",
    **{number: "2014/06/05" for number in (3, 4, 5)},
    **{number: "2014/06/06" for number in (6, 7)},
    8: "2014/06/10",
    9: "2014/06/11",
    25: "2014/07/06",
    26: "2014/07/09",
    27: "2014/07/10",
    **{number: "2014/07/11" for number in range(28, 33)},
    **{number: "2014/07/12" for number in range(33, 39)},
    **{number: "2014/07/14" for number in range(39, 45)},
    **{number: "2014/07/15" for number in (45, 46)},
    75: "2014/07/20",
    76: "2014/07/21",
    **{number: "2014/07/22" for number in (77, 78, 79)},
    80: "2014/07/23",
    **{number: "2014/07/31" for number in range(99, 103)},
    **{number: "2014/08/01" for number in range(103, 111)},
    **{number: "2014/08/05" for number in range(143, 147)},
    **{number: "2014/08/06" for number in range(156, 162)},
    **{number: "2014/08/07" for number in (*range(168, 174), *range(183, 187))},
}
CRYSTAL_SYMMETRY_DIAGRAM_BY_NUMBER = {
    1: "001-p1-2",
    3: "003-p2-2",
    4: "004-p21-2",
    5: "005-c2-2",
    6: "006-pm-2",
    7: "007-pc-2",
    8: "008-cm-2",
    9: "009-cc-2",
    25: "025-pmm2-3",
    26: "026-pmc21-2",
    27: "027-pcc2-2",
    28: "028-pma2",
    29: "029-pca21",
    30: "030-pnc2",
    31: "031-pmn21",
    32: "032-pba2",
    33: "033-pna21",
    34: "034-pnn2",
    35: "035-cmm2",
    36: "036-cmc21",
    37: "037-ccc2",
    38: "038-amm2",
    39: "039-aem2",
    40: "040-ama2",
    41: "041-aea2",
    42: "042-fmm2",
    43: "043-fdd2",
    44: "044-imm2",
    45: "045-iba2",
    46: "046-ima2",
    75: "075-p4",
    76: "076-p41",
    77: "077-p42",
    78: "078-p43",
    79: "079-i4",
    80: "080-i41",
    99: "099-p4mm",
    100: "100-p4bm",
    101: "101-p42cm",
    102: "102-p42nm",
    103: "103-p4cc",
    104: "104-p4nc",
    105: "105-p42mc",
    106: "106-p42bc",
    107: "107-i4mm",
    108: "108-i4cm",
    109: "109-i41md",
    110: "110-i41cd",
    143: "143-p3",
    144: "144-p31",
    145: "145-p32",
    146: "146-r3-hex",
    156: "156-p3m1",
    157: "157-p31m",
    158: "158-p3c1",
    159: "159-p31c",
    160: "160-r3m-hex",
    161: "161-r3c-hex",
    168: "168-p6",
    169: "169-p61",
    170: "170-p65",
    171: "171-p62",
    172: "172-p64",
    173: "173-p63",
    183: "183-p6mm",
    184: "184-p6cc",
    185: "185-p63cm",
    186: "186-p63mc",
}

POINT_GROUP_CATALOG_LINKS = {
    "1": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=1&num=1",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/1.pdf",
        "webmineral": "https://webmineral.com/crystal/Triclinic-Pedial.shtml",
        "smorf": "https://smorf.nl/crystals_triclinic.php?crystal=pv/triclinicpedion1",
    },
    "2": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=3&num=3",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/2.pdf",
        "webmineral": "https://webmineral.com/crystal/Monoclinic-Sphenoidal.shtml",
        "smorf": "https://smorf.nl/crystals_monoclinic.php?crystal=pv/monoclinicsphenoid1",
    },
    "m": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=6&num=4",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/m.pdf",
        "webmineral": "https://webmineral.com/crystal/Monoclinic-Domatic.shtml",
        "smorf": "https://smorf.nl/crystals_monoclinic.php?crystal=pv/monoclinicdoma1",
    },
    "mm2": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=25&num=7",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/mm2.pdf",
        "webmineral": "https://webmineral.com/crystal/Orthorhombic-Pyramidal.shtml",
        "smorf": "https://smorf.nl/crystals_orthorhombic.php?crystal=pv/rhombicpyramid",
    },
    "4": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=75&num=9",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/4.pdf",
        "webmineral": "https://webmineral.com/crystal/Tetragonal-Pyramidal.shtml",
        "smorf": "https://smorf.nl/crystals_tetragonal.php?crystal=pv/tetragonalpyramid1",
    },
    "4mm": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=99&num=13",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/4mm.pdf",
        "webmineral": "https://webmineral.com/crystal/Tetragonal-DitetragonalPyramidal.shtml",
        "smorf": "https://smorf.nl/crystals_tetragonal.php?crystal=pv/ditetragonalpyramid",
    },
    "3": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=143&num=16",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/3.pdf",
        "webmineral": "https://webmineral.com/crystal/Trigonal-Pyramidal.shtml",
        "smorf": "https://smorf.nl/crystals_trigonal.php?crystal=pv/trigonalpyramid",
    },
    "3m": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=156&num=19",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/3m.pdf",
        "webmineral": "https://webmineral.com/crystal/Trigonal-DitrigonalPyramidal.shtml",
        "smorf": "https://smorf.nl/crystals_trigonal.php?crystal=pv/ditrigonalpyramid",
    },
    "6": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=168&num=21",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/6.pdf",
        "webmineral": "https://webmineral.com/crystal/Hexagonal-Pyramidal.shtml",
        "smorf": "https://smorf.nl/crystals_hexagonal.php?crystal=pv/hexagonalpyramid",
    },
    "6mm": {
        "bilbao": "https://cryst.ehu.es/cgi-bin/rep/programs/sam/point.py?sg=183&num=25",
        "gsp": "https://github.com/LluisCasas/GSP/blob/main/6mm.pdf",
        "webmineral": "https://webmineral.com/crystal/Hexagonal-DihexagonalPyramidal.shtml",
        "smorf": "https://smorf.nl/crystals_hexagonal.php?crystal=pv/dihexagonalpyramid",
    },
}

EXTRA_CATALOG_IDS = (
    "crystal-symmetry-example",
    "crystal-symmetry-diagram",
    "iucr-space-group",
    "ucl-space-group",
    "bilbao-point-group",
    "aflow-prototypes",
    "gsp-point-group",
    "webmineral-crystal-class",
    "smorf-crystal-form",
    "gemmology-cdl",
    "iucr-plane-group",
    "jmol-sgsv",
    "crystallify",
)

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

# The full space-group Schoenflies symbols for the same 68 International
# Tables types.  These were independently rechecked against spglib 2.7.0; the
# generator keeps them pinned so building the site does not depend on spglib.
SCHOENFLIES_BY_IT_NUMBER: dict[int, str] = {
    1: "C1^1",
    3: "C2^1",
    4: "C2^2",
    5: "C2^3",
    6: "Cs^1",
    7: "Cs^2",
    8: "Cs^3",
    9: "Cs^4",
    25: "C2v^1",
    26: "C2v^2",
    27: "C2v^3",
    28: "C2v^4",
    29: "C2v^5",
    30: "C2v^6",
    31: "C2v^7",
    32: "C2v^8",
    33: "C2v^9",
    34: "C2v^10",
    35: "C2v^11",
    36: "C2v^12",
    37: "C2v^13",
    38: "C2v^14",
    39: "C2v^15",
    40: "C2v^16",
    41: "C2v^17",
    42: "C2v^18",
    43: "C2v^19",
    44: "C2v^20",
    45: "C2v^21",
    46: "C2v^22",
    75: "C4^1",
    76: "C4^2",
    77: "C4^3",
    78: "C4^4",
    79: "C4^5",
    80: "C4^6",
    99: "C4v^1",
    100: "C4v^2",
    101: "C4v^3",
    102: "C4v^4",
    103: "C4v^5",
    104: "C4v^6",
    105: "C4v^7",
    106: "C4v^8",
    107: "C4v^9",
    108: "C4v^10",
    109: "C4v^11",
    110: "C4v^12",
    143: "C3^1",
    144: "C3^2",
    145: "C3^3",
    146: "C3^4",
    156: "C3v^1",
    157: "C3v^2",
    158: "C3v^3",
    159: "C3v^4",
    160: "C3v^5",
    161: "C3v^6",
    168: "C6^1",
    169: "C6^2",
    170: "C6^3",
    171: "C6^4",
    172: "C6^5",
    173: "C6^6",
    183: "C6v^1",
    184: "C6v^2",
    185: "C6v^3",
    186: "C6v^4",
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


def _extra_catalog_links(
    source_record: dict[str, Any],
    *,
    number: int,
    hm_short: str,
    ucl_url: str,
) -> list[dict[str, str]]:
    """Return one audited, nonduplicated link per catalogue resource."""

    post_date = CRYSTAL_SYMMETRY_POST_DATE_BY_NUMBER[number]
    post_slug = "33-3" if number == 33 else str(number)
    diagram_slug = CRYSTAL_SYMMETRY_DIAGRAM_BY_NUMBER[number]
    point_group = _point_group(number)
    crystal_system = _crystal_system(number)
    point_links = POINT_GROUP_CATALOG_LINKS[point_group]
    parent_hm = source_record["parent"]["hm"]
    plane_number = clockwork.PLANE_GROUP_NUMBER_BY_HM[parent_hm]
    space_target = f"No. {number} {hm_short}"
    point_target = f"Point group {point_group}"

    links = [
        {
            "catalog_id": "crystal-symmetry-example",
            "catalog": "CrystalSymmetry worked example",
            "scope": "exact_space_group",
            "target": space_target,
            "url": (
                "https://crystalsymmetry.wordpress.com/"
                f"{post_date}/{post_slug}/"
            ),
        },
        {
            "catalog_id": "crystal-symmetry-diagram",
            "catalog": "CrystalSymmetry diagram",
            "scope": "exact_space_group",
            "target": space_target,
            "url": (
                "https://crystalsymmetry.wordpress.com/space-group-diagrams/"
                f"{diagram_slug}/"
            ),
        },
        {
            "catalog_id": "iucr-space-group",
            "catalog": "IUCr Volume A space-group table",
            "scope": "exact_space_group",
            "target": space_target,
            "url": (
                "https://onlinelibrary.wiley.com/iucr/itc/Ac/ch2o3v0001/"
                f"sgtable2o3o{number:03d}/"
            ),
        },
        {
            "catalog_id": "ucl-space-group",
            "catalog": "UCL space-group diagrams",
            "scope": "exact_space_group",
            "target": space_target,
            "url": ucl_url,
        },
        {
            "catalog_id": "bilbao-point-group",
            "catalog": "Bilbao Point Group Tables",
            "scope": "polar_point_group",
            "target": point_target,
            "url": point_links["bilbao"],
        },
        {
            "catalog_id": "aflow-prototypes",
            "catalog": "AFLOW crystal prototypes",
            "scope": "exact_space_group",
            "target": space_target,
            "url": f"https://aflow.org/p/{crystal_system}_spacegroup.html#sg{number}",
        },
        {
            "catalog_id": "gsp-point-group",
            "catalog": "GSP crystal morphology",
            "scope": "polar_point_group",
            "target": point_target,
            "url": point_links["gsp"],
        },
        {
            "catalog_id": "webmineral-crystal-class",
            "catalog": "Webmineral crystal class",
            "scope": "polar_point_group",
            "target": point_target,
            "url": point_links["webmineral"],
        },
        {
            "catalog_id": "smorf-crystal-form",
            "catalog": "Smorf crystal form",
            "scope": "polar_point_group",
            "target": point_target,
            "url": point_links["smorf"],
        },
        {
            "catalog_id": "gemmology-cdl",
            "catalog": "gemmology.dev CDL",
            "scope": "point_group_reference",
            "target": f"CDL point-group table · {point_group}",
            "url": "https://gemmology.dev/docs/cdl/#crystal-systems",
        },
        {
            "catalog_id": "iucr-plane-group",
            "catalog": "IUCr plane-group table",
            "scope": "parent_plane_group",
            "target": f"No. {plane_number} {parent_hm}",
            "url": clockwork.IUCR_PLANE_GROUP_URL.format(number=plane_number),
        },
        {
            "catalog_id": "jmol-sgsv",
            "catalog": "Jmol Space Group Visualizer",
            "scope": "manual_space_group_selection",
            "target": f"Select {space_target} manually",
            "url": "https://spacegroups.symotter.org/",
        },
        {
            "catalog_id": "crystallify",
            "catalog": "Crystallify",
            "scope": "manual_space_group_selection",
            "target": f"Select {space_target} manually",
            "url": "https://www.crystallify.com/",
        },
    ]
    if tuple(link["catalog_id"] for link in links) != EXTRA_CATALOG_IDS:
        raise AssertionError("extra catalogue order no longer matches its schema")
    urls = [link["url"] for link in links]
    if len(urls) != len(set(urls)):
        raise ValueError(f"duplicate extra catalogue URL for {source_record['id']}")
    return links


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


def _translation_with_height(operation: str, phase: str) -> str:
    """Rewrite a planar translation as a translation in the lifted cell."""

    match = re.fullmatch(r"([^ ]+)-cell translation (along|opposite) ([ab])", operation)
    if match:
        amount, direction, axis = match.groups()
        planar = f"{amount} {axis}" if direction == "along" else f"−{amount} {axis}"
    elif operation.startswith("Translation by "):
        planar = operation.removeprefix("Translation by ")
    elif operation == "Pure time step":
        planar = ""
    else:
        raise ValueError(f"unrecognized planar translation description: {operation}")
    pieces = [piece for piece in (planar, "" if phase == "0" else f"{phase} c") if piece]
    return "Translation by " + " + ".join(pieces)


def _lifted_generator_description(generator: dict[str, str]) -> str:
    """Describe one finite-cell generator after phase becomes height."""

    kind = generator["kind"]
    operation = generator["operation"]
    phase = generator["phase"]
    height = "" if phase == "0" else f"; height shift {phase}"
    if kind == "translation":
        return _translation_with_height(operation, phase)
    if kind == "rotation":
        turn = operation.replace(" rotation", "")
        motion = "rotation" if phase == "0" else "screw rotation"
        return f"{turn} {motion} about an axis parallel to the lift direction{height}"
    if kind in {"mirror", "glide"}:
        direction = ""
        match = re.search(r"axis direction ([0-9]+)$", operation)
        if match:
            direction = f", direction {match.group(1)}"
        motion = "Mirror reflection" if kind == "mirror" and phase == "0" else "Glide reflection"
        return f"{motion} in a vertical plane{direction}{height}"
    raise ValueError(f"unsupported lifted generator kind: {kind}")


Affine3 = tuple[tuple[tuple[int, int, int], ...], tuple[Fraction, Fraction, Fraction]]
R3_ID = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
AFFINE3_ID: Affine3 = (R3_ID, (Fraction(0), Fraction(0), Fraction(0)))


def _matrix3_multiply(
    left: tuple[tuple[int, int, int], ...],
    right: tuple[tuple[int, int, int], ...],
) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        tuple(sum(left[row][inner] * right[inner][column] for inner in range(3)) for column in range(3))
        for row in range(3)
    )


def _matrix3_vector(
    matrix: tuple[tuple[int, int, int], ...],
    vector: tuple[Fraction, Fraction, Fraction],
) -> tuple[Fraction, Fraction, Fraction]:
    return tuple(
        sum((Fraction(matrix[row][column]) * vector[column] for column in range(3)), Fraction(0))
        for row in range(3)
    )  # type: ignore[return-value]


def _compose_affine3(left: Affine3, right: Affine3) -> Affine3:
    left_matrix, left_translation = left
    right_matrix, right_translation = right
    moved = _matrix3_vector(left_matrix, right_translation)
    return (
        _matrix3_multiply(left_matrix, right_matrix),
        tuple(moved[index] + left_translation[index] for index in range(3)),
    )  # type: ignore[return-value]


def _inverse_affine3(value: Affine3) -> Affine3:
    matrix, translation = value
    a, b = matrix[0][0], matrix[0][1]
    c, d = matrix[1][0], matrix[1][1]
    determinant = a * d - b * c
    if determinant not in {-1, 1} or matrix[2] != (0, 0, 1):
        raise ValueError(f"unsupported lifted matrix: {matrix!r}")
    inverse = (
        (determinant * d, -determinant * b, 0),
        (-determinant * c, determinant * a, 0),
        (0, 0, 1),
    )
    moved = _matrix3_vector(inverse, translation)
    return inverse, tuple(-coordinate for coordinate in moved)  # type: ignore[return-value]


def _lifted_affine(operation: dict[str, Any]) -> Affine3:
    matrix = clockwork.matrix(operation)
    return (
        (
            (matrix[0][0], matrix[0][1], 0),
            (matrix[1][0], matrix[1][1], 0),
            (0, 0, 1),
        ),
        (
            clockwork.exact_fraction(operation["v"][0]),
            clockwork.exact_fraction(operation["v"][1]),
            clockwork.exact_fraction(operation["tau"]),
        ),
    )


def _presentation_seed_operations(source_record: dict[str, Any]) -> list[dict[str, Any]]:
    identity = (
        clockwork.M_ID,
        (Fraction(0), Fraction(0)),
        1,
        Fraction(0),
    )
    operations: list[dict[str, Any]] = []
    source_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for source_index, operation in enumerate(source_record["render"]["ops"]):
        key = clockwork.op_key(operation)
        if key == identity:
            continue
        matrix = clockwork.matrix(operation)
        translation = tuple(clockwork.exact_fraction(x) for x in operation["v"])
        determinant = clockwork.det2(matrix)
        if matrix == clockwork.M_ID:
            kind = "translation"
        elif determinant == 1:
            kind = "rotation"
        else:
            square_translation = (
                translation[0] + matrix[0][0] * translation[0] + matrix[0][1] * translation[1],
                translation[1] + matrix[1][0] * translation[0] + matrix[1][1] * translation[1],
            )
            kind = "mirror" if square_translation == (0, 0) else "glide"
        operations.append(
            {
                "source_index": source_index,
                "key": key,
                "matrix": matrix,
                "translation": translation,
                "phase_fraction": clockwork.exact_fraction(operation["tau"]),
                "kind": kind,
            }
        )
        source_by_key[key] = operation
    all_keys = {identity, *(operation["key"] for operation in operations)}
    seeds = clockwork._minimal_operation_generators(operations, all_keys)
    return [source_by_key[seed] for seed in seeds]


def _word_power(word: tuple[str, ...], exponent: int) -> tuple[str, ...]:
    return word * exponent


def _quotient_relators(template: str) -> list[tuple[str, tuple[str, ...], str, tuple[str, ...]]]:
    power = lambda name, exponent: (f"{name}{_superscript(exponent)}", (name,) * exponent, "1", ())
    commute = lambda left, right: (left + right, (left, right), right + left, (right, left))
    if template == "cyclic_2_x_4":
        return [power("A", 2), power("B", 4), commute("A", "B")]
    if template == "cyclic_2_x_dihedral_4":
        return [
            power("A", 2), power("B", 2), power("C", 2),
            ("(BC)⁴", _word_power(("B", "C"), 4), "1", ()),
            commute("A", "B"), commute("A", "C"),
        ]
    if template.startswith("cyclic_"):
        return [power("A", int(template.removeprefix("cyclic_")))]
    if template.startswith("elementary_2_"):
        count = int(template.rsplit("_", 1)[1])
        names = [chr(ord("A") + index) for index in range(count)]
        return [power(name, 2) for name in names] + [
            commute(names[left], names[right])
            for left in range(count)
            for right in range(left + 1, count)
        ]
    if template == "exceptional_16":
        return [
            power("A", 2), power("B", 4),
            ("(AB)⁴", _word_power(("A", "B"), 4), "1", ()),
            ("AB²", ("A", "B", "B"), "B²A", ("B", "B", "A")),
        ]
    if template in {"dihedral_4_reflections", "dihedral_3", "dihedral_6"}:
        order = {"dihedral_4_reflections": 4, "dihedral_3": 3, "dihedral_6": 6}[template]
        return [
            power("A", 2), power("B", 2),
            (f"(AB){_superscript(order)}", _word_power(("A", "B"), order), "1", ()),
        ]
    if template == "dihedral_4_rotation":
        return [
            power("A", 2), power("B", 4),
            ("(AB)²", _word_power(("A", "B"), 2), "1", ()),
        ]
    if template == "elementary_3_2":
        return [power("A", 3), power("B", 3), commute("A", "B")]
    if template == "exceptional_18":
        return [
            power("A", 2), power("B", 3),
            ("B(ABA)", ("B", "A", "B", "A"), "(ABA)B", ("A", "B", "A", "B")),
        ]
    raise ValueError(f"unsupported quotient presentation template: {template}")


def _superscript(value: int) -> str:
    table = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return str(value).translate(table)


def _translation_word(vector: tuple[int, int, int]) -> str:
    terms = []
    for name, exponent in zip(("a", "b", "c"), vector):
        if exponent == 0:
            continue
        terms.append(name if exponent == 1 else name + _superscript(exponent))
    return "".join(terms) or "1"


def _word_affine(word: tuple[str, ...], generators: dict[str, Affine3]) -> Affine3:
    result = AFFINE3_ID
    for name in word:
        result = _compose_affine3(result, generators[name])
    return result


def _lifted_relator(
    left_label: str,
    left_word: tuple[str, ...],
    right_label: str,
    right_word: tuple[str, ...],
    generators: dict[str, Affine3],
) -> str:
    left = _word_affine(left_word, generators)
    right = _word_affine(right_word, generators)
    difference = _compose_affine3(left, _inverse_affine3(right))
    if difference[0] != R3_ID or any(value.denominator != 1 for value in difference[1]):
        raise ValueError(f"cell relation does not lift to a lattice translation: {left_label}={right_label}")
    translation = tuple(int(value) for value in difference[1])
    factor = _translation_word(translation)
    lifted_right = factor if right_label == "1" else (right_label if factor == "1" else f"{factor} · {right_label}")
    return f"{left_label} = {lifted_right}"


def _space_group_presentation(source_record: dict[str, Any]) -> dict[str, Any] | None:
    """Compute a complete extension presentation relative to the displayed cell."""

    if source_record["clock_order"] == 1:
        return None
    source = source_record.get("cell_action_presentation")
    if not source or source.get("relations") in {None, "omitted"}:
        raise ValueError(f"missing source presentation for {source_record['id']}")
    seed_operations = _presentation_seed_operations(source_record)
    point_generators = source["generators"]
    if len(seed_operations) != len(point_generators):
        raise ValueError(f"presentation seed mismatch in {source_record['id']}")
    names = [generator["name"] for generator in point_generators]
    if names != [chr(ord("A") + index) for index in range(len(names))]:
        raise ValueError(f"nonconsecutive presentation generators in {source_record['id']}")

    affine_generators = {
        name: _lifted_affine(operation)
        for name, operation in zip(names, seed_operations)
    }
    displayed_generators = [
        {"name": "a", "operation": "Unit translation along a"},
        {"name": "b", "operation": "Unit translation along b"},
        {"name": "c", "operation": "Unit translation along the lift axis"},
        *[
            {
                "name": generator["name"],
                "operation": _lifted_generator_description(generator),
            }
            for generator in point_generators
        ],
    ]

    lattice_relations = ["ab = ba", "ac = ca", "bc = cb"]
    action_relations: list[str] = []
    for name in names:
        matrix = affine_generators[name][0]
        images = []
        for axis_index in range(3):
            image = tuple(matrix[row][axis_index] for row in range(3))
            images.append(_translation_word(image))
        action_relations.append(
            f"{name}(a,b,c){name}⁻¹ = ({','.join(images)})"
        )
    cell_relations = [
        _lifted_relator(left_label, left_word, right_label, right_word, affine_generators)
        for left_label, left_word, right_label, right_word in _quotient_relators(source["template"])
    ]
    return {
        "relative_to": "displayed unit cell",
        "quotient": "G/Λ₃",
        "quotient_order": source["quotient_order"],
        "template": source["template"],
        "generators": displayed_generators,
        "relations": {
            "lattice": lattice_relations,
            "action": action_relations,
            "cell": cell_relations,
        },
    }


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
        ucl_url = f"{UCL_SPACE_GROUP_BASE}/{ucl_page}"
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
            "book_color_signature": source_record["book_color_signature"],
            "clock_order": source_record["clock_order"],
            "cyclic_group": source_record["cyclic_group"],
            "phase_residues": source_record["phase_residues"],
            "phase_profile": source_record["phase_profile"],
            "cell_action_presentation": source_record["cell_action_presentation"],
            "space_group_presentation": _space_group_presentation(source_record),
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
                "schoenflies": SCHOENFLIES_BY_IT_NUMBER[number],
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
                    f"Space–time lift diagram for {group_id} and polar space group "
                    f"No. {number} {hm_short}; exact clock phases form stacked "
                    "sheets in vertical time through one clock period."
                ),
                "ucl_reference_url": ucl_url,
                "extra_links": _extra_catalog_links(
                    source_record,
                    number=number,
                    hm_short=hm_short,
                    ucl_url=ucl_url,
                ),
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
            "schema_version": 5,
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
            "mapping_database": (
                "Pinned spglib 2.6.0 space-group type results; naming fields "
                "independently rechecked against spglib 2.7.0"
            ),
            "construction": "Embed (M, v, τ) as (diag(M, 1), (v, τ)); cyclic phase becomes fractional height along the new z coordinate.",
            "scope_caveat": SCOPE_CAVEAT,
            "image_size": [IMAGE_WIDTH, IMAGE_HEIGHT],
            "image_note": "Space–time preview sheets place every operation at its exact cyclic phase in vertical time, repeat phase zero after one clock period, and reuse the colouring palette only to trace the height lift; colour is not additional crystallographic structure in the 3D group.",
            "external_reference": "Jeremy K. Cockcroft, A Hypertext Book of Crystallographic Space Group Diagrams and Tables, UCL/Birkbeck College, 1997-1999.",
            "external_reference_index": f"{UCL_SPACE_GROUP_BASE}/sgp.htm",
            "external_reference_cache_policy": "The project does not redistribute UCL pages or images because their published end-user licence prohibits Internet distribution; hover cards reuse locally generated project plates.",
            "extra_catalog_count": len(EXTRA_CATALOG_IDS),
            "polar_it_numbers": sorted(POLAR_IT_NUMBERS),
            "family_counts": {base: family_counts[base] for base in BASE_ORDER},
        },
        "groups": records,
    }


def validate_payload(payload: dict[str, Any]) -> None:
    meta = payload.get("meta", {})
    if meta.get("schema_version") != 5:
        raise ValueError("expected space-group correspondence schema 5")
    if meta.get("scope_caveat") != SCOPE_CAVEAT:
        raise ValueError("scope caveat is missing or changed")
    if meta.get("extra_catalog_count") != len(EXTRA_CATALOG_IDS):
        raise ValueError("extra catalogue count is missing or changed")
    if set(CRYSTAL_SYMMETRY_POST_DATE_BY_NUMBER) != POLAR_IT_NUMBERS:
        raise ValueError("CrystalSymmetry post mapping must cover the 68 polar types")
    if set(CRYSTAL_SYMMETRY_DIAGRAM_BY_NUMBER) != POLAR_IT_NUMBERS:
        raise ValueError("CrystalSymmetry diagram mapping must cover the 68 polar types")
    expected_point_groups = {label for _, label in POINT_GROUP_BY_RANGE}
    if set(POINT_GROUP_CATALOG_LINKS) != expected_point_groups:
        raise ValueError("point-group catalogue mapping must cover all polar classes")
    if len(EXTRA_CATALOG_IDS) != len(set(EXTRA_CATALOG_IDS)):
        raise ValueError("extra catalogue IDs must be unique")
    if set(SCHOENFLIES_BY_IT_NUMBER) != POLAR_IT_NUMBERS:
        raise ValueError("Schoenflies map must cover exactly the 68 polar types")
    if len(set(SCHOENFLIES_BY_IT_NUMBER.values())) != len(POLAR_IT_NUMBERS):
        raise ValueError("Schoenflies symbols must identify 68 distinct types")
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
        if actual.get("schoenflies") != SCHOENFLIES_BY_IT_NUMBER[actual["it_number"]]:
            raise ValueError(f"incorrect Schoenflies symbol for {group['id']}")
        if group["parent"]["hm"] not in BASE_ORDER:
            raise ValueError(f"unknown wallpaper family for {group['id']}")
        expected_signature = clockwork.book_color_signature(
            group["id"],
            group["parent"]["orbifold"],
            group["tos_notation"],
            group["clock_order"],
        )
        if group.get("book_color_signature") != expected_signature:
            raise ValueError(f"incorrect short colour signature for {group['id']}")
        if group["lift_operations"] != _lift_operations(group["render"]):
            raise ValueError(f"incorrect lifted operations for {group['id']}")
        expected_presentation = _space_group_presentation(group)
        if group.get("space_group_presentation") != expected_presentation:
            raise ValueError(f"incorrect space-group presentation for {group['id']}")
        expected_links = _extra_catalog_links(
            group,
            number=actual["it_number"],
            hm_short=actual["hm_short"],
            ucl_url=actual["ucl_reference_url"],
        )
        if actual.get("extra_links") != expected_links:
            raise ValueError(f"incorrect extra catalogue links for {group['id']}")
        links = actual["extra_links"]
        if tuple(link["catalog_id"] for link in links) != EXTRA_CATALOG_IDS:
            raise ValueError(f"incorrect extra catalogue order for {group['id']}")
        urls = [link["url"] for link in links]
        if len(urls) != len(set(urls)):
            raise ValueError(f"duplicate extra catalogue URL for {group['id']}")
        if any(not link["url"].startswith(("http://", "https://")) for link in links):
            raise ValueError(f"invalid extra catalogue URL for {group['id']}")
        numbers.append(actual["it_number"])
    if len(set(numbers)) != 68 or set(numbers) != POLAR_IT_NUMBERS:
        raise ValueError("space-group numbers are not the 68 polar types")


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    value = hex_colour.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _mix(colour: tuple[int, int, int], other: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round((1 - amount) * left + amount * right) for left, right in zip(colour, other))  # type: ignore[return-value]


def _fractional_planar_site(
    record: dict[str, Any], operation: dict[str, Any]
) -> tuple[float, float]:
    base_x, base_y = record["render"]["base"]
    matrix = operation["M"]
    x = matrix[0][0] * base_x + matrix[0][1] * base_y + operation["v"][0]
    y = matrix[1][0] * base_x + matrix[1][1] * base_y + operation["v"][1]
    return x % 1.0, y % 1.0


def _preview_phase_index(record: dict[str, Any], operation: dict[str, Any]) -> int:
    """Return the exact cyclic residue represented by an operation's height."""

    order = int(record["clock_order"])
    scaled = float(operation["tau"]) * order
    residue = round(scaled)
    if not math.isclose(scaled, residue, abs_tol=1e-8):
        raise ValueError(
            f"non-cyclic preview height for {record['id']}: {operation['tau']}"
        )
    return residue % order


PREVIEW_LATTICE_SHIFTS = (
    (0, 0),
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
)


def _height_lift_preview_layout(record: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic phase sheets and tiled sites for the preview plate."""

    order = int(record["clock_order"])
    layers = [
        {
            "phase": Fraction(index, order),
            "phase_index": index,
            "closure": False,
            "colour": PALETTE[index],
        }
        for index in range(order)
    ]
    layers.append(
        {
            "phase": Fraction(1),
            "phase_index": 0,
            "closure": True,
            "colour": PALETTE[0],
        }
    )

    sites: list[dict[str, Any]] = []
    for operation_index, operation in enumerate(record["render"]["ops"]):
        phase_index = _preview_phase_index(record, operation)
        u, v = _fractional_planar_site(record, operation)
        for shift_u, shift_v in PREVIEW_LATTICE_SHIFTS:
            site = {
                "u": u + shift_u,
                "v": v + shift_v,
                "phase": Fraction(phase_index, order),
                "phase_index": phase_index,
                "closure": False,
                "lattice_shift": (shift_u, shift_v),
                "neighbor": (shift_u, shift_v) != (0, 0),
                "colour": PALETTE[phase_index],
                "operation": operation,
                "operation_index": operation_index,
            }
            sites.append(site)
            if phase_index == 0:
                closure_site = dict(site)
                closure_site["phase"] = Fraction(1)
                closure_site["closure"] = True
                sites.append(closure_site)
    return {"layers": layers, "sites": sites}


def _preview_camera(record: dict[str, Any]) -> dict[str, Any]:
    """Choose an orientation-preserving view that avoids edge-on base vectors."""

    basis = record["render"]["basis"]
    vectors = [
        (float(basis[index][0]), float(basis[index][1]))
        for index in (0, 1)
    ]
    best: tuple[float, int, tuple[float, float], tuple[float, float]] | None = None
    for degrees in range(0, 180, 15):
        radians = math.radians(degrees)
        horizontal = (math.cos(radians), math.sin(radians))
        depth = (-horizontal[1], horizontal[0])
        scores = [
            abs(vector[0] * horizontal[0] + vector[1] * horizontal[1])
            / max(math.hypot(*vector), 1e-8)
            for vector in vectors
        ]
        candidate = (min(scores), -degrees, horizontal, depth)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    if best is None:  # pragma: no cover - the candidate range is nonempty
        raise AssertionError("preview camera search produced no candidates")
    score, negative_degrees, horizontal, depth = best
    return {
        "angle_degrees": -negative_degrees,
        "horizontal": horizontal,
        "depth": depth,
        "minimum_horizontal_score": score,
    }


def _projection(record: dict[str, Any]) -> tuple[Any, Any]:
    basis = record["render"]["basis"]
    a = (float(basis[0][0]), float(basis[0][1]))
    b = (float(basis[1][0]), float(basis[1][1]))
    longest = max(math.hypot(*a), math.hypot(*b), 1e-8)
    a = (a[0] / longest, a[1] / longest)
    b = (b[0] / longest, b[1] / longest)

    camera = _preview_camera(record)
    horizontal = camera["horizontal"]
    depth = camera["depth"]

    def raw(u: float, v: float, w: float) -> tuple[float, float]:
        x = u * a[0] + v * b[0]
        y = u * a[1] + v * b[1]
        across = x * horizontal[0] + y * horizontal[1]
        away = x * depth[0] + y * depth[1]
        return across, 0.38 * away - 1.16 * w

    spatial_extent = (-0.42, 1.42)
    corners = [
        raw(u, v, w)
        for u in spatial_extent
        for v in spatial_extent
        for w in (0.0, 1.0)
    ]
    min_x = min(point[0] for point in corners)
    max_x = max(point[0] for point in corners)
    min_y = min(point[1] for point in corners)
    max_y = max(point[1] for point in corners)
    left = 28 * ANTIALIAS
    right = (IMAGE_WIDTH - 142) * ANTIALIAS
    top = 24 * ANTIALIAS
    bottom = (IMAGE_HEIGHT - 142) * ANTIALIAS
    usable_width = right - left
    usable_height = bottom - top
    scale = min(
        usable_width / max(max_x - min_x, 1e-8),
        usable_height / max(max_y - min_y, 1e-8),
    )
    offset_x = left + (usable_width - scale * (max_x - min_x)) / 2 - scale * min_x
    offset_y = top + (usable_height - scale * (max_y - min_y)) / 2 - scale * min_y

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
    background = (249, 247, 241)
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    project, scale = _projection(record)
    layout = _height_lift_preview_layout(record)
    sheet_extent = (-0.42, 1.42)
    rail_colour = (191, 198, 194)
    grid_colour = (153, 164, 159)
    cell_colour = (70, 91, 83)

    # Vertical rails make the new coordinate unmistakable without implying a
    # trajectory for any one motif.
    for u, v in ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)):
        _draw_dashed_line(
            draw,
            project(u, v, 0.0),
            project(u, v, 1.0),
            rail_colour,
            max(1, ANTIALIAS),
            3.2 * ANTIALIAS,
        )

    # Draw one exact wallpaper sheet per cyclic residue.  The final outline is
    # phase zero repeated at t/T=1, making periodic closure visible.
    for layer in layout["layers"]:
        w = float(layer["phase"])
        corners = [
            project(u, v, w)
            for u, v in (
                (sheet_extent[0], sheet_extent[0]),
                (sheet_extent[1], sheet_extent[0]),
                (sheet_extent[1], sheet_extent[1]),
                (sheet_extent[0], sheet_extent[1]),
            )
        ]
        layer_colour = _rgb(layer["colour"])
        if layer["closure"]:
            for index, start in enumerate(corners):
                _draw_dashed_line(
                    draw,
                    start,
                    corners[(index + 1) % len(corners)],
                    _mix(layer_colour, background, 0.34),
                    max(2, ANTIALIAS),
                    4.2 * ANTIALIAS,
                )
        else:
            draw.polygon(corners, fill=_mix(layer_colour, background, 0.91))
            draw.line(
                corners + [corners[0]],
                fill=_mix(layer_colour, background, 0.50),
                width=max(2, ANTIALIAS),
                joint="curve",
            )
        for coordinate in (0.0, 1.0):
            for start, end in (
                ((coordinate, sheet_extent[0], w), (coordinate, sheet_extent[1], w)),
                ((sheet_extent[0], coordinate, w), (sheet_extent[1], coordinate, w)),
            ):
                draw.line(
                    (*project(*start), *project(*end)),
                    fill=_mix(grid_colour, background, 0.28 if layer["closure"] else 0.48),
                    width=max(1, ANTIALIAS),
                )
        main_cell = [
            project(u, v, w)
            for u, v in ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
        ]
        draw.line(
            main_cell + [main_cell[0]],
            fill=_mix(cell_colour, background, 0.30 if layer["closure"] else 0.10),
            width=max(2, ANTIALIAS),
            joint="curve",
        )

    operations = record["render"]["ops"]
    core_per_layer = max(1, len(operations) // int(record["clock_order"]))
    motif_scale = 1.05 if core_per_layer <= 2 else 0.82 if core_per_layer <= 4 else 0.68
    motif = tuple(
        (motif_scale * x, motif_scale * y)
        for x, y in (
            (-0.060, -0.045), (0.055, -0.070), (0.025, -0.005),
            (0.073, 0.050), (-0.020, 0.037),
        )
    )
    outline = (38, 51, 47)
    site_rows = []
    for site_index, site in enumerate(layout["sites"]):
        if not (
            sheet_extent[0] - 0.08 <= site["u"] <= sheet_extent[1] + 0.08
            and sheet_extent[0] - 0.08 <= site["v"] <= sheet_extent[1] + 0.08
        ):
            continue
        w = float(site["phase"])
        centre = project(site["u"], site["v"], w)
        site_rows.append((centre[1], site_index, site, centre))
    site_rows.sort(key=lambda row: (row[0], row[1]))

    for _, _, site, centre in site_rows:
        u, v, w = site["u"], site["v"], float(site["phase"])
        operation = site["operation"]
        matrix = operation["M"]
        points = []
        for local_x, local_y in motif:
            du = matrix[0][0] * local_x + matrix[0][1] * local_y
            dv = matrix[1][0] * local_x + matrix[1][1] * local_y
            points.append(project(u + du, v + dv, w))
        base_colour = _rgb(site["colour"])
        if site["closure"]:
            draw.line(
                points + [points[0]],
                fill=_mix(base_colour, background, 0.12 if not site["neighbor"] else 0.58),
                width=max(2, ANTIALIAS),
                joint="curve",
            )
        else:
            fill = _mix(base_colour, background, 0.58) if site["neighbor"] else base_colour
            edge = _mix(outline, background, 0.50) if site["neighbor"] else outline
            draw.polygon(points, fill=fill)
            draw.line(points + [points[0]], fill=edge, width=max(2, ANTIALIAS), joint="curve")
        marker = points[1]
        if not site["closure"] and not site["neighbor"]:
            marker_radius = max(1.8 * ANTIALIAS, 0.010 * scale)
            draw.ellipse(
                (marker[0] - marker_radius, marker[1] - marker_radius,
                 marker[0] + marker_radius, marker[1] + marker_radius),
                fill=background,
                outline=outline,
                width=max(1, ANTIALIAS),
            )

    # Keep the explanatory ruler above the viewer's bottom loading prompt.
    axis_x = (IMAGE_WIDTH - 62) * ANTIALIAS
    axis_top = 45 * ANTIALIAS
    axis_bottom = 306 * ANTIALIAS
    axis_colour = (42, 59, 53)
    draw.line(
        (axis_x, axis_bottom, axis_x, axis_top),
        fill=axis_colour,
        width=3 * ANTIALIAS,
    )
    draw.polygon(
        (
            (axis_x, axis_top - 9 * ANTIALIAS),
            (axis_x - 5 * ANTIALIAS, axis_top + 1 * ANTIALIAS),
            (axis_x + 5 * ANTIALIAS, axis_top + 1 * ANTIALIAS),
        ),
        fill=axis_colour,
    )
    font = ImageFont.load_default(size=11 * ANTIALIAS)
    small_font = ImageFont.load_default(size=9 * ANTIALIAS)
    draw.text(
        ((IMAGE_WIDTH - 107) * ANTIALIAS, 14 * ANTIALIAS),
        "TIME  t/T",
        fill=axis_colour,
        font=font,
    )
    order = int(record["clock_order"])
    for index in range(order + 1):
        y = axis_bottom - (axis_bottom - axis_top) * index / order
        phase_index = index % order
        colour = _rgb(PALETTE[phase_index])
        draw.line(
            (axis_x - 9 * ANTIALIAS, y, axis_x + 5 * ANTIALIAS, y),
            fill=axis_colour,
            width=max(2, ANTIALIAS),
        )
        radius = 4 * ANTIALIAS
        draw.ellipse(
            (axis_x - radius, y - radius, axis_x + radius, y + radius),
            fill=background if index == order else colour,
            outline=colour,
            width=max(2, ANTIALIAS),
        )
        if index == 0:
            label = "0"
        elif index == order:
            label = "1 = 0"
        else:
            common = math.gcd(index, order)
            label = f"{index // common}/{order // common}"
        draw.text(
            (axis_x + 10 * ANTIALIAS, y - 5 * ANTIALIAS),
            label,
            fill=axis_colour,
            font=small_font,
        )

    image = image.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", lossless=True, method=6)
    return buffer.getvalue()


def _hm_html(symbol: str) -> str:
    escaped = escape(symbol)
    return re.sub(r"_([0-9]+)", r"<sub>\1</sub>", escaped)


def _presentation_html(record: dict[str, Any]) -> str:
    full_presentation = record["space_group_presentation"]
    quotient_presentation = record["cell_action_presentation"]
    if not full_presentation:
        raise ValueError(f"missing displayed presentation for {record['id']}")
    if not quotient_presentation or quotient_presentation.get("relations") in {None, "omitted"}:
        raise ValueError(f"missing displayed quotient presentation for {record['id']}")
    lifted_generators = {
        generator["name"]: generator
        for generator in full_presentation["generators"]
        if generator["name"] not in {"a", "b", "c"}
    }
    quotient_names = [
        generator["name"] for generator in quotient_presentation["generators"]
    ]
    if list(lifted_generators) != quotient_names:
        raise ValueError(f"lifted/quotient generator mismatch for {record['id']}")
    rows = "\n".join(
        "<tr class=\"presentation-generator-row\">"
        f"<th scope=\"row\"><span class=\"generator-key\">{escape(generator['name'])}</span></th>"
        f"<td>{escape(generator['operation'])}</td>"
        "</tr>"
        for generator in lifted_generators.values()
    )
    names = ", ".join(quotient_names)
    group_id = escape(record["id"])
    return f"""
                <section class="space-group-presentation" aria-labelledby="{group_id}-presentation-title">
                  <h4 id="{group_id}-presentation-title">Presentation</h4>
                  <table data-space-presentation="{group_id}">
                    <caption class="visually-hidden">Geometric generators modulo full-cell translations for space group {_hm_html(record['space_group']['hm_short'])}</caption>
                    <tbody>
                      {rows}
                    </tbody>
                  </table>
                  <p class="presentation-relations"><strong>Relations</strong> <span>G/Λ = ⟨{escape(names)} | {escape(quotient_presentation['relations'])}⟩</span></p>
                </section>"""


def _base_group_html(record: dict[str, Any], *, anchor: bool = False) -> str:
    group_id = escape(record["id"])
    space_group = record["space_group"]
    id_attribute = f' id="{group_id}"' if anchor else ""
    return f"""
                <dl class="base-group"{id_attribute}>
                  <dt>Base group</dt>
                  <dd><span class="base-orbifold">{clockwork.orbifold_html(record['parent']['orbifold'])}</span> <span aria-hidden="true">·</span> <a class="base-group-link" href="{escape(space_group['ucl_reference_url'])}" target="_blank" rel="noopener">{_hm_html(space_group['hm_short'])}</a></dd>
                </dl>"""


def _entry_html(
    record: dict[str, Any],
    trivial_record: dict[str, Any],
    family_ordinal: int,
) -> str:
    group_id = escape(record["id"])
    space_group = record["space_group"]
    reference_url = escape(space_group["ucl_reference_url"])
    catalog_url = escape(record["catalog_url"])
    signature = record["book_color_signature"]
    return f"""
          <article class="space-entry" id="{group_id}" data-space-tabpanel>
            <div class="entry-pair">
              <figure class="colouring-card">
                <a class="colouring-catalog-link" href="{catalog_url}" target="_blank" rel="noopener" aria-label="{escape(signature)}; open colouring in catalog"><img src="{escape(record['image'])}" alt="{escape(record['image_alt'])}" width="720" height="420" loading="lazy" decoding="async"><span>Colouring ↗</span></a>
              </figure>
              <section class="space-group-summary" aria-labelledby="{group_id}-space-name">
                <h3 id="{group_id}-space-name" class="space-group-name">{_hm_html(space_group['hm_short'])}</h3>
                <a class="ucl-link" href="{reference_url}" target="_blank" rel="noopener" aria-describedby="ucl-credit">UCL space-group page</a>
{_base_group_html(trivial_record, anchor=family_ordinal == 1)}
{_presentation_html(record)}
              </section>
            </div>
          </article>"""


def _base_only_html(record: dict[str, Any]) -> str:
    return f"""
      <div class="base-only-entry">
        <section class="space-group-summary" aria-label="Base group">
{_base_group_html(record, anchor=True)}
        </section>
      </div>"""


def _family_html(
    base: str,
    rows: list[dict[str, Any]],
    trivial_record: dict[str, Any],
) -> str:
    tabs = "\n".join(
        f'<a id="tab-{escape(record["id"])}" href="#{escape(record["id"])}" '
        f'class="space-tab" data-space-tab data-panel-id="{escape(record["id"])}" '
        f'aria-label="{escape(record["book_color_signature"])}; colour action {escape(record["id"])}">'
        f'<span class="tab-signature book-color-signature">{clockwork.superscript_html(record["book_color_signature"])}</span>'
        f'<span class="tab-meta">{escape(record["id"])} · C<sub>{record["clock_order"]}</sub></span></a>'
        for record in rows
    )
    entries = "\n".join(
        _entry_html(record, trivial_record, index)
        for index, record in enumerate(rows, 1)
    )
    lift_word = "lift" if len(rows) == 1 else "lifts"
    family_class = "wallpaper-family space-family" + (" is-empty" if not rows else "")
    if rows:
        contents = f"""
      <div class="space-tabs" data-space-tabs>
        <nav class="space-tabbar" data-space-tablist aria-label="Nontrivial cyclic lifts over orbifold {escape(ORBIFOLD_BY_BASE[base])}">
          {tabs}
        </nav>
        <div class="space-panels">
{entries}
        </div>
      </div>"""
    else:
        contents = _base_only_html(trivial_record)
    return f"""
    <section class="{family_class}" id="wallpaper-{escape(base)}" data-wallpaper-family aria-labelledby="wallpaper-{escape(base)}-title">
      <header class="family-header">
        <h2 id="wallpaper-{escape(base)}-title"><span class="family-orbifold">{clockwork.orbifold_html(ORBIFOLD_BY_BASE[base])}</span> <span class="family-count">{len(rows)} {lift_word}</span></h2>
      </header>
{contents}
    </section>"""


def _directory_family_html(base: str, rows: list[dict[str, Any]]) -> str:
    group_links = "\n".join(
        f'<a class="directory-group" href="#{escape(record["id"])}" data-directory-group="{escape(record["id"])}" '
        f'aria-label="{escape(record["book_color_signature"])}; {record["clock_order"]} colours; open {escape(record["id"])}">'
        f'<span class="directory-signature book-color-signature">{clockwork.superscript_html(record["book_color_signature"])}</span>'
        f'<span class="directory-palette" aria-hidden="true">'
        + "".join(
            f'<span style="--directory-colour: {escape(residue["color"])}"></span>'
            for residue in record["phase_residues"]
        )
        + f'</span><span class="directory-group-id">{escape(record["id"])}</span></a>'
        for record in rows
    )
    return f"""
        <section class="directory-family">
          <h3><a class="directory-family-link" href="#wallpaper-{escape(base)}">{clockwork.orbifold_html(ORBIFOLD_BY_BASE[base])}<span class="directory-family-count">{len(rows)} nontrivial {"type" if len(rows) == 1 else "types"}</span></a></h3>
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
        _family_html(base, grouped[base], trivial_by_base[base])
        for base in BASE_ORDER
    )
    directory = "\n".join(
        _directory_family_html(base, grouped[base]) for base in contributing_bases
    ).strip()
    digest = escape(payload["meta"]["source_sha256"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="The 51 nontrivial cyclic colourings organized by Conway orbifold and Goodman–Strauss short colour notation, paired with classical polar space-group names and compact cell-action presentations.">
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
        <a href="brownian.html">brownian</a>
        <a href="future-directions.html">Colours</a>
        <a href="color-pattern-catalog.html">Patterns</a>
        <a href="clockwork-coloring-correspondence.html">Correspondence</a>
        <a href="space-group-correspondence.html" aria-current="page">Space groups</a>
        <a href="dihedral-interactive.html">Dihedral</a>
        <a href="docs/orbifold_notation.html">Notation</a>
        <a href="data/space-group-correspondence.json">Data</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>

  <main class="space-page">
    <section class="space-hero" aria-labelledby="page-title">
      <h1 id="page-title">Cyclic colourings <span aria-hidden="true">↔</span> polar space groups</h1>
      <p class="space-scope">51 nontrivial cyclic lifts · 17 base groups</p>
      <code class="height-lift" aria-label="Height-lift formula">(M, v, τ): (x, y, z) ↦ (M(x, y) + v, z + τ)</code>
    </section>

    <nav class="atlas-directory" aria-labelledby="directory-title">
      <h2 id="directory-title">51 nontrivial lifts</h2>
      <p class="directory-legend">Superscripts are colour-permutation orders.</p>
      <div class="directory-families">
{directory}
      </div>
    </nav>

    <div class="space-atlas" id="correspondences">
{families}
    </div>

    <section class="sources" aria-labelledby="provenance-title">
      <h2 id="provenance-title">Data</h2>
      <p><a href="data/space-group-correspondence.json">68-record JSON</a> · <a id="ucl-credit" href="{escape(payload['meta']['external_reference_index'])}" target="_blank" rel="noopener">UCL tables</a> · <a href="https://journals.iucr.org/j/issues/2018/05/00/in5013/index.html">IUCr hierarchy</a> · <a href="https://doi.org/10.1107/S0365110X57001966">Mackay</a> · <a href="https://arxiv.org/abs/math/9911185">Conway et al.</a> · SHA-256 <code>{digest}</code></p>
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
