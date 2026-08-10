"""Deterministic links between catalog rows and the four rendered recipes."""

from __future__ import annotations

from fractions import Fraction

from .algebra import CircleIsometry
from .enumerate import Catalog, CatalogEntry
from .patterns import PATTERNS


def _images(entry: CatalogEntry) -> dict[str, CircleIsometry]:
    return {image.generator: image.action for image in entry.generator_images}


def _matches(pattern_key: str, entry: CatalogEntry) -> bool:
    images = _images(entry)
    identity = CircleIsometry.identity()
    if pattern_key == "iris_c6_time_screw":
        return (
            entry.family == "cyclic"
            and entry.domain == "C6"
            and images == {"r": CircleIsometry(Fraction(1, 6), False)}
        )
    if pattern_key == "wave_loom_c5_relay":
        return (
            entry.family == "translation"
            and images
            == {
                "x": CircleIsometry(Fraction(1, 5), False),
                "y": identity,
            }
        )
    if pattern_key == "elastic_d4_choreography":
        return (
            entry.family == "dihedral"
            and entry.domain == "D4"
            and images
            == {
                "r": CircleIsometry(Fraction(1, 4), False),
                "s": CircleIsometry(Fraction(0), True),
            }
        )
    if pattern_key == "liquid_c2_centered_lattice":
        return (
            entry.family == "translation"
            and images
            == {
                "x": CircleIsometry(Fraction(1, 2), False),
                "y": CircleIsometry(Fraction(1, 2), False),
            }
        )
    raise ValueError(f"unknown catalog pattern {pattern_key!r}")


def select_pattern_entries(catalog: Catalog) -> dict[str, CatalogEntry]:
    """Resolve every fixed recipe to exactly one normalized catalog row."""

    selected: dict[str, CatalogEntry] = {}
    for key in PATTERNS:
        matches = [entry for entry in catalog.entries if _matches(key, entry)]
        if len(matches) != 1:
            raise ValueError(
                f"catalog selector for {key!r} matched {len(matches)} rows; expected one"
            )
        selected[key] = matches[0]
    return selected


__all__ = ["select_pattern_entries"]
