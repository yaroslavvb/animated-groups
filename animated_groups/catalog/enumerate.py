"""Enumerate and normalize finite phase actions for the systematic catalog."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
import hashlib
import math
from itertools import product
from typing import Iterable, Sequence

from .algebra import (
    CircleIsometry,
    FiniteSpatialGroup,
    PhaseElement,
    SpatialElement,
    canonicalize_target_assignment,
    circle_assignment_sort_key,
    classify_extension,
    evaluate_phase_word,
    finite_hom_image,
    finite_spatial_groups,
    generated_circle_subgroup,
    phase_elements,
)


SCHEMA_VERSION = "1.0"
DEFAULT_TARGET_MODULI = tuple(range(2, 13))
DEFAULT_FINITE_ORDERS = (2, 3, 4, 6)
EXTENSION_TYPES = {"trivial", "direct_product", "split_semidirect", "non_split"}


@dataclass(frozen=True, order=True)
class GeneratorImage:
    generator: str
    action: CircleIsometry

    def token(self) -> str:
        return f"{self.generator}={self.action.token()}"


@dataclass(frozen=True)
class FiniteHomomorphism:
    """One target-conjugacy class of maps from a finite spatial group."""

    group: FiniteSpatialGroup
    target_modulus: int
    generator_images: tuple[GeneratorImage, ...]

    def image(self, element: SpatialElement) -> CircleIsometry:
        assignment = {item.generator: item.action for item in self.generator_images}
        return finite_hom_image(self.group, assignment, element)

    @property
    def canonical_images(self) -> tuple[CircleIsometry, ...]:
        return tuple(item.action for item in self.generator_images)


@dataclass(frozen=True)
class CatalogEntry:
    """A serializable normalized catalog row."""

    id: str
    canonical_key: str
    family: str
    domain: str
    order: int | None
    domain_size: int | None
    generator_images: tuple[GeneratorImage, ...]
    target_phase_order: int
    reduced_phase_order: int
    phase_rotation_order: int
    image_order: int
    kernel_elements: tuple[str, ...]
    kernel_order: int | None
    graph_nonproduct: bool
    extension_type: str
    time_reversing: bool
    frame_divisor: int
    tags: tuple[str, ...]
    realized_in_moduli: tuple[int, ...]
    translation_d4_orbit_key: str | None = None
    quotient_projection_split: bool | None = None
    product_lattice_cover_split: bool | None = None

    def __post_init__(self) -> None:
        if self.extension_type not in EXTENSION_TYPES:
            raise ValueError(f"unknown extension type {self.extension_type!r}")
        if not self.realized_in_moduli:
            raise ValueError("catalog entries need at least one target realization")
        if self.target_phase_order != min(self.realized_in_moduli):
            raise ValueError("target_phase_order must be the least realized modulus")
        if (
            self.frame_divisor < 1
            or self.reduced_phase_order < 1
            or self.phase_rotation_order < 1
        ):
            raise ValueError("phase and frame divisors must be positive")


@dataclass(frozen=True)
class Catalog:
    schema_version: str
    target_moduli: tuple[int, ...]
    finite_orders: tuple[int, ...]
    entries: tuple[CatalogEntry, ...]

    @property
    def finite_entries(self) -> tuple[CatalogEntry, ...]:
        return tuple(
            entry for entry in self.entries if entry.family in {"cyclic", "dihedral"}
        )

    @property
    def translation_entries(self) -> tuple[CatalogEntry, ...]:
        return tuple(entry for entry in self.entries if entry.family == "translation")

    @property
    def reversible_relay_entries(self) -> tuple[CatalogEntry, ...]:
        return tuple(entry for entry in self.entries if entry.family == "reversible_relay")


def _assignment_key(images: Sequence[CircleIsometry]) -> tuple[tuple[int, Fraction], ...]:
    return circle_assignment_sort_key(images)


def _is_nontrivial(images: Sequence[CircleIsometry]) -> bool:
    identity = CircleIsometry.identity()
    return any(image != identity for image in images)


def enumerate_finite_homomorphisms(
    group: FiniteSpatialGroup,
    target_modulus: int,
) -> tuple[FiniteHomomorphism, ...]:
    """Exhaust all generator assignments, relations, and target conjugacy."""

    if target_modulus < 2:
        raise ValueError("target modulus must be at least two")
    labels = tuple(label for label, _ in group.generators)
    target = phase_elements(target_modulus)
    canonical_assignments: set[tuple[CircleIsometry, ...]] = set()

    for values in product(target, repeat=len(labels)):
        assignment = dict(zip(labels, values))
        if any(
            evaluate_phase_word(target_modulus, assignment, relator)
            != PhaseElement.identity(target_modulus)
            for relator in group.relators
        ):
            continue
        reduced = tuple(value.reduced() for value in values)
        if not _is_nontrivial(reduced):
            continue
        canonical_assignments.add(canonicalize_target_assignment(values))

    result = []
    for images in sorted(canonical_assignments, key=_assignment_key):
        result.append(
            FiniteHomomorphism(
                group=group,
                target_modulus=target_modulus,
                generator_images=tuple(
                    GeneratorImage(label, image) for label, image in zip(labels, images)
                ),
            )
        )
    return tuple(result)


def validate_finite_homomorphism(homomorphism: FiniteHomomorphism) -> None:
    """Exhaustively verify the homomorphism law on a finite domain."""

    group = homomorphism.group
    for first, second in product(group.elements, repeat=2):
        actual = homomorphism.image(group.multiply(first, second))
        expected = homomorphism.image(first).compose(homomorphism.image(second))
        if actual != expected:
            raise ValueError(
                f"invalid homomorphism {group.key} -> D_{homomorphism.target_modulus}"
            )


def _lcm_denominators(images: Sequence[CircleIsometry]) -> int:
    return reduce(math.lcm, (image.shift.denominator for image in images), 1)


def _canonical_key(
    family: str,
    domain: str,
    order: int | None,
    images: Sequence[GeneratorImage],
) -> str:
    order_token = "infinite" if order is None else str(order)
    image_token = ";".join(image.token() for image in images)
    return f"{family}|{domain}|{order_token}|{image_token}"


def _stable_id(family: str, domain: str, canonical_key: str) -> str:
    digest = hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:12]
    domain_slug = "".join(character.lower() if character.isalnum() else "-" for character in domain)
    domain_slug = "-".join(filter(None, domain_slug.split("-")))
    return f"{family}-{domain_slug}-{digest}"


def _finite_tags(
    group: FiniteSpatialGroup,
    images: Sequence[CircleIsometry],
    image_order: int,
    extension_type: str,
) -> tuple[str, ...]:
    tags = {
        group.family,
        group.key.lower(),
        "graph_nonproduct",
        extension_type,
        f"image_order_{image_order}",
        "time_reversing" if any(image.reverses for image in images) else "phase_shifting",
    }
    if group.family == "cyclic":
        tags.add("rotary_reversal" if any(image.reverses for image in images) else "time_screw")
    else:
        tags.add("dihedral_choreography")
    if group.key == "D1":
        tags.add("single_mirror")
    return tuple(sorted(tags))


def _entry_from_finite_bucket(
    group: FiniteSpatialGroup,
    images: tuple[GeneratorImage, ...],
    moduli: Iterable[int],
) -> CatalogEntry:
    moduli = tuple(sorted(set(moduli)))
    image_actions = tuple(image.action for image in images)
    image_subgroup = generated_circle_subgroup(image_actions)
    phase_rotation_order = sum(
        not element.reverses for element in image_subgroup
    )
    assignment = {image.generator: image.action for image in images}
    kernel = frozenset(
        element
        for element in group.elements
        if finite_hom_image(group, assignment, element) == CircleIsometry.identity()
    )
    if len(group.elements) != len(kernel) * len(image_subgroup):
        raise ValueError(f"first-isomorphism check failed for {group.key}")
    extension_type = classify_extension(group, kernel, len(image_subgroup))
    reduced_phase_order = _lcm_denominators(image_actions)
    canonical_key = _canonical_key(group.family, group.key, group.order, images)
    return CatalogEntry(
        id=_stable_id(group.family, group.key, canonical_key),
        canonical_key=canonical_key,
        family=group.family,
        domain=group.key,
        order=group.order,
        domain_size=len(group.elements),
        generator_images=images,
        target_phase_order=min(moduli),
        reduced_phase_order=reduced_phase_order,
        phase_rotation_order=phase_rotation_order,
        image_order=len(image_subgroup),
        kernel_elements=tuple(
            group.format_element(element) for element in group.elements if element in kernel
        ),
        kernel_order=len(kernel),
        graph_nonproduct=True,
        extension_type=extension_type,
        time_reversing=any(image.reverses for image in image_actions),
        frame_divisor=reduced_phase_order,
        tags=_finite_tags(group, image_actions, len(image_subgroup), extension_type),
        realized_in_moduli=moduli,
    )


def _mod_one(value: Fraction) -> Fraction:
    return Fraction(value) % 1


def _translation_pair_key(pair: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    inverse = (_mod_one(-pair[0]), _mod_one(-pair[1]))
    return min(pair, inverse)


def translation_d4_orbit_key(first: Fraction, second: Fraction) -> str:
    """Return the square point-group orbit key without quotienting catalog rows."""

    first = _mod_one(first)
    second = _mod_one(second)
    candidates = {
        (_mod_one(sign_first * left), _mod_one(sign_second * right))
        for left, right in ((first, second), (second, first))
        for sign_first in (-1, 1)
        for sign_second in (-1, 1)
    }
    representative = min(candidates)
    return (
        f"x:{representative[0].numerator}/{representative[0].denominator};"
        f"y:{representative[1].numerator}/{representative[1].denominator}"
    )


def enumerate_translation_characters(
    target_modulus: int,
) -> tuple[tuple[CircleIsometry, CircleIsometry], ...]:
    """Enumerate nonzero ``Z^2 -> C_n`` maps modulo target conjugacy.

    The ordered basis labels ``x`` and ``y`` are never swapped or otherwise
    quotiented.  Target reflection only identifies ``(p,q)`` with ``(-p,-q)``.
    """

    if target_modulus < 2:
        raise ValueError("target modulus must be at least two")
    result: set[tuple[Fraction, Fraction]] = set()
    for first in range(target_modulus):
        for second in range(target_modulus):
            if first == 0 and second == 0:
                continue
            pair = (Fraction(first, target_modulus), Fraction(second, target_modulus))
            result.add(_translation_pair_key(pair))
    return tuple(
        (CircleIsometry(first, False), CircleIsometry(second, False))
        for first, second in sorted(result)
    )


def _entry_from_translation_bucket(
    images: tuple[GeneratorImage, ...],
    moduli: Iterable[int],
) -> CatalogEntry:
    moduli = tuple(sorted(set(moduli)))
    actions = tuple(image.action for image in images)
    reduced_phase_order = _lcm_denominators(actions)
    image_order = len(generated_circle_subgroup(actions))
    canonical_key = _canonical_key("translation", "Z2_square", None, images)
    first, second = (action.shift for action in actions)
    tags = tuple(
        sorted(
            {
                "translation",
                "square_lattice",
                "traveling",
                "phase_shifting",
                "graph_nonproduct",
                "non_split",
                f"image_order_{image_order}",
            }
        )
    )
    return CatalogEntry(
        id=_stable_id("translation", "Z2_square", canonical_key),
        canonical_key=canonical_key,
        family="translation",
        domain="Z2_square",
        order=None,
        domain_size=None,
        generator_images=images,
        target_phase_order=min(moduli),
        reduced_phase_order=reduced_phase_order,
        phase_rotation_order=image_order,
        image_order=image_order,
        kernel_elements=(),
        kernel_order=None,
        graph_nonproduct=True,
        # Z^2 is torsion-free, so a nontrivial finite quotient has no subgroup
        # complement in the product-lattice covering group.
        extension_type="non_split",
        time_reversing=False,
        frame_divisor=reduced_phase_order,
        tags=tags,
        realized_in_moduli=moduli,
        translation_d4_orbit_key=translation_d4_orbit_key(first, second),
        quotient_projection_split=None,
        product_lattice_cover_split=False,
    )


def _reversible_relay_entry(order: int, available_moduli: Sequence[int]) -> CatalogEntry:
    """Build the canonical reversible relay carried by the wallpaper group pm.

    On the product-lattice cover, ``a`` is an infinite translation with phase
    ``1/order``, ``b`` has zero phase, and the mirror ``m`` reverses time.  The
    finite n-cell quotient projects isomorphically to ``D_n`` and therefore
    splits, while the torsion-free translation direction prevents a complement
    on the full product-lattice cover.
    """

    realized = tuple(modulus for modulus in available_moduli if modulus % order == 0)
    if not realized:
        raise ValueError(f"reversible relay order {order} is not realized")
    images = (
        GeneratorImage("a", CircleIsometry(Fraction(1, order), False)),
        GeneratorImage("b", CircleIsometry.identity()),
        GeneratorImage("m", CircleIsometry(Fraction(0), True)),
    )
    domain = "pm_wallpaper_cover"
    canonical_key = _canonical_key("reversible_relay", domain, order, images)
    tags = tuple(
        sorted(
            {
                "reversible_relay",
                "pm",
                "traveling",
                "time_reversing",
                "graph_nonproduct",
                "non_split_cover",
                "split_finite_quotient",
                f"image_order_{2 * order}",
            }
        )
    )
    return CatalogEntry(
        id=_stable_id("reversible_relay", f"pm-{order}", canonical_key),
        canonical_key=canonical_key,
        family="reversible_relay",
        domain=domain,
        order=order,
        domain_size=None,
        generator_images=images,
        target_phase_order=min(realized),
        reduced_phase_order=order,
        phase_rotation_order=order,
        image_order=2 * order,
        kernel_elements=(),
        kernel_order=None,
        graph_nonproduct=True,
        extension_type="non_split",
        time_reversing=True,
        frame_divisor=order,
        tags=tags,
        realized_in_moduli=realized,
        quotient_projection_split=True,
        product_lattice_cover_split=False,
    )


def build_catalog(
    *,
    target_moduli: Iterable[int] = DEFAULT_TARGET_MODULI,
    finite_orders: Sequence[int] = DEFAULT_FINITE_ORDERS,
    include_translations: bool = True,
    include_reversible_relays: bool = True,
) -> Catalog:
    """Build the deterministic normalized catalog in memory.

    Assignments are quotiented only by simultaneous conjugacy in their target
    ``D_n``.  Rows from inflated target moduli merge exactly when their reduced
    Fraction-valued canonical generator images are identical.
    """

    moduli = tuple(sorted(set(target_moduli)))
    if not moduli or moduli[0] < 2:
        raise ValueError("target moduli must all be at least two")
    orders = tuple(dict.fromkeys(finite_orders))

    finite_buckets: dict[
        tuple[str, str, int, tuple[GeneratorImage, ...]],
        tuple[FiniteSpatialGroup, set[int]],
    ] = {}
    for group in finite_spatial_groups(orders):
        for modulus in moduli:
            for homomorphism in enumerate_finite_homomorphisms(group, modulus):
                validate_finite_homomorphism(homomorphism)
                images = homomorphism.generator_images
                key = (group.family, group.key, group.order, images)
                if key not in finite_buckets:
                    finite_buckets[key] = (group, set())
                finite_buckets[key][1].add(modulus)

    entries = [
        _entry_from_finite_bucket(group, key[3], realized)
        for key, (group, realized) in finite_buckets.items()
    ]

    if include_translations:
        translation_buckets: dict[tuple[GeneratorImage, ...], set[int]] = {}
        for modulus in moduli:
            for first, second in enumerate_translation_characters(modulus):
                images = (
                    GeneratorImage("x", first),
                    GeneratorImage("y", second),
                )
                translation_buckets.setdefault(images, set()).add(modulus)
        entries.extend(
            _entry_from_translation_bucket(images, realized)
            for images, realized in translation_buckets.items()
        )

    if include_reversible_relays:
        entries.extend(_reversible_relay_entry(order, moduli) for order in moduli)

    entries.sort(key=lambda entry: (entry.family, entry.domain, entry.canonical_key))
    ids = [entry.id for entry in entries]
    canonical_keys = [entry.canonical_key for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("stable catalog ID collision")
    if len(canonical_keys) != len(set(canonical_keys)):
        raise ValueError("duplicate normalized catalog key")

    return Catalog(
        schema_version=SCHEMA_VERSION,
        target_moduli=moduli,
        finite_orders=orders,
        entries=tuple(entries),
    )


__all__ = [
    "Catalog",
    "CatalogEntry",
    "DEFAULT_FINITE_ORDERS",
    "DEFAULT_TARGET_MODULI",
    "FiniteHomomorphism",
    "GeneratorImage",
    "build_catalog",
    "enumerate_finite_homomorphisms",
    "enumerate_translation_characters",
    "translation_d4_orbit_key",
    "validate_finite_homomorphism",
]
