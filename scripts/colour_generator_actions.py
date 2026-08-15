"""Geometric generators and their induced permutations of one to three colours.

Generator names follow the annotated signatures in *The Symmetries of
Things*, Tables 11.1--13.1.  Permutations use the displayed palette labels
A, B, C.  The corrected pmg, cmm, and p31m three-colour types use the same
generator actions as the book's presentations, with the audited kernels used
by the colour-pattern catalog.
"""

from __future__ import annotations

from typing import Any


# The ordered generators are exactly those read from the annotated orbifold
# signature.  Stars introduce mirror generators; crosses introduce glide
# generators; circle generators are translations.
GENERATOR_GEOMETRY: dict[str, tuple[tuple[str, str], ...]] = {
    "p1": (("X", "translation"), ("Y", "translation")),
    "p2": (
        ("α", "half-turn"), ("β", "half-turn"),
        ("γ", "half-turn"), ("δ", "half-turn"),
    ),
    "pm": (
        ("α", "translation"),
        ("P", "mirror reflection"), ("Q", "parallel mirror reflection"),
    ),
    "pg": (("Y", "glide reflection"), ("Z", "glide reflection")),
    "cm": (("P", "mirror reflection"), ("Z", "glide reflection")),
    "pmm": (
        ("P", "mirror reflection"), ("Q", "mirror reflection"),
        ("R", "mirror reflection"), ("S", "mirror reflection"),
    ),
    "pmg": (
        ("α", "half-turn"), ("β", "half-turn"),
        ("P", "mirror reflection"),
    ),
    "pgg": (
        ("α", "half-turn"), ("β", "half-turn"),
        ("Z", "glide reflection"),
    ),
    "cmm": (
        ("α", "half-turn"),
        ("P", "mirror reflection"), ("Q", "mirror reflection"),
    ),
    "p4": (
        ("α", "quarter-turn"), ("β", "quarter-turn"),
        ("γ", "half-turn"),
    ),
    "p4m": (
        ("P", "mirror reflection"), ("Q", "mirror reflection"),
        ("R", "mirror reflection"),
    ),
    "p4g": (("α", "quarter-turn"), ("P", "mirror reflection")),
    "p3": (
        ("α", "one-third turn"), ("β", "one-third turn"),
        ("γ", "one-third turn"),
    ),
    "p3m1": (
        ("P", "mirror reflection"), ("Q", "mirror reflection"),
        ("R", "mirror reflection"),
    ),
    "p31m": (("α", "one-third turn"), ("P", "mirror reflection")),
    "p6": (
        ("α", "one-sixth turn"), ("β", "one-third turn"),
        ("γ", "half-turn"),
    ),
    "p6m": (
        ("P", "mirror reflection"), ("Q", "mirror reflection"),
        ("R", "mirror reflection"),
    ),
}


# Exact representatives of the 23 transitive three-colour actions.  Codes
# denote permutations of A,B,C.  The low-symmetry rows are Table 13.1 with
# t+1=(ABC), t-1=(ACB), 1-t=(AB), and -t=(BC).  The high-symmetry rows are
# the explicit permutations in the derivations on pp. 156--158.
THREE_COLOUR_ACTION_CODES: dict[str, tuple[str, ...]] = {
    "◦³/◦": ("1", "ABC"),
    "2222³//◦": ("BC", "BC", "AB", "AB"),
    "**³//◦": ("1", "AB", "BC"),
    "**³/**": ("ABC", "1", "1"),
    "××³/××": ("ABC", "ACB"),
    "××³//◦": ("AB", "BC"),
    "*×³/*×": ("1", "ABC"),
    "*×³//◦": ("AB", "BC"),
    "*2222³//**": ("1", "AB", "1", "BC"),
    # The printed/errata row 22*³//◦ is intransitive.  The transitive
    # replacement has α=β=-t and P=1-t, hence K=××.
    "22*³//××": ("BC", "BC", "AB"),
    "22*³//**": ("BC", "AB", "1"),
    "22×³//××": ("BC", "BC", "AB"),
    # The displayed presentation gives the centred-mirror kernel *×.
    "2*22³//*×": ("BC", "1", "AB"),
    "333³/◦": ("ABC", "ABC", "ABC"),
    "333³/333": ("ABC", "ACB", "1"),
    "*333³//◦": ("AB", "BC", "CA"),
    "*333³//333": ("AB", "BC", "BC"),
    # Table 12.1 interchanges the two p31m kernel labels.  These actions are
    # the presentations themselves, paired with their audited kernels.
    "3*3³//◦": ("ABC", "AB"),
    "3*3³/*333": ("ABC", "1"),
    "632³/2222": ("ABC", "ACB", "1"),
    "632³//333": ("AB", "ABC", "CA"),
    "*632³//2222": ("BC", "AB", "BC"),
    "*632³//*333": ("1", "AB", "BC"),
}


PERMUTATION_BY_CODE: dict[str, tuple[int, int, int]] = {
    "1": (0, 1, 2),
    "AB": (1, 0, 2),
    "BC": (0, 2, 1),
    "CA": (2, 1, 0),
    "ABC": (1, 2, 0),
    "ACB": (2, 0, 1),
}

SUPERSCRIPT_DIGITS = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
}


def _numeric_superscripts(signature: str) -> tuple[int, ...]:
    """Read the generator orders from a two-colour short signature."""

    result: list[int] = []
    index = 0
    while index < len(signature):
        if signature[index] in SUPERSCRIPT_DIGITS:
            digits = ""
            while index < len(signature) and signature[index] in SUPERSCRIPT_DIGITS:
                digits += SUPERSCRIPT_DIGITS[signature[index]]
                index += 1
            result.append(int(digits))
            continue
        index += 1
    return tuple(result)


def _permutation(code: str, colours: int) -> tuple[int, ...]:
    if colours == 1:
        return (0,)
    if colours == 2:
        return (0, 1) if code == "1" else (1, 0)
    return PERMUTATION_BY_CODE[code]


def generator_colour_actions(
    parent: str,
    colours: int,
    notation: str,
    short_signature: str,
) -> list[dict[str, Any]]:
    """Return the ordered geometric generators and their colour permutations."""

    geometry = GENERATOR_GEOMETRY[parent]
    if colours == 1:
        codes = ("1",) * len(geometry)
    elif colours == 2:
        orders = _numeric_superscripts(short_signature)
        codes = tuple("1" if order == 1 else "AB" for order in orders)
    else:
        codes = THREE_COLOUR_ACTION_CODES[notation]
    if len(codes) != len(geometry):
        raise ValueError(
            f"generator/action mismatch for {notation}: {len(geometry)} generators, "
            f"{len(codes)} actions"
        )
    return [
        {
            "generator": generator,
            "geometry": description,
            "permutation_code": code,
            "colour_permutation": list(_permutation(code, colours)),
        }
        for (generator, description), code in zip(geometry, codes, strict=True)
    ]


def permutation_group(actions: list[dict[str, Any]]) -> set[tuple[int, ...]]:
    """Generate the finite permutation image, for catalog validation."""

    generators = [tuple(action["colour_permutation"]) for action in actions]
    degree = len(generators[0])
    identity = tuple(range(degree))

    def compose(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
        return tuple(left[right[index]] for index in range(degree))

    image = {identity}
    while True:
        enlarged = image | {
            compose(element, generator)
            for element in image
            for generator in generators
        }
        if enlarged == image:
            return image
        image = enlarged
