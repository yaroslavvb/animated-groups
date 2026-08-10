from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import tempfile
import unittest

from animated_groups.catalog.motif_variants import (
    CATALOG_VARIANT_KEYS,
    VARIANT_STYLES,
    catalog_variant_state,
    render_catalog_variant_frames,
    render_catalog_variant_gallery,
)
from animated_groups.catalog.patterns import (
    PATTERNS,
    advance_slots,
    centered_liquid_step,
    reflect_elastic_d4,
)


class CatalogVariantStateTests(unittest.TestCase):
    SAMPLE_PHASES = (0.0, 0.073, 0.251, 0.5, 0.819)

    def assertStatesAlmostEqual(
        self,
        first: tuple[object, ...],
        second: tuple[object, ...],
    ) -> None:
        self.assertEqual(len(first), len(second))
        for actual, expected in zip(first, second):
            self.assertEqual(type(actual), type(expected))
            for field in fields(actual):
                actual_value = getattr(actual, field.name)
                expected_value = getattr(expected, field.name)
                if isinstance(actual_value, float):
                    self.assertAlmostEqual(actual_value, expected_value, places=9)
                else:
                    self.assertEqual(actual_value, expected_value)

    def test_public_registries_are_complete_and_stable(self) -> None:
        self.assertEqual(
            CATALOG_VARIANT_KEYS,
            (
                "iris_c6_time_screw",
                "wave_loom_c5_relay",
                "elastic_d4_choreography",
                "liquid_c2_centered_lattice",
            ),
        )
        self.assertEqual(VARIANT_STYLES, ("discs", "bars"))
        self.assertEqual(set(CATALOG_VARIANT_KEYS), set(PATTERNS))

    def test_all_variant_states_are_one_periodic(self) -> None:
        for key in CATALOG_VARIANT_KEYS:
            self.assertStatesAlmostEqual(
                catalog_variant_state(key, 0.0),
                catalog_variant_state(key, 1.0),
            )

    def test_cyclic_generator_identities_are_preserved(self) -> None:
        for key, order in (
            ("iris_c6_time_screw", 6),
            ("wave_loom_c5_relay", 5),
        ):
            for phase in self.SAMPLE_PHASES:
                self.assertStatesAlmostEqual(
                    advance_slots(catalog_variant_state(key, phase), order),
                    catalog_variant_state(key, phase + 1.0 / order),
                )

    def test_d4_rotation_and_mirror_time_reversal_are_preserved(self) -> None:
        key = "elastic_d4_choreography"
        for phase in self.SAMPLE_PHASES:
            states = catalog_variant_state(key, phase)
            self.assertStatesAlmostEqual(
                advance_slots(states, 4),
                catalog_variant_state(key, phase + 0.25),
            )
            self.assertStatesAlmostEqual(
                reflect_elastic_d4(states),
                catalog_variant_state(key, -phase),
            )

    def test_centered_translation_identity_is_preserved(self) -> None:
        key = "liquid_c2_centered_lattice"
        for phase in self.SAMPLE_PHASES:
            self.assertStatesAlmostEqual(
                centered_liquid_step(catalog_variant_state(key, phase)),
                catalog_variant_state(key, phase + 0.5),
            )


class CatalogVariantRenderTests(unittest.TestCase):
    def test_every_key_and_style_renders_distinct_nonempty_rgb_frames(self) -> None:
        for key in CATALOG_VARIANT_KEYS:
            frame_count = 2 * PATTERNS[key].phase_divisor
            rendered = {}
            for style in VARIANT_STYLES:
                frames = render_catalog_variant_frames(
                    key,
                    style,
                    frame_count=frame_count,
                    size=96,
                    supersample=1,
                )
                self.assertEqual(len(frames), frame_count)
                self.assertTrue(all(frame.size == (96, 96) for frame in frames))
                self.assertTrue(all(frame.mode == "RGB" for frame in frames))
                self.assertIsNotNone(frames[0].getbbox())
                self.assertNotEqual(frames[0].tobytes(), frames[-1].tobytes())
                rendered[style] = frames[0].tobytes()
            self.assertNotEqual(rendered["discs"], rendered["bars"])

    def test_invalid_requests_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            render_catalog_variant_frames("missing", "discs")
        with self.assertRaises(ValueError):
            render_catalog_variant_frames(CATALOG_VARIANT_KEYS[0], "triangles")
        with self.assertRaises(ValueError):
            render_catalog_variant_frames(CATALOG_VARIANT_KEYS[0], "discs", frame_count=11)
        with self.assertRaises(ValueError):
            render_catalog_variant_frames(
                CATALOG_VARIANT_KEYS[0],
                "discs",
                frame_count=12,
                size=31,
            )

    def test_small_gallery_gifs_pass_loop_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "variants"
            audits = render_catalog_variant_gallery(
                output,
                target_frames=12,
                fps=20,
                size=120,
                supersample=1,
            )
            names = {path.name for path in output.glob("*.gif")}

        self.assertEqual(len(audits), 8)
        self.assertEqual(
            names,
            {
                f"{key}__{style}.gif"
                for key in CATALOG_VARIANT_KEYS
                for style in VARIANT_STYLES
            },
        )
        for audit in audits:
            self.assertTrue(audit.passes, (audit.path, audit.checks))
            self.assertEqual(audit.loop, 0)
            self.assertFalse(audit.first_last_identical)
            self.assertEqual(set(audit.durations_ms), {50})


if __name__ == "__main__":
    unittest.main()
