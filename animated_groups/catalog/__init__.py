"""Systematic exact catalog of finite phase actions for looping animations."""

from .algebra import (
    CircleIsometry,
    FiniteSpatialGroup,
    PhaseElement,
    SpatialElement,
    finite_spatial_groups,
    phase_elements,
)
from .enumerate import (
    Catalog,
    CatalogEntry,
    FiniteHomomorphism,
    GeneratorImage,
    build_catalog,
    enumerate_finite_homomorphisms,
    enumerate_translation_characters,
    translation_d4_orbit_key,
    validate_finite_homomorphism,
)
from .export import (
    catalog_to_dict,
    export_catalog,
    write_catalog_csv,
    write_catalog_json,
    write_catalog_markdown,
)
from .selection import select_pattern_entries

__all__ = [
    "Catalog",
    "CatalogEntry",
    "CircleIsometry",
    "FiniteHomomorphism",
    "FiniteSpatialGroup",
    "GeneratorImage",
    "PhaseElement",
    "SpatialElement",
    "build_catalog",
    "catalog_to_dict",
    "enumerate_finite_homomorphisms",
    "enumerate_translation_characters",
    "export_catalog",
    "finite_spatial_groups",
    "phase_elements",
    "select_pattern_entries",
    "translation_d4_orbit_key",
    "validate_finite_homomorphism",
    "write_catalog_csv",
    "write_catalog_json",
    "write_catalog_markdown",
]
