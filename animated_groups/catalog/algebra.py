"""Exact finite-group algebra used by the systematic animation catalog.

The target group ``D_n`` is represented by pairs ``(k, e)`` acting on the
phase circle as ``t -> (-1)**e t + k/n``.  Composition follows the convention

    (k, e) (l, f) = (k + (-1)**e l, e + f),

with both components reduced modulo ``n`` and ``2`` respectively.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import product
from typing import Mapping, Sequence


@dataclass(frozen=True, order=True)
class PhaseElement:
    """One element of the finite phase-isometry group ``D_n``."""

    modulus: int
    shift: int = 0
    reverses: bool = False

    def __post_init__(self) -> None:
        if self.modulus < 1:
            raise ValueError("phase modulus must be positive")
        object.__setattr__(self, "shift", self.shift % self.modulus)

    @classmethod
    def identity(cls, modulus: int) -> "PhaseElement":
        return cls(modulus, 0, False)

    def compose(self, other: "PhaseElement") -> "PhaseElement":
        """Return ``self`` after ``other`` (the displayed pair law above)."""

        if self.modulus != other.modulus:
            raise ValueError("cannot compose phase elements with different moduli")
        sign = -1 if self.reverses else 1
        return PhaseElement(
            self.modulus,
            self.shift + sign * other.shift,
            self.reverses ^ other.reverses,
        )

    def inverse(self) -> "PhaseElement":
        sign = -1 if self.reverses else 1
        return PhaseElement(self.modulus, -sign * self.shift, self.reverses)

    def power(self, exponent: int) -> "PhaseElement":
        if exponent < 0:
            return self.inverse().power(-exponent)
        result = PhaseElement.identity(self.modulus)
        factor = self
        value = exponent
        while value:
            if value & 1:
                result = result.compose(factor)
            factor = factor.compose(factor)
            value >>= 1
        return result

    def conjugate_by(self, conjugator: "PhaseElement") -> "PhaseElement":
        """Return ``conjugator * self * conjugator^-1``."""

        return conjugator.compose(self).compose(conjugator.inverse())

    def reduced(self) -> "CircleIsometry":
        return CircleIsometry(Fraction(self.shift, self.modulus), self.reverses)


@dataclass(frozen=True, order=True)
class CircleIsometry:
    """A modulus-independent, exact isometry of ``R/Z``."""

    shift: Fraction = Fraction(0)
    reverses: bool = False

    def __post_init__(self) -> None:
        shift = Fraction(self.shift) % 1
        object.__setattr__(self, "shift", shift)

    @classmethod
    def identity(cls) -> "CircleIsometry":
        return cls(Fraction(0), False)

    def compose(self, other: "CircleIsometry") -> "CircleIsometry":
        sign = -1 if self.reverses else 1
        return CircleIsometry(
            self.shift + sign * other.shift,
            self.reverses ^ other.reverses,
        )

    def inverse(self) -> "CircleIsometry":
        sign = -1 if self.reverses else 1
        return CircleIsometry(-sign * self.shift, self.reverses)

    def power(self, exponent: int) -> "CircleIsometry":
        if exponent < 0:
            return self.inverse().power(-exponent)
        result = CircleIsometry.identity()
        factor = self
        value = exponent
        while value:
            if value & 1:
                result = result.compose(factor)
            factor = factor.compose(factor)
            value >>= 1
        return result

    def token(self) -> str:
        prefix = "rev" if self.reverses else "shift"
        return f"{prefix}:{self.shift.numerator}/{self.shift.denominator}"


def phase_elements(modulus: int) -> tuple[PhaseElement, ...]:
    """Return the ``2 * modulus`` elements of ``D_modulus``."""

    if modulus < 1:
        raise ValueError("phase modulus must be positive")
    return tuple(
        PhaseElement(modulus, shift, reverses)
        for reverses in (False, True)
        for shift in range(modulus)
    )


def circle_assignment_sort_key(
    assignment: Sequence[CircleIsometry],
) -> tuple[tuple[int, Fraction], ...]:
    return tuple((int(image.reverses), image.shift) for image in assignment)


def canonicalize_target_assignment(
    assignment: Sequence[PhaseElement],
) -> tuple[CircleIsometry, ...]:
    """Canonicalize generator images by simultaneous target conjugacy only."""

    if not assignment:
        return ()
    modulus = assignment[0].modulus
    if any(image.modulus != modulus for image in assignment):
        raise ValueError("all generator images must lie in the same D_n")
    candidates = []
    for conjugator in phase_elements(modulus):
        candidates.append(
            tuple(image.conjugate_by(conjugator).reduced() for image in assignment)
        )
    return min(candidates, key=circle_assignment_sort_key)


@dataclass(frozen=True, order=True)
class SpatialElement:
    """Normal form ``r^power s^reflected`` in a finite spatial group."""

    power: int = 0
    reflected: bool = False


Relator = tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class FiniteSpatialGroup:
    """A cyclic or dihedral spatial group with its standard presentation."""

    family: str
    order: int

    def __post_init__(self) -> None:
        if self.family not in {"cyclic", "dihedral"}:
            raise ValueError(f"unsupported finite spatial family {self.family!r}")
        minimum = 1 if self.family == "dihedral" else 2
        if self.order < minimum:
            raise ValueError(f"{self.family} spatial order must be at least {minimum}")

    @property
    def key(self) -> str:
        prefix = "C" if self.family == "cyclic" else "D"
        return f"{prefix}{self.order}"

    @property
    def elements(self) -> tuple[SpatialElement, ...]:
        rotations = tuple(SpatialElement(power, False) for power in range(self.order))
        if self.family == "cyclic":
            return rotations
        return rotations + tuple(
            SpatialElement(power, True) for power in range(self.order)
        )

    @property
    def identity(self) -> SpatialElement:
        return SpatialElement(0, False)

    @property
    def generators(self) -> tuple[tuple[str, SpatialElement], ...]:
        if self.family == "dihedral" and self.order == 1:
            return (("s", SpatialElement(0, True)),)
        result = [("r", SpatialElement(1, False))]
        if self.family == "dihedral":
            result.append(("s", SpatialElement(0, True)))
        return tuple(result)

    @property
    def relators(self) -> tuple[Relator, ...]:
        if self.family == "cyclic":
            return ((("r", self.order),),)
        if self.order == 1:
            return ((("s", 2),),)
        return (
            (("r", self.order),),
            (("s", 2),),
            (("s", 1), ("r", 1), ("s", 1), ("r", 1)),
        )

    def normalize(self, element: SpatialElement) -> SpatialElement:
        reflected = element.reflected if self.family == "dihedral" else False
        return SpatialElement(element.power % self.order, reflected)

    def multiply(self, first: SpatialElement, second: SpatialElement) -> SpatialElement:
        first = self.normalize(first)
        second = self.normalize(second)
        if self.family == "cyclic":
            return SpatialElement((first.power + second.power) % self.order, False)
        sign = -1 if first.reflected else 1
        return SpatialElement(
            (first.power + sign * second.power) % self.order,
            first.reflected ^ second.reflected,
        )

    def inverse(self, element: SpatialElement) -> SpatialElement:
        element = self.normalize(element)
        sign = -1 if element.reflected else 1
        return SpatialElement((-sign * element.power) % self.order, element.reflected)

    def power(self, element: SpatialElement, exponent: int) -> SpatialElement:
        if exponent < 0:
            return self.power(self.inverse(element), -exponent)
        result = self.identity
        factor = self.normalize(element)
        value = exponent
        while value:
            if value & 1:
                result = self.multiply(result, factor)
            factor = self.multiply(factor, factor)
            value >>= 1
        return result

    def format_element(self, element: SpatialElement) -> str:
        element = self.normalize(element)
        if element.power == 0:
            rotation = "1"
        elif element.power == 1:
            rotation = "r"
        else:
            rotation = f"r^{element.power}"
        if not element.reflected:
            return rotation
        return "s" if rotation == "1" else f"{rotation} s"


def finite_spatial_groups(
    orders: Sequence[int] = (2, 3, 4, 6),
) -> tuple[FiniteSpatialGroup, ...]:
    cyclic = tuple(FiniteSpatialGroup("cyclic", order) for order in orders)
    dihedral_orders = (1, *tuple(order for order in orders if order != 1))
    dihedral = tuple(FiniteSpatialGroup("dihedral", order) for order in dihedral_orders)
    return cyclic + dihedral


def evaluate_spatial_word(
    group: FiniteSpatialGroup,
    assignment: Mapping[str, SpatialElement],
    word: Relator,
) -> SpatialElement:
    result = group.identity
    for generator, exponent in word:
        result = group.multiply(result, group.power(assignment[generator], exponent))
    return result


def evaluate_phase_word(
    modulus: int,
    assignment: Mapping[str, PhaseElement],
    word: Relator,
) -> PhaseElement:
    result = PhaseElement.identity(modulus)
    for generator, exponent in word:
        result = result.compose(assignment[generator].power(exponent))
    return result


def finite_hom_image(
    group: FiniteSpatialGroup,
    generator_images: Mapping[str, CircleIsometry],
    element: SpatialElement,
) -> CircleIsometry:
    """Evaluate a homomorphism on the normal form ``r^k s^e``."""

    element = group.normalize(element)
    rotation_image = generator_images.get("r", CircleIsometry.identity())
    image = rotation_image.power(element.power)
    if element.reflected:
        image = image.compose(generator_images["s"])
    return image


def generated_circle_subgroup(
    generators: Sequence[CircleIsometry],
) -> frozenset[CircleIsometry]:
    """Return the finite phase subgroup generated by exact circle isometries."""

    identity = CircleIsometry.identity()
    subgroup = {identity}
    frontier = [identity]
    steps = tuple(generators) + tuple(generator.inverse() for generator in generators)
    while frontier:
        current = frontier.pop()
        for step in steps:
            candidate = current.compose(step)
            if candidate not in subgroup:
                subgroup.add(candidate)
                frontier.append(candidate)
    return frozenset(subgroup)


@lru_cache(maxsize=None)
def finite_subgroups(family: str, order: int) -> tuple[frozenset[SpatialElement], ...]:
    """Enumerate every subgroup; the largest supported group has 12 elements."""

    group = FiniteSpatialGroup(family, order)
    elements = group.elements
    identity_index = elements.index(group.identity)
    result: list[frozenset[SpatialElement]] = []
    for mask in range(1 << len(elements)):
        if not mask & (1 << identity_index):
            continue
        subset = frozenset(
            element for index, element in enumerate(elements) if mask & (1 << index)
        )
        closed = True
        for first, second in product(subset, repeat=2):
            if group.multiply(first, second) not in subset:
                closed = False
                break
        if closed and all(group.inverse(element) in subset for element in subset):
            result.append(subset)
    return tuple(sorted(result, key=lambda subgroup: (len(subgroup), tuple(sorted(subgroup)))))


def classify_extension(
    group: FiniteSpatialGroup,
    kernel: frozenset[SpatialElement],
    image_order: int,
) -> str:
    """Classify ``1 -> kernel -> group -> image -> 1`` by complement search."""

    if len(kernel) == 1 or image_order == 1:
        return "trivial"

    complements: list[frozenset[SpatialElement]] = []
    for subgroup in finite_subgroups(group.family, group.order):
        if len(subgroup) != image_order:
            continue
        if subgroup.intersection(kernel) != {group.identity}:
            continue
        products = {
            group.multiply(kernel_element, complement_element)
            for kernel_element in kernel
            for complement_element in subgroup
        }
        if products == set(group.elements):
            complements.append(subgroup)

    if not complements:
        return "non_split"

    for complement in complements:
        if all(
            group.multiply(kernel_element, complement_element)
            == group.multiply(complement_element, kernel_element)
            for kernel_element in kernel
            for complement_element in complement
        ):
            return "direct_product"
    return "split_semidirect"


__all__ = [
    "CircleIsometry",
    "FiniteSpatialGroup",
    "PhaseElement",
    "Relator",
    "SpatialElement",
    "canonicalize_target_assignment",
    "circle_assignment_sort_key",
    "classify_extension",
    "evaluate_phase_word",
    "evaluate_spatial_word",
    "finite_hom_image",
    "finite_spatial_groups",
    "finite_subgroups",
    "generated_circle_subgroup",
    "phase_elements",
]
