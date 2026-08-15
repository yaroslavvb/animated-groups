"""Canonical affine realizations of the 17 wallpaper-group presentations.

The generators use the names in :mod:`colour_generator_actions`.  Affine
motions act on column vectors by ``x -> M x + v``.  A word is read in the
left-to-right convention of *The Symmetries of Things*: appending a generator
means applying that generator after the motion represented by the preceding
word.

These realizations are deliberately normalized per wallpaper parent.  Every
colouring over one parent therefore uses exactly the same geometry; only the
declared colour homomorphism changes between colour-group tabs.
"""

from __future__ import annotations

from math import cos, floor, pi, sin, sqrt
from typing import Any

from colour_generator_actions import GENERATOR_GEOMETRY, GROUP_PRESENTATIONS


Affine = tuple[tuple[tuple[float, float], tuple[float, float]], tuple[float, float]]


def _clean(value: float) -> float:
    return 0.0 if abs(value) < 1e-12 else round(value, 12)


def _affine(matrix: tuple[tuple[float, float], tuple[float, float]], vector=(0.0, 0.0)) -> Affine:
    return (
        tuple(tuple(_clean(value) for value in row) for row in matrix),
        tuple(_clean(value) for value in vector),
    )  # type: ignore[return-value]


IDENTITY = _affine(((1.0, 0.0), (0.0, 1.0)))


def compose(left: Affine, right: Affine) -> Affine:
    """Return ``left`` after ``right``."""

    a, u = left
    b, v = right
    matrix = (
        (a[0][0] * b[0][0] + a[0][1] * b[1][0], a[0][0] * b[0][1] + a[0][1] * b[1][1]),
        (a[1][0] * b[0][0] + a[1][1] * b[1][0], a[1][0] * b[0][1] + a[1][1] * b[1][1]),
    )
    vector = (
        a[0][0] * v[0] + a[0][1] * v[1] + u[0],
        a[1][0] * v[0] + a[1][1] * v[1] + u[1],
    )
    return _affine(matrix, vector)


def inverse(motion: Affine) -> Affine:
    matrix, vector = motion
    determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
    inverse_matrix = (
        (matrix[1][1] / determinant, -matrix[0][1] / determinant),
        (-matrix[1][0] / determinant, matrix[0][0] / determinant),
    )
    inverse_vector = (
        -(inverse_matrix[0][0] * vector[0] + inverse_matrix[0][1] * vector[1]),
        -(inverse_matrix[1][0] * vector[0] + inverse_matrix[1][1] * vector[1]),
    )
    return _affine(inverse_matrix, inverse_vector)


def _translation(x: float, y: float) -> Affine:
    return _affine(((1.0, 0.0), (0.0, 1.0)), (x, y))


def _rotation(degrees: float, centre=(0.0, 0.0)) -> Affine:
    angle = degrees * pi / 180.0
    matrix = ((cos(angle), -sin(angle)), (sin(angle), cos(angle)))
    cx, cy = centre
    vector = (
        cx - matrix[0][0] * cx - matrix[0][1] * cy,
        cy - matrix[1][0] * cx - matrix[1][1] * cy,
    )
    return _affine(matrix, vector)


def _reflection(degrees: float, point=(0.0, 0.0)) -> Affine:
    angle = degrees * pi / 180.0
    ux, uy = cos(angle), sin(angle)
    matrix = ((2 * ux * ux - 1, 2 * ux * uy), (2 * ux * uy, 2 * uy * uy - 1))
    px, py = point
    vector = (
        px - matrix[0][0] * px - matrix[0][1] * py,
        py - matrix[1][0] * px - matrix[1][1] * py,
    )
    return _affine(matrix, vector)


def _close_product(generators: dict[str, Affine], names: tuple[str, ...]) -> Affine:
    result = IDENTITY
    for name in names:
        result = compose(generators[name], result)
    return inverse(result)


def _build_generators() -> dict[str, dict[str, Affine]]:
    result: dict[str, dict[str, Affine]] = {
        "p1": {"X": _translation(1, 0), "Y": _translation(0, 1)},
        "pm": {
            "α": _translation(1, 0),
            "P": _reflection(0, (0, 0)),
            "Q": _reflection(0, (0, 0.5)),
        },
        "pg": {
            "Y": _affine(((1, 0), (0, -1)), (0.5, 0)),
            "Z": _affine(((1, 0), (0, -1)), (-0.5, 1)),
        },
        "cm": {
            "P": _reflection(0, (0, 0)),
            "Z": _affine(((1, 0), (0, -1)), (0.5, 1)),
        },
        "pmm": {
            "P": _reflection(90, (0, 0)),
            "Q": _reflection(0, (0, 0)),
            "R": _reflection(90, (0.5, 0)),
            "S": _reflection(0, (0, 0.5)),
        },
        "pmg": {
            "α": _rotation(180, (0, 0.25)),
            "β": _rotation(180, (0.5, 0.25)),
            "P": _reflection(0, (0, 0)),
        },
        "pgg": {
            "α": _rotation(180, (0, 0.25)),
            "β": _rotation(180, (0.5, 0.25)),
            "Z": _affine(((1, 0), (0, -1)), (-0.5, 0)),
        },
        "cmm": {
            "α": _rotation(180, (0.25, 0.25)),
            "P": _reflection(90, (0, 0)),
            "Q": _reflection(0, (0, 0)),
        },
        "p4m": {
            "P": _reflection(0, (0, 0)),
            "Q": _reflection(45, (0, 0)),
            "R": _reflection(90, (0.5, 0)),
        },
        "p4g": {
            "α": _rotation(90, (0.25, 0.25)),
            "P": _reflection(0, (0, 0)),
        },
        "p3m1": {
            "P": _reflection(0, (0, 0)),
            "Q": _reflection(60, (0, 0)),
            "R": _reflection(-60, (1 / sqrt(3), 0)),
        },
        "p31m": {
            "α": _rotation(120, (0.5, sqrt(3) / 6)),
            "P": _reflection(0, (0, 0)),
        },
        "p6m": {
            "P": _reflection(0, (0, 0)),
            "Q": _reflection(30, (0, 0)),
            "R": _reflection(90, (0.5, 0)),
        },
    }

    p2 = {
        "α": _rotation(180, (0, 0)),
        "β": _rotation(180, (0.5, 0)),
        "γ": _rotation(180, (0.5, 0.5)),
    }
    p2["δ"] = _close_product(p2, ("α", "β", "γ"))
    result["p2"] = p2

    p4 = {"α": _rotation(90, (0, 0)), "β": _rotation(90, (0.5, 0.5))}
    p4["γ"] = _close_product(p4, ("α", "β"))
    result["p4"] = p4

    p3 = {
        "α": _rotation(120, (0, 0)),
        "β": _affine(
            ((-0.5, -sqrt(3) / 2), (sqrt(3) / 2, -0.5)),
            (1, 0),
        ),
    }
    p3["γ"] = _affine(
        ((-0.5, -sqrt(3) / 2), (sqrt(3) / 2, -0.5)),
        (0.5, -sqrt(3) / 2),
    )
    result["p3"] = p3

    p6 = {
        "α": _rotation(60, (0, 0)),
        "β": _affine(
            ((-0.5, -sqrt(3) / 2), (sqrt(3) / 2, -0.5)),
            (1, 0),
        ),
        "γ": _affine(((-1, 0), (0, -1)), (1, 0)),
    }
    result["p6"] = p6
    return result


AFFINE_GENERATORS = _build_generators()


# Scale is pixels per normalized world unit in the 960 x 560 plate.  Coxeter
# triangles use larger translation cells than the rectangular presentations.
RENDER_SCALE: dict[str, float] = {
    "p1": 116, "p2": 116, "pm": 112, "pg": 112, "cm": 108,
    "pmm": 158, "pmg": 158, "pgg": 158, "cmm": 230,
    "p4": 168, "p4m": 235, "p4g": 182,
    "p3": 154, "p3m1": 183, "p31m": 203,
    "p6": 183, "p6m": 215,
}


def affine_generators_for(parent: str) -> dict[str, Any]:
    """Return a JSON-serializable, ordered affine rendering specification."""

    generators = AFFINE_GENERATORS[parent]
    expected_names = [name for name, _description in GENERATOR_GEOMETRY[parent]]
    if list(generators) != expected_names:
        raise ValueError(f"affine generator order mismatch for {parent}")
    return {
        "scale": RENDER_SCALE[parent],
        "generators": [
            {
                "generator": name,
                "matrix": [list(row) for row in generators[name][0]],
                "translation": list(generators[name][1]),
            }
            for name in expected_names
        ],
    }


def affine_relations_hold(parent: str, tolerance: float = 1e-8) -> bool:
    generators = AFFINE_GENERATORS[parent]
    for relator in GROUP_PRESENTATIONS[parent]["relators"]:
        value = IDENTITY
        for generator, exponent in relator:
            motion = generators[generator] if exponent > 0 else inverse(generators[generator])
            for _ in range(abs(exponent)):
                value = compose(motion, value)
        matrix, vector = value
        if any(
            abs(matrix[row][column] - (1.0 if row == column else 0.0)) > tolerance
            for row in range(2) for column in range(2)
        ) or any(abs(component) > tolerance for component in vector):
            return False
    return True


def _compose_permutations(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(left[image] for image in right)


def _inverse_permutation(permutation: tuple[int, ...]) -> tuple[int, ...]:
    result = [0] * len(permutation)
    for index, image in enumerate(permutation):
        result[image] = index
    return tuple(result)


def _motion_key(motion: Affine) -> tuple[int, ...]:
    matrix, vector = motion
    return tuple(
        round(value * 1_000_000)
        for value in (*matrix[0], *matrix[1], *vector)
    )


def enumerate_coloured_actions(
    parent: str,
    generator_actions: list[dict[str, Any]],
    translation_bound: float = 6.5,
) -> tuple[tuple[Affine, tuple[int, ...]], ...]:
    """Enumerate the bounded affine action used by the browser renderer."""

    action_by_name = {
        action["generator"]: tuple(action["colour_permutation"])
        for action in generator_actions
    }
    steps: list[tuple[Affine, tuple[int, ...]]] = []
    for name, _description in GENERATOR_GEOMETRY[parent]:
        motion = AFFINE_GENERATORS[parent][name]
        permutation = action_by_name[name]
        steps.append((motion, permutation))
        steps.append((inverse(motion), _inverse_permutation(permutation)))

    degree = len(next(iter(action_by_name.values())))
    identity_permutation = tuple(range(degree))
    queue: list[tuple[Affine, tuple[int, ...]]] = [(IDENTITY, identity_permutation)]
    by_motion = {_motion_key(IDENTITY): identity_permutation}
    cursor = 0
    while cursor < len(queue):
        current_motion, current_permutation = queue[cursor]
        cursor += 1
        for step_motion, step_permutation in steps:
            motion = compose(step_motion, current_motion)
            if max(map(abs, motion[1])) > translation_bound:
                continue
            permutation = _compose_permutations(step_permutation, current_permutation)
            key = _motion_key(motion)
            existing = by_motion.get(key)
            if existing is not None:
                if existing != permutation:
                    raise ValueError(f"inconsistent affine colour action for {parent}")
                continue
            by_motion[key] = permutation
            queue.append((motion, permutation))
            if len(queue) > 16_000:
                raise ValueError(f"affine closure exceeded limit for {parent}")
    return tuple(queue)


def _fractional_part(value: float) -> float:
    return value - floor(value)


def pattern_template_seeds(
    pattern: dict[str, Any], colours: int
) -> tuple[tuple[tuple[float, float], float, int], ...]:
    """Return the PP-stem template and the six explicit variant overlays."""

    import re

    match = re.search(r"PP(\d+)", pattern["underlying_pattern_type"])
    number = int(match.group(1)) if match else 1
    symbol = pattern["gs_pattern_type"]
    star = re.search(r"\](?:_\d+)?\*$", symbol) is not None
    letter_match = re.match(r"^PP\d+([AB])\[", symbol)
    letter = letter_match.group(1) if letter_match else None
    variant = 3 if star else (1 if letter == "A" else 2 if letter == "B" else 0)
    x = (
        0.105 + 0.29 * _fractional_part(number * 0.61803398875 + 0.17)
        + variant * 0.037
    )
    y = (
        0.085 + 0.27 * _fractional_part(number * 0.41421356237 + 0.31)
        - variant * 0.029
    )
    angle = (number * 47 + 11 + variant * 23) % 360
    return (((x, y), angle, (number + variant) % colours),)


def scene_fingerprint(
    pattern: dict[str, Any],
    group: dict[str, Any],
    operations: tuple[tuple[Affine, tuple[int, ...]], ...] | None = None,
) -> tuple[tuple[int, int, int, int, int, int], ...]:
    """Canonical visible-pose fingerprint mirroring ``buildPatternSvg``."""

    if operations is None:
        operations = enumerate_coloured_actions(
            group["wallpaper_id"], group["generator_colour_actions"]
        )
    scale = RENDER_SCALE[group["wallpaper_id"]]
    poses: set[tuple[int, int, int, int, int, int]] = set()
    for seed_index, (point, angle, seed_colour) in enumerate(
        pattern_template_seeds(pattern, group["number_of_colours"])
    ):
        radians = angle * pi / 180
        direction = (cos(radians), sin(radians))
        for (matrix, vector), permutation in operations:
            world = (
                matrix[0][0] * point[0] + matrix[0][1] * point[1] + vector[0],
                matrix[1][0] * point[0] + matrix[1][1] * point[1] + vector[1],
            )
            x, y = 480 + scale * world[0], 280 - scale * world[1]
            if x < -30 or x > 990 or y < -30 or y > 590:
                continue
            transformed_direction = (
                matrix[0][0] * direction[0] + matrix[0][1] * direction[1],
                matrix[1][0] * direction[0] + matrix[1][1] * direction[1],
            )
            # The SVG key uses the pose angle; its cosine/sine vector is an
            # equivalent, wrap-free fingerprint and remains exact enough at
            # the renderer's 1e-3 quantization.
            determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
            poses.add((
                round(x * 1_000),
                round(y * 1_000),
                round(transformed_direction[0] * 1_000_000),
                round(-transformed_direction[1] * 1_000_000),
                1 if determinant < 0 else 0,
                permutation[seed_colour] * 10 + seed_index,
            ))
    return tuple(sorted(poses))


if set(AFFINE_GENERATORS) != set(GENERATOR_GEOMETRY):
    raise ValueError("affine generator table does not cover all wallpaper parents")
for _parent in AFFINE_GENERATORS:
    if not affine_relations_hold(_parent):
        raise ValueError(f"affine presentation relations fail for {_parent}")


__all__ = [
    "AFFINE_GENERATORS",
    "RENDER_SCALE",
    "affine_generators_for",
    "affine_relations_hold",
    "enumerate_coloured_actions",
    "pattern_template_seeds",
    "scene_fingerprint",
    "compose",
    "inverse",
]
