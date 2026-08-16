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

from math import acos, cos, hypot, pi, sin, sqrt
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

    # Conjugate the usual p2 realization by reflection in y=x.  This places
    # the index-two colour translation horizontally, so its colour classes
    # read as the vertical strips used in the Gruenbaum--Shephard plates.
    p2 = {
        "α": _rotation(180, (0, 0)),
        "β": _rotation(180, (0, 0.5)),
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


CANONICAL_PATTERN_SEED = ((0.173, 0.137), 17.0, 0)
# The global seed lies too close to one mirror of the *632 and *442
# fundamental triangles: its reflected centres are only 13.8 px and 12.0 px
# apart at the catalog scale, so the deliberately large R-diamonds overlap.
# Each triangle's incenter is generic and maximizes the distance from all
# three mirrors, lifting the closest pair to 74.4 px and 68.8 px.
MIRROR_CLEARANCE_SEEDS: dict[str, tuple[tuple[float, float], float, int]] = {
    "p6m": ((0.394338, 0.105662), 17.0, 0),
    "p4m": ((0.353553, 0.146447), 17.0, 0),
}


def pattern_seed(parent: str | None = None) -> tuple[tuple[float, float], float, int]:
    """Return the normalized generic-orbit seed for one wallpaper parent."""

    return MIRROR_CLEARANCE_SEEDS.get(parent, CANONICAL_PATTERN_SEED)


def candidate_orbit_layouts(parent: str | None = None) -> tuple[dict[str, Any], ...]:
    """Nearby generic-orbit candidates for measured layout optimization.

    Wallpaper families share the common normalized seed except the dense
    kaleidoscopes in :data:`MIRROR_CLEARANCE_SEEDS`, whose mirror-triangle
    incenters prevent the large motifs from overlapping.  A later candidate is
    used only when reusing the family seed would make two full coloured scenes
    identical.  The catalog generator measures and ranks candidates;
    angle-only alternatives preserve every motif centre and win whenever their
    measured discrepancy is minimal.
    """

    (point, angle, colour) = pattern_seed(parent)
    if parent in MIRROR_CLEARANCE_SEEDS:
        # Keep every representative on the same maximally separated centre
        # grid.  Orientation-only alternatives are enough to separate repeated
        # pattern types without sacrificing the mirror clearance.
        angle_offsets = (0,) + tuple(
            signed
            for step in range(6, 180, 6)
            for signed in (step, -step)
        )
        point_offsets = ((0.0, 0.0),)
    else:
        angle_offsets = (0, 6, -6, 12, -12, 20, -20, 30, -30)
        point_offsets = (
            (0.0, 0.0),
            (0.018, 0.0), (-0.018, 0.0),
            (0.0, 0.018), (0.0, -0.018),
            (0.018, 0.018), (-0.018, 0.018),
            (0.018, -0.018), (-0.018, -0.018),
        )
    result: list[dict[str, Any]] = []
    for dx, dy in point_offsets:
        for offset in angle_offsets:
            result.append({
                "kind": "orbit",
                "seeds": [{
                    "point": [round(point[0] + dx, 6), round(point[1] + dy, 6)],
                    "angle": angle + offset,
                    "colour": colour,
                }],
            })
    return tuple(result)


def _layout_seeds(
    pattern: dict[str, Any], colours: int, parent: str | None = None
) -> tuple[tuple[tuple[float, float], float, int], ...]:
    layout = pattern.get("render_layout") or {}
    if layout.get("kind") == "orbit":
        seeds = layout.get("seeds") or []
        return tuple(
            (
                (float(seed["point"][0]), float(seed["point"][1])),
                float(seed["angle"]),
                int(seed.get("colour", 0)) % colours,
            )
            for seed in seeds
        )
    # Reached only by a pattern with no assigned orbit layout.  The seed must
    # stay parent-aware; the shared canonical point overlaps its own mirror
    # images in the families listed in MIRROR_CLEARANCE_SEEDS.
    point, angle, colour = pattern_seed(parent)
    return ((point, angle, colour % colours),)


def pattern_template_seeds(
    pattern: dict[str, Any], colours: int, parent: str | None = None
) -> tuple[tuple[tuple[float, float], float, int], ...]:
    """Return the assigned generic-orbit seeds for a catalog pattern."""

    return _layout_seeds(pattern, colours, parent)


def _fixed_vertical_band_scene(
    layout: dict[str, Any], *, include_colours: bool
) -> tuple[tuple[int, int, int, int, int, int], ...]:
    """Return a PP7/PP8 band layout on one shared lattice.

    In the source, primitive PP7 has two asymmetric copies around every band
    centre.  Nonprimitive PP8 moves each same-colour pair together until it
    becomes one half-turn-symmetric motif.  Our mandated R is asymmetric, so
    PP8 uses the closest schematic substitute: one R at the shared centre.
    """

    columns = int(layout.get("columns", 13))
    rows = int(layout.get("rows", 6))
    origin_x, origin_y = layout.get("origin", [60, 55])
    spacing_x, spacing_y = layout.get("spacing", [70, 90])
    motifs_per_band = int(layout.get("motifs_per_band", 1))
    offset_x, offset_y = layout.get("pair_offset", [14, 10])
    colours = int(layout.get("colours", 2))
    poses = []
    for row in range(rows):
        for column in range(columns):
            offsets = (
                ((-offset_x, -offset_y, 0), (offset_x, offset_y, 180))
                if motifs_per_band == 2 else ((0, 0, 0),)
            )
            for motif_index, (dx, dy, angle) in enumerate(offsets):
                if include_colours:
                    colour = (
                        motif_index % colours
                        if layout.get("colour_rule") == "within_pair"
                        else column % colours
                    )
                else:
                    colour = 0
                poses.append((
                    round((origin_x + column * spacing_x + dx) * 1_000),
                    round((origin_y + row * spacing_y + dy) * 1_000),
                    round(cos(angle * pi / 180) * 1_000_000),
                    round(-sin(angle * pi / 180) * 1_000_000),
                    0,
                    colour * 10 + motif_index,
                ))
    return tuple(poses)


def _orbit_scene_fingerprint(
    pattern: dict[str, Any],
    group: dict[str, Any],
    operations: tuple[tuple[Affine, tuple[int, ...]], ...],
    *,
    include_colours: bool,
) -> tuple[tuple[int, int, int, int, int, int], ...]:
    scale = RENDER_SCALE[group["wallpaper_id"]]
    poses: set[tuple[int, int, int, int, int, int]] = set()
    for seed_index, (point, angle, seed_colour) in enumerate(
        pattern_template_seeds(
            pattern, group["number_of_colours"], group["wallpaper_id"]
        )
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
            determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
            colour = permutation[seed_colour] if include_colours else 0
            poses.add((
                round(x * 1_000),
                round(y * 1_000),
                round(transformed_direction[0] * 1_000_000),
                round(-transformed_direction[1] * 1_000_000),
                1 if determinant < 0 else 0,
                colour * 10 + seed_index,
            ))
    return tuple(sorted(poses))


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
    layout = pattern.get("render_layout") or {}
    if layout.get("kind") == "fixed_vertical_bands":
        return _fixed_vertical_band_scene(layout, include_colours=True)
    return _orbit_scene_fingerprint(
        pattern, group, operations, include_colours=True
    )


def colour_blind_fingerprint(
    pattern: dict[str, Any],
    group: dict[str, Any],
    operations: tuple[tuple[Affine, tuple[int, ...]], ...] | None = None,
) -> tuple[tuple[int, int, int, int, int, int], ...]:
    """Visible motif poses with palette labels erased."""

    if operations is None:
        operations = enumerate_coloured_actions(
            group["wallpaper_id"], group["generator_colour_actions"]
        )
    layout = pattern.get("render_layout") or {}
    if layout.get("kind") == "fixed_vertical_bands":
        return _fixed_vertical_band_scene(layout, include_colours=False)
    return _orbit_scene_fingerprint(
        pattern, group, operations, include_colours=False
    )


def colour_blind_discrepancy(
    left: tuple[tuple[int, int, int, int, int, int], ...],
    right: tuple[tuple[int, int, int, int, int, int], ...],
) -> float:
    """Symmetric normalized Chamfer distance between uncoloured motif poses.

    Zero means the motif centres, orientations, and handedness agree exactly.
    The value approaches one as the layouts diverge by roughly two motif
    diameters.  Colours are deliberately absent from both inputs.
    """

    if left == right:
        return 0.0
    if not left or not right:
        return 1.0

    def pose_cost(a: tuple[int, ...], b: tuple[int, ...]) -> float:
        dx = (a[0] - b[0]) / 1_000
        dy = (a[1] - b[1]) / 1_000
        dot = max(-1.0, min(1.0, (a[2] * b[2] + a[3] * b[3]) / 1e12))
        angular = 18.0 * acos(dot) / pi
        handed = 18.0 if a[4] != b[4] else 0.0
        return min(1.0, hypot(hypot(dx, dy), hypot(angular, handed)) / 52.0)

    def directed(source: tuple[tuple[int, ...], ...], target: tuple[tuple[int, ...], ...]) -> float:
        return sum(min(pose_cost(a, b) for b in target) for a in source) / len(source)

    pose_distance = (directed(left, right) + directed(right, left)) / 2
    count_distance = abs(len(left) - len(right)) / max(len(left), len(right))
    # The explicit count term matters for the PP7 -> PP8 merge: every PP8
    # centre is near a PP7 pair, but half of the asymmetric motif copies have
    # genuinely disappeared into the book's symmetric compound motif.
    return round(min(1.0, 0.75 * pose_distance + 0.25 * count_distance), 6)


if set(AFFINE_GENERATORS) != set(GENERATOR_GEOMETRY):
    raise ValueError("affine generator table does not cover all wallpaper parents")
for _parent in AFFINE_GENERATORS:
    if not affine_relations_hold(_parent):
        raise ValueError(f"affine presentation relations fail for {_parent}")


__all__ = [
    "AFFINE_GENERATORS",
    "MIRROR_CLEARANCE_SEEDS",
    "RENDER_SCALE",
    "pattern_seed",
    "affine_generators_for",
    "affine_relations_hold",
    "candidate_orbit_layouts",
    "colour_blind_discrepancy",
    "colour_blind_fingerprint",
    "enumerate_coloured_actions",
    "pattern_template_seeds",
    "scene_fingerprint",
    "compose",
    "inverse",
]
