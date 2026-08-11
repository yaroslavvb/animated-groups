#!/usr/bin/env python3
"""Build the 68-row clockwork/colouring correspondence page.

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
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable

from PIL import Image, ImageDraw

from tos_book_excerpt_specs import BOOK_EXCERPTS


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "color-forward-manifest.json"
DATA = ROOT / "data" / "clockwork-coloring-correspondence.json"
PAGE = ROOT / "clockwork-coloring-correspondence.html"
IMAGE_DIR = ROOT / "output" / "clockwork-colorings"

SOURCE_SHA256 = "040eebe747815557014c1dbf1d4265d204aaae35c110595f2a15b94ee7f68ca0"
CATALOG_ROOT = "https://yaroslavvb.github.io/animated-groups-fable/catalog.html?time=forward"
CATALOG_DATA_URL = "https://yaroslavvb.github.io/animated-groups-fable/data/catalog.json"
BOOK_RECORD_URL = "https://books.google.com/books?id=EtQCk0TNafsC"
BOOK_PAGE_URL = BOOK_RECORD_URL + "&pg=PA{page}"
BOOK_ERRATA_URL = "https://www.mit.edu/~hlb/Symmetries_of_Things/SoTerrors.html"
FARRIS_URL = "https://archive.bridgesmathart.org/2017/bridges2017-131.pdf#page=6"

IMAGE_WIDTH = 720
IMAGE_HEIGHT = 420
ANTIALIAS = 2
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
EXPECTED_BOOK_AUDIT_COUNTS = {
    "plane-group": 17,
    "direct-table": 41,
    "internal-discrepancy": 1,
    "composite-extension": 9,
}
M_ID = ((1, 0), (0, 1))

SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

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
                "The clock operations give the regular type 3*3³/*333. Table 13.1 "
                "prints that type, but Table 12.1 instead prints the nonregular S3 type "
                "3*3³//*333 and the derivation on p. 158 gives 3*3³/◦. The page keeps "
                "the computed kernel, flags the conflict, and links an independent "
                "p31m/3 p3m1 construction by Frank Farris."
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
                    "Table 12.1 · conflicting threefold table",
                    role="conflict",
                    excerpt_key="p156::3*3³//*333",
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
    symbol = group["symbol"]
    parent = ORBIFOLD_BY_BASE[group["base"]]
    class_phrase = f"the {group['system']} system with a {group['bravais']} lattice"
    if order == 1:
        return (
            f"{symbol} is the direct-product forward group over wallpaper orbifold "
            f"{parent} ({group['base']}), classified in {class_phrase}. Every displayed "
            "spatial operation has phase 0."
        )
    profile = phase_profile(group["render"]["ops"])
    assignments = "; ".join(
        f"{row['operation']}: {', '.join(row['phases'])}" for row in profile
    )
    return (
        f"{symbol} is a non-product forward clockwork group over wallpaper orbifold "
        f"{parent} ({group['base']}), classified in {class_phrase}. Its phases form "
        f"C{order}; the catalog cosets show {assignments}."
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
    return (
        f"The zero-phase kernel K is orbifold {kernel} ({kernel_base}); it preserves every "
        f"colour and is the frame-preserving wallpaper subgroup. The traditional perfect "
        f"cyclic colouring is {notation}, with [G:K] = {order} and G/K isomorphic to C{order}. "
        "Because this cyclic action is regular, the chosen-colour stabilizer H equals K, so "
        "the notation has one slash. "
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
            "clock_order": order,
            "cyclic_group": f"C_{order}",
            "phase_residues": residues,
            "phase_profile": phase_profile(group["render"]["ops"]),
            "clockwork_description": clockwork_description(group, order),
            "coloring_description": coloring_description(group, order, kernel_base),
            "book_audit": book_audit(
                group_id, order, parent_orbifold, kernel_orbifold
            ),
            "inverse_clock_mate": INVERSE_CLOCK_MATE.get(group_id),
            "catalog_url": f"{CATALOG_ROOT}#{group_id}",
            "image": f"output/clockwork-colorings/{group_id}.webp",
            "image_alt": (
                f"Static {order}-colour wallpaper plate induced by clockwork group "
                f"{group['symbol']}: asymmetric motifs carry phase colours for "
                f"{notation}."
            ),
            "render": group["render"],
        }
        records.append(record)

    payload = {
        "meta": {
            "schema_version": 2,
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


def validate_payload(payload: dict[str, Any]) -> None:
    meta = payload.get("meta", {})
    groups = payload.get("groups", [])
    if meta.get("schema_version") != 2:
        raise ValueError("correspondence data must use schema version 2")
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
    minimum_radius = 14 * ANTIALIAS
    if 0 < radius < minimum_radius:
        cell = min(cell * minimum_radius / radius, cell_for(3))
        b1, b2, radius = radius_for(cell)

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
    local_shape = (
        (-0.58, -0.44),
        (-0.03, -0.68),
        (0.56, -0.28),
        (0.25, 0.02),
        (0.48, 0.58),
        (-0.12, 0.40),
        (-0.64, 0.14),
    )
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
                for local_x, local_y in local_shape:
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


def _book_link(reference: dict[str, Any], css_class: str) -> str:
    excerpt = BOOK_EXCERPTS[reference["excerpt_key"]]
    return (
        f'<a class="{css_class}" href="{escape(reference["url"])}" '
        f'data-printed-page="{reference["printed_page"]}" '
        f'data-pdf-page="{reference["pdf_page"]}" '
        f'data-book-excerpt="{escape(excerpt["key"])}" '
        f'data-book-image="{escape(excerpt["image"])}" '
        f'data-book-title="{escape(excerpt["title"])}" '
        f'data-book-context="{escape(excerpt["context"])}" '
        f'data-book-alt="{escape(excerpt["alt"])}" '
        'aria-haspopup="dialog" aria-controls="book-excerpt-dialog">'
        f'{escape(reference["label"])} · printed p. {reference["printed_page"]} '
        f'(attached PDF p. {reference["pdf_page"]}) · view annotated excerpt</a>'
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
                f"<span>{escape(step['notation'])} · index {step['index']}</span>"
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
                <p>{escape(audit['summary'])}</p>
                <p class="book-primary-reference">{_book_link(primary, 'book-page-link')}</p>
                {supporting_html}
                {chain_html}
                {independent_html}
              </aside>"""


def _film_html(record: dict[str, Any]) -> str:
    group_id = escape(record["id"])
    symbol = escape(record["symbol"])
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
                  <label class="visually-hidden" for="{group_id}-phase">Phase of {symbol}</label>
                  <input class="phase-slider" id="{group_id}-phase" data-film-slider type="range" min="0" max="1" step="0.001" value="0" aria-valuetext="phase 0.000 of one period" disabled>
                  <output class="phase-output" data-film-output for="{group_id}-phase">0.000</output>
                </div>
                <figcaption id="{group_id}-film-caption">Clockwork film · paused by default</figcaption>
              </figure>"""


def _entry_html(record: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str:
    group_id = escape(record["id"])
    order = record["clock_order"]
    parent = record["parent"]
    kernel = record["kernel"]
    mate_note = ""
    if record["inverse_clock_mate"]:
        mate = by_id[record["inverse_clock_mate"]]
        mate_note = (
            "<aside class=\"orientation-note\">"
            "<strong>Clock orientation.</strong> This has the same traditional colour group as "
            f"<a href=\"#{escape(mate['id'])}\">{escape(mate['symbol'])} "
            f"({escape(mate['id'])})</a>, but traverses the cyclic palette in the opposite "
            "time order.</aside>"
        )
    entry = f"""
      <li>
        <section class="correspondence-entry" id="{group_id}" aria-labelledby="{group_id}-title" data-clock-order="{order}">
          <header class="entry-header">
            <p class="entry-number">{record['ordinal']:02d} / 68</p>
            <div>
              <h2 id="{group_id}-title"><span class="clockwork-symbol">{escape(record['symbol'])}</span> <span class="group-id">{group_id}</span></h2>
              <p class="entry-kicker">clockwork orbifold · {escape(record['system'])} · {escape(record['bravais'])}</p>
            </div>
            <div class="entry-badges" aria-label="Correspondence summary">
              <span>C<sub>{order}</sub></span>
              <span>{escape(record['tos_notation'])}</span>
            </div>
          </header>

          <div class="entry-grid">
            <div class="entry-visuals">
              {_film_html(record)}
              <figure class="colour-plate">
                <img src="{escape(record['image'])}" width="{IMAGE_WIDTH}" height="{IMAGE_HEIGHT}" loading="lazy" decoding="async" alt="{escape(record['image_alt'])}">
                <figcaption>
                  <span>Traditional coloured wallpaper plate</span>
                  <ol class="colour-key" aria-label="Colour and phase key">
                    {_phase_legend(record)}
                  </ol>
                </figcaption>
              </figure>
            </div>

            <div class="entry-copy">
              <p class="pair-label">Conway–Burgiel–Goodman-Strauss colour type</p>
              <p class="orbifold-pair">{escape(record['tos_notation'])}</p>
              <dl class="group-data">
                <div><dt>Full symmetry G</dt><dd>{escape(parent['orbifold'])} <span>({escape(parent['hm'])})</span></dd></div>
                <div><dt>All-colours kernel K</dt><dd>{escape(kernel['orbifold'])} <span>({escape(kernel['hm'])})</span></dd></div>
                <div><dt>Regular quotient</dt><dd>G/K ≅ C<sub>{order}</sub>; [G:K] = {order}</dd></div>
                <div><dt>Catalog type</dt><dd>{'product' if record['product'] else 'non-product'} · {'symmorphic' if record['symmorphic'] else 'non-symmorphic'}</dd></div>
              </dl>
              <p class="clockwork-description">{escape(record['clockwork_description'])}</p>
              <p class="coloring-description">{escape(record['coloring_description'])}</p>
              {_book_audit_html(record)}
              <div class="phase-assignment">
                <h3>Phase assignment in the displayed cosets</h3>
                {_phase_profile(record)}
              </div>
              {mate_note}
              <p class="catalog-action"><a href="{escape(record['catalog_url'])}">Open {escape(record['symbol'])} ({group_id}) in the forward catalog</a></p>
            </div>
          </div>
        </section>
      </li>"""
    return "\n".join(line.rstrip() for line in entry.splitlines())


def page_html(payload: dict[str, Any]) -> str:
    groups = payload["groups"]
    by_id = {group["id"]: group for group in groups}
    entries = "\n".join(_entry_html(group, by_id) for group in groups)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        grouped[group["parent"]["hm"]].append(group)
    directory_groups = []
    for base in BASE_ORDER:
        rows = grouped.get(base, [])
        if not rows:
            continue
        links = "".join(
            f'<li><a href="#{escape(row["id"])}">{escape(row["symbol"])}</a></li>'
            for row in rows
        )
        directory_groups.append(
            "<div class=\"directory-group\">"
            f"<h3>{escape(ORBIFOLD_BY_BASE[base])} <span>{escape(base)}</span></h3>"
            f"<ul>{links}</ul></div>"
        )
    directory = "\n".join(directory_groups)
    counts = EXPECTED_ORDER_COUNTS
    digest = payload["meta"]["source_catalog_sha256"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="An audited 68-row correspondence from forward clockwork groups to regular cyclic coloured wallpaper groups, with paused films, traditional plates, and book-page checks.">
  <meta name="theme-color" content="#ffffff">
  <title>Clockwork/coloring correspondence</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="site-controls-v2.css">
  <link rel="stylesheet" href="clockwork-coloring-correspondence.css">
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
        <a href="docs/orbifold_notation.md">Notation</a>
        <a href="data/clockwork-coloring-correspondence.json">Data</a>
        <a href="https://github.com/yaroslavvb/animated-groups">Source</a>
      </nav>
    </div>
  </header>

  <main class="correspondence-page">
    <section class="page-introduction" aria-labelledby="page-title">
      <p class="overline">68 forward groups · live films paused by default</p>
      <h1 id="page-title">Clockwork/coloring correspondence</h1>
      <p class="lead">
        Each forward clockwork group assigns a phase to every operation of its projected wallpaper
        group. Reading those phases as colour shifts turns the film into a traditional perfect
        cyclic colouring. Every row pairs the paused film with a conventional static colour plate
        and records its audit against <cite>The Symmetries of Things</cite>.
      </p>
      <div class="result-card">
        <p class="overline">The map in one line</p>
        <p class="map-formula">κ(M,v) = Nτ mod N <span>·</span> K = ker κ <span>·</span> G/K ≅ C<sub>N</sub></p>
        <p>
          The exact clock-order distribution is C<sub>1</sub>: {counts[1]}, C<sub>2</sub>: {counts[2]},
          C<sub>3</sub>: {counts[3]}, C<sub>4</sub>: {counts[4]}, C<sub>5</sub>: {counts[5]}, and
          C<sub>6</sub>: {counts[6]}. Four inverse-clock pairs differ only by cyclic colour
          orientation, leaving 64 traditional colour classes after global colour relabelling.
        </p>
      </div>
      <div class="audit-summary" aria-label="Book audit totals">
        <div><strong>58</strong><span>direct plane-group or colour-table matches</span></div>
        <div><strong>1</strong><span>disclosed internal book discrepancy</span></div>
        <div><strong>9</strong><span>composite C<sub>4</sub>/C<sub>6</sub> extensions checked by prime layers</span></div>
      </div>
    </section>

    <section class="method" aria-labelledby="reading-title">
      <p class="section-number">How to read a row</p>
      <h2 id="reading-title">The full group, the kernel, and the slash</h2>
      <div class="method-grid">
        <p>
          G is the wallpaper group obtained by forgetting time. K consists of the phase-zero
          operations and fixes every colour. The book calls H the stabilizer of one chosen colour.
          Here C<sub>N</sub> acts regularly, so H = K: onefold rows are simply G, twofold rows are
          G/K, and higher rows are G<sup>N</sup>/K. A double slash would incorrectly assert H ≠ K.
        </p>
        <p>
          The upper canvas repeats one continuously animated asymmetric motif under the exact
          catalog operations. It never starts itself: use Play or seek with the phase slider. The
          lower plate freezes the same phase character into N conventional colours, making
          colour-turning rotations, glides, and translations readable as a wallpaper pattern.
        </p>
      </div>
      <aside>
        This is an induced correspondence, not a bijection of classification tables. Orbifold
        signatures alone do not determine the embedding: a type such as 2222/2222 can have index
        two because K has a larger translation cell. The book's exceptional twofold ambiguity
        **/** does not occur among these 36 two-colour rows.
      </aside>
    </section>

    <section class="book-method" aria-labelledby="book-method-title">
      <p class="section-number">Source check</p>
      <h2 id="book-method-title">What the book verifies</h2>
      <p>
        The 2008 Conway–Burgiel–Goodman-Strauss edition was checked at full-page resolution.
        Table 3.2 verifies the 17 ordinary plane signatures; Table 11.1 directly contains all 36
        twofold G/K pairs; and Table 12.1 directly contains five of the six regular threefold
        cases. The g234 row exposes a conflict between Tables 12.1 and 13.1 and the prose on
        p. 158, so it is flagged rather than forced into the book's nonregular S<sub>3</sub> type.
      </p>
      <p>
        Chapters 11–13 stop after primefold types (p. 169). The six fourfold and three sixfold
        records are therefore labelled as extensions of the notation on p. 155. Each is checked
        through its tabulated prime-index subgroup chain, while the operation audit establishes
        that the full quotient is cyclic. Each printed-page link opens a tightly cropped,
        highlighted excerpt made from the supplied PDF; complete pages and the source PDF are not
        published. Every crop is marked <q>© COPYRIGHTED EXCERPT</q>, and the original link to
        <a href="{BOOK_RECORD_URL}">Google Books</a> remains available in the popup and without
        JavaScript. See also the book's <a href="{BOOK_ERRATA_URL}">official errata</a>.
      </p>
    </section>

    <nav class="directory" aria-labelledby="directory-title">
      <p class="section-number">Jump by projected orbifold</p>
      <h2 id="directory-title">All 68 clockwork groups</h2>
      <div class="directory-grid">
        {directory}
      </div>
    </nav>

    <ol class="correspondence-list" id="correspondences">
{entries}
    </ol>

    <section class="provenance" aria-labelledby="provenance-title">
      <p class="section-number">Audit trail</p>
      <h2 id="provenance-title">Data and reproduction</h2>
      <p>
        The <a href="data/clockwork-coloring-correspondence.json">68-record JSON</a>, this HTML,
        all 68 lossless WebP plates, 62 annotated book excerpts, and the local paused-film
        controller are generated or tracked in this repository. The data and page come from the
        <a href="scripts/generate_clockwork_coloring_correspondence.py">correspondence generator</a>;
        the <a href="scripts/tos_book_excerpt_specs.py">excerpt coordinates</a> and
        <a href="scripts/generate_tos_book_excerpts.py">crop renderer</a> are checked in separately.
        The read-only source snapshot has SHA-256 <code>{escape(digest)}</code>. Each row links to
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

  <dialog class="book-excerpt-dialog" id="book-excerpt-dialog" role="dialog" aria-modal="true" aria-labelledby="book-excerpt-title" aria-describedby="book-excerpt-context">
    <article class="book-excerpt-panel">
      <header class="book-excerpt-header">
        <p class="overline">Annotated book evidence</p>
        <button class="book-excerpt-close" type="button" data-book-dialog-close aria-label="Close book excerpt">×</button>
        <h2 id="book-excerpt-title">The Symmetries of Things</h2>
        <p id="book-excerpt-context"></p>
      </header>
      <div class="book-excerpt-media" data-book-excerpt-media data-state="idle">
        <img data-book-excerpt-image alt="" decoding="async">
        <p class="book-excerpt-status" data-book-excerpt-status role="status">Loading annotated excerpt…</p>
      </div>
      <footer class="book-excerpt-footer">
        <p>This is a low-resolution, annotated evidence crop—not a complete page. The baked-in outline marks the cited item; the faint copyright notice identifies the excerpt.</p>
        <a class="book-excerpt-source" data-book-excerpt-source href="{BOOK_RECORD_URL}" target="_blank" rel="noopener">Open the cited page at Google Books</a>
      </footer>
    </article>
  </dialog>

  <script type="module" src="clockwork-coloring-correspondence.js"></script>
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
    parser.add_argument("--check", action="store_true", help="fail if generated outputs are stale")
    args = parser.parse_args(argv)

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
    print("wrote 68 correspondence rows and static colour plates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
