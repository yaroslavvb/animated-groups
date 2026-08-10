from __future__ import annotations

import csv
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest

from animated_groups.catalog import (
    CircleIsometry,
    FiniteSpatialGroup,
    PhaseElement,
    build_catalog,
    enumerate_finite_homomorphisms,
    enumerate_translation_characters,
    export_catalog,
    finite_spatial_groups,
    phase_elements,
    select_pattern_entries,
    validate_finite_homomorphism,
)
from animated_groups.catalog.patterns import PATTERNS
from animated_groups.catalog.algebra import evaluate_spatial_word


class PhaseAlgebraTests(unittest.TestCase):
    def test_exact_dihedral_pair_law(self) -> None:
        first = PhaseElement(7, 2, True)
        second = PhaseElement(7, 5, False)
        self.assertEqual(first.compose(second), PhaseElement(7, 4, True))

        first = PhaseElement(7, 2, False)
        second = PhaseElement(7, 5, True)
        self.assertEqual(first.compose(second), PhaseElement(7, 0, True))

    def test_phase_groups_are_associative_with_inverses(self) -> None:
        for modulus in range(2, 13):
            identity = PhaseElement.identity(modulus)
            elements = phase_elements(modulus)
            for element in elements:
                self.assertEqual(element.compose(element.inverse()), identity)
                self.assertEqual(element.inverse().compose(element), identity)
            for first in elements:
                for second in elements:
                    for third in elements:
                        self.assertEqual(
                            first.compose(second).compose(third),
                            first.compose(second.compose(third)),
                        )

    def test_circle_isometries_reduce_shifts_exactly(self) -> None:
        self.assertEqual(
            CircleIsometry(Fraction(6, 8), False),
            CircleIsometry(Fraction(3, 4), False),
        )
        reflection = CircleIsometry(Fraction(1, 3), True)
        self.assertEqual(reflection.compose(reflection), CircleIsometry.identity())


class FiniteEnumerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = build_catalog()

    def test_spatial_presentations_hold_in_every_domain(self) -> None:
        groups = finite_spatial_groups()
        self.assertEqual(tuple(group.key for group in groups), (
            "C2", "C3", "C4", "C6", "D1", "D2", "D3", "D4", "D6",
        ))
        for group in groups:
            assignment = dict(group.generators)
            for relator in group.relators:
                self.assertEqual(
                    evaluate_spatial_word(group, assignment, relator),
                    group.identity,
                    (group.key, relator),
                )

    def test_enumerated_maps_obey_homomorphism_law(self) -> None:
        group = FiniteSpatialGroup("dihedral", 4)
        homomorphisms = enumerate_finite_homomorphisms(group, 6)
        self.assertTrue(homomorphisms)
        for homomorphism in homomorphisms:
            validate_finite_homomorphism(homomorphism)
            for first in group.elements:
                for second in group.elements:
                    self.assertEqual(
                        homomorphism.image(group.multiply(first, second)),
                        homomorphism.image(first).compose(homomorphism.image(second)),
                    )

    def test_catalog_ids_and_normalized_keys_are_unique(self) -> None:
        entries = self.catalog.entries
        self.assertEqual(len(entries), 468)
        self.assertEqual(len(self.catalog.finite_entries), 192)
        self.assertEqual(len(self.catalog.translation_entries), 265)
        self.assertEqual(len(self.catalog.reversible_relay_entries), 11)
        self.assertEqual(len({entry.id for entry in entries}), len(entries))
        self.assertEqual(len({entry.canonical_key for entry in entries}), len(entries))

    def test_point_groups_have_only_crystallographic_phase_rotation_orders(self) -> None:
        self.assertLessEqual(
            {entry.phase_rotation_order for entry in self.catalog.finite_entries},
            {1, 2, 3, 4, 6},
        )

    def test_pattern_selectors_resolve_to_four_unique_catalog_rows(self) -> None:
        selected = select_pattern_entries(self.catalog)
        self.assertEqual(tuple(selected), tuple(PATTERNS))
        self.assertEqual(len({entry.id for entry in selected.values()}), len(PATTERNS))

    def test_c4_to_time_reflection_is_nonsplit(self) -> None:
        fixture = [
            entry
            for entry in self.catalog.entries
            if entry.domain == "C4"
            and len(entry.generator_images) == 1
            and entry.generator_images[0].action == CircleIsometry(Fraction(0), True)
        ]
        self.assertEqual(len(fixture), 1)
        entry = fixture[0]
        self.assertEqual(entry.image_order, 2)
        self.assertEqual(entry.kernel_order, 2)
        self.assertEqual(entry.kernel_elements, ("1", "r^2"))
        self.assertEqual(entry.extension_type, "non_split")
        self.assertTrue(entry.graph_nonproduct)
        self.assertTrue(entry.time_reversing)

    def test_inflated_target_moduli_merge_by_exact_fraction_images(self) -> None:
        fixture = [
            entry
            for entry in self.catalog.translation_entries
            if tuple(image.action.shift for image in entry.generator_images)
            == (Fraction(0), Fraction(1, 2))
        ]
        self.assertEqual(len(fixture), 1)
        self.assertEqual(fixture[0].realized_in_moduli, (2, 4, 6, 8, 10, 12))
        self.assertEqual(fixture[0].target_phase_order, 2)
        self.assertEqual(fixture[0].reduced_phase_order, 2)


class TranslationCatalogTests(unittest.TestCase):
    def test_per_modulus_and_merged_translation_counts(self) -> None:
        expected = (3, 4, 9, 12, 19, 24, 33, 40, 51, 60, 73)
        actual = tuple(
            len(enumerate_translation_characters(modulus))
            for modulus in range(2, 13)
        )
        self.assertEqual(actual, expected)

        catalog = build_catalog()
        self.assertEqual(len(catalog.translation_entries), 265)
        self.assertTrue(all(entry.extension_type == "non_split" for entry in catalog.translation_entries))
        self.assertTrue(all(entry.graph_nonproduct for entry in catalog.translation_entries))

    def test_basis_labels_are_retained_but_d4_orbit_is_reported(self) -> None:
        catalog = build_catalog()

        def find(first: Fraction, second: Fraction):
            return next(
                entry
                for entry in catalog.translation_entries
                if tuple(image.action.shift for image in entry.generator_images)
                == (first, second)
            )

        x_character = find(Fraction(0), Fraction(1, 3))
        y_character = find(Fraction(1, 3), Fraction(0))
        self.assertNotEqual(x_character.id, y_character.id)
        self.assertNotEqual(x_character.canonical_key, y_character.canonical_key)
        self.assertEqual(
            x_character.translation_d4_orbit_key,
            y_character.translation_d4_orbit_key,
        )

    def test_translation_enumeration_is_deterministic(self) -> None:
        first = enumerate_translation_characters(12)
        second = enumerate_translation_characters(12)
        self.assertEqual(first, second)
        self.assertEqual(first, tuple(sorted(first, key=lambda pair: (pair[0].shift, pair[1].shift))))

    def test_all_moduli_have_a_canonical_reversible_pm_relay(self) -> None:
        catalog = build_catalog()
        relays = catalog.reversible_relay_entries
        self.assertEqual(tuple(sorted(entry.order for entry in relays)), tuple(range(2, 13)))
        for entry in relays:
            self.assertTrue(entry.graph_nonproduct)
            self.assertTrue(entry.time_reversing)
            self.assertEqual(entry.image_order, 2 * entry.order)
            self.assertEqual(entry.frame_divisor, entry.order)
            self.assertEqual(entry.phase_rotation_order, entry.order)
            self.assertTrue(entry.quotient_projection_split)
            self.assertFalse(entry.product_lattice_cover_split)
            self.assertEqual(entry.extension_type, "non_split")


class CatalogExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = build_catalog()

    def test_all_exports_are_deterministic_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = export_catalog(self.catalog, root / "first")
            second = export_catalog(self.catalog, root / "second")

            self.assertEqual(set(first), {"json", "csv", "markdown"})
            for format_name in first:
                self.assertEqual(
                    first[format_name].read_bytes(),
                    second[format_name].read_bytes(),
                    format_name,
                )

            payload = json.loads(first["json"].read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertEqual(payload["counts"], {
                "finite": 192,
                "reversible_relay": 11,
                "total": 468,
                "translation": 265,
            })
            self.assertEqual(len(payload["entries"]), len(self.catalog.entries))

            with first["csv"].open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), len(self.catalog.entries))

            markdown = first["markdown"].read_text(encoding="utf-8")
            self.assertTrue(markdown.startswith("# Systematic spacetime-group catalog\n"))
            self.assertIn(self.catalog.entries[0].id, markdown)


if __name__ == "__main__":
    unittest.main()
