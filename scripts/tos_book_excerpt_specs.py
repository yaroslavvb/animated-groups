"""Exact evidence crops from *The Symmetries of Things* used by the site.

Coordinates are PDF points on 612 x 792 media-box pages, measured from the
top-left corner. Each ``crop`` is the original focus region; the renderer
expands it to at least five times that page area while retaining the exact
``highlight`` rectangle. The stored WebPs are annotated excerpts, not complete
book pages.
"""

from __future__ import annotations

import re
from typing import Any


def _asset_slug(key: str) -> str:
    slug = key.replace("::", "-")
    slug = slug.replace("//", "-double-over-")
    slug = slug.replace("/", "-over-")
    slug = slug.replace("*", "star")
    slug = slug.replace("×", "cross")
    slug = slug.replace("◦", "ring")
    slug = slug.replace("³", "3")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    return slug


def _excerpt(
    key: str,
    printed_page: int,
    crop: tuple[float, float, float, float],
    highlight: tuple[float, float, float, float],
    title: str,
    context: str,
    alt: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "printed_page": printed_page,
        "pdf_page": printed_page + 19,
        "crop": crop,
        "highlight": highlight,
        "image": f"output/book-excerpts/{_asset_slug(key)}.webp",
        "title": title,
        "context": context,
        "alt": alt,
    }


BOOK_EXCERPTS: dict[str, dict[str, Any]] = {}


def _add(*args: Any) -> None:
    excerpt = _excerpt(*args)
    key = excerpt["key"]
    if key in BOOK_EXCERPTS:
        raise ValueError(f"duplicate book excerpt key: {key}")
    BOOK_EXCERPTS[key] = excerpt


# Printed p. 40 / attached PDF p. 59: Table 3.2, the 17 plane groups.
_PLANE_GROUP_HIGHLIGHTS = {
    "*632": (277, 200, 28.5, 18),
    "*442": (311.5, 200, 29, 18),
    "*333": (346, 200, 29, 18),
    "*2222": (381, 200, 34.5, 18),
    "**": (424, 200, 17, 18),
    "2*22": (383.5, 216, 29, 14),
    "*×": (422.5, 223, 20.5, 14.5),
    "4*2": (314.5, 232.5, 23, 13.5),
    "3*3": (349, 232.5, 23, 13.5),
    "22*": (386, 232.5, 24, 13.5),
    "××": (421, 235.5, 23, 18.5),
    "22×": (384.5, 249, 27, 13.5),
    "632": (279, 262.5, 25, 13.5),
    "442": (313.5, 262.5, 25, 13.5),
    "333": (348, 262.5, 25, 13.5),
    "2222": (382.5, 262.5, 31, 13.5),
    "◦": (426, 256.5, 13.5, 22.5),
}
for _signature, _highlight in _PLANE_GROUP_HIGHLIGHTS.items():
    _add(
        f"p40::{_signature}",
        40,
        (268, 197, 184, 105),
        _highlight,
        f"Plane-group signature {_signature}",
        f"Table 3.2 on printed p. 40; the outline marks {_signature} among the 17 plane groups.",
        f"Annotated excerpt of Table 3.2 with the plane-group signature {_signature} outlined.",
    )


# Printed p. 140 / attached PDF p. 159: Table 11.1, twofold types.
_TWOFOLD_P140 = {
    "*632/3*3": ((300, 168, 216, 19), (460, 170, 42, 14.5)),
    "*632/*333": ((300, 179, 216, 19), (457.5, 181, 47, 14.5)),
    "*632/632": ((300, 190, 216, 19), (459.5, 192, 43, 14.5)),
    "632/333": ((300, 201.5, 216, 19), (462, 203.5, 38.5, 14.5)),
    "*442/*442": ((300, 224, 216, 19), (457.5, 226, 47, 14)),
    "*442/4*2": ((300, 234.5, 216, 19), (460, 236.5, 42, 14.5)),
    "*442/*2222": ((300, 245.5, 216, 19), (455, 247.5, 52, 14.5)),
    "*442/2*22": ((300, 256.5, 216, 19), (457.5, 258.5, 47, 14.5)),
    "*442/442": ((300, 267.5, 216, 19), (459.5, 269.5, 43, 14.5)),
    "4*2/442": ((300, 279, 216, 19), (462, 281, 38, 14.5)),
    "4*2/2*22": ((300, 290, 216, 19), (460, 292, 42, 14)),
    "4*2/22×": ((300, 301, 216, 19), (461.5, 303, 39.5, 14)),
    "442/442": ((300, 312, 216, 19), (462, 314, 38.5, 14.5)),
    "442/2222": ((300, 323, 216, 19), (459.5, 325, 43.5, 14.5)),
    "*333/333": ((300, 334.5, 216, 19), (459.5, 336.5, 43, 14.5)),
    "3*3/333": ((300, 357, 216, 19), (462, 359, 38, 14)),
    "*2222/*2222": ((300, 401.5, 216, 19), (453, 403.5, 56.5, 14.5)),
    "*2222/2*22": ((300, 412.5, 216, 19), (455, 414.5, 52, 14.5)),
    "*2222/**": ((300, 423.5, 216, 19), (460.5, 425.5, 41, 14.5)),
    "*2222/22*": ((300, 434.5, 216, 19), (457.5, 436.5, 47, 14)),
    "*2222/2222": ((300, 445.5, 216, 19), (455, 447.5, 52.5, 14)),
    "2*22/22*": ((300, 456.5, 216, 19), (460, 458.5, 42, 14.5)),
    "2*22/2222": ((300, 467.5, 216, 19), (457.5, 469.5, 47.5, 14.5)),
    "2*22/*2222": ((300, 478.5, 216, 19), (455, 480.5, 52, 14.5)),
    "2*22/*×": ((300, 489.5, 216, 19), (461.5, 491.5, 39, 14.5)),
    "2*22/22×": ((300, 500.5, 216, 19), (459, 502.5, 44.5, 14.5)),
    "22*/2222": ((300, 512, 216, 19), (459.5, 514, 43, 14)),
    "22*/22*": ((300, 523, 216, 19), (462.5, 525, 37, 14)),
    "22*/22×": ((300, 534, 216, 19), (461.5, 536, 39.5, 14)),
    "22*/**": ((300, 545, 216, 19), (465.5, 547, 31.5, 14)),
    "22*/××": ((300, 555.5, 216, 19), (463, 557.5, 36.5, 14.5)),
}
for _type, (_crop, _highlight) in _TWOFOLD_P140.items():
    _add(
        f"p140::{_type}",
        140,
        _crop,
        _highlight,
        f"Twofold colour type {_type}",
        f"Table 11.1 on printed p. 140; the outline marks the colour-type cell {_type}.",
        f"Annotated Table 11.1 row with the twofold colour type {_type} outlined.",
    )


# Printed p. 141 / attached PDF p. 160: continuation of Table 11.1.
_TWOFOLD_P141 = {
    "22×/2222": ((210, 168, 180, 19), (338, 170, 45, 14.5)),
    "22×/××": ((210, 179, 180, 19), (341, 181, 39, 14.5)),
    "2222/2222": ((210, 190.5, 180, 19), (336.5, 192.5, 48, 14.5)),
    "2222/◦": ((210, 201.5, 180, 19), (344, 203.5, 33, 14.5)),
    "*×/◦": ((210, 290, 180, 19), (348.5, 292, 24, 14)),
}
for _type, (_crop, _highlight) in _TWOFOLD_P141.items():
    _add(
        f"p141::{_type}",
        141,
        _crop,
        _highlight,
        f"Twofold colour type {_type}",
        f"Table 11.1 on printed p. 141; the outline marks the colour-type cell {_type}.",
        f"Annotated Table 11.1 row with the twofold colour type {_type} outlined.",
    )


_add(
    "p153::onefold-nfold-definition",
    153,
    (86, 491, 336, 124),
    (89, 494, 327, 116),
    "Onefold and n-fold colourings",
    "Printed p. 153; the outline marks the definition of onefold and transitive n-fold colourings.",
    "Annotated paragraph defining onefold and n-fold colourings.",
)

_add(
    "p155::slash-rule",
    155,
    (86, 438, 334, 80),
    (89, 444, 326, 66),
    "The book's slash rule",
    "Printed p. 155; the outline marks G³/H/K, the single- and double-slash abbreviations, and their p-fold extension.",
    "Annotated paragraph defining the book's single- and double-slash colour notation.",
)


# Printed p. 156 / attached PDF p. 175: selected Table 12.1 rows.
_THREEFOLD_P156 = {
    "333³/◦": ((325, 258, 160, 28), (425, 258, 43, 26)),
    "333³/333": ((325, 273, 160, 22), (426, 274, 45, 18)),
    "632³/2222": ((325, 183, 160, 22), (424, 185, 52, 18)),
    "3*3³//*333": ((325, 247, 160, 22), (424, 249, 52, 18)),
}
for _type, (_crop, _highlight) in _THREEFOLD_P156.items():
    _add(
        f"p156::{_type}",
        156,
        _crop,
        _highlight,
        f"Threefold colour type {_type}",
        f"Table 12.1 on printed p. 156; the outline marks {_type}.",
        f"Annotated Table 12.1 row with the threefold colour type {_type} outlined.",
    )


_add(
    "p158::g234-prose-conflict",
    158,
    (194, 359, 333, 49),
    (198, 363, 326, 41),
    "The p. 158 threefold derivation",
    "Printed p. 158; the outline marks the prose alternatives used in the g234 audit.",
    "Annotated excerpt of the p. 158 threefold derivation relevant to g234.",
)

_add(
    "p164::g234-single-slash-table",
    164,
    (265, 429, 238, 40),
    (387, 448, 52, 17),
    "The later g234 table entry",
    "Table 13.1 on printed p. 164; the outline marks the later single-slash 3*3³/*333 entry.",
    "Annotated Table 13.1 excerpt with 3*3 cubed over *333 outlined.",
)

_add(
    "p169::primefold-scope",
    169,
    (84, 415, 338, 90),
    (89, 442, 327, 53),
    "Where the book's enumeration stops",
    "Printed p. 169; the outline marks the statement that the chapters enumerate primefold types and stop there.",
    "Annotated paragraph stating the scope of the book's primefold colour-type enumeration.",
)


if len(BOOK_EXCERPTS) != 62:
    raise ValueError(f"expected 62 book excerpt specifications, found {len(BOOK_EXCERPTS)}")

if len({excerpt["image"] for excerpt in BOOK_EXCERPTS.values()}) != 62:
    raise ValueError("book excerpt asset names are not unique")
