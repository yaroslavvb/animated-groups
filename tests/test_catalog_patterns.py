from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
import tempfile
import unittest

from animated_groups.catalog.patterns import (
    PATTERNS,
    advance_slots,
    centered_liquid_step,
    elastic_d4_state,
    iris_c6_state,
    liquid_c2_state,
    reflect_elastic_d4,
    wave_loom_c5_state,
)
from animated_groups.catalog.render import (
    compatible_frame_count,
    render_catalog_gallery,
    render_pattern_frames,
)


class AnalyticPatternTests(unittest.TestCase):
    SAMPLE_PHASES = (0.0, 0.073, 0.251, 0.5, 0.819)

    def assertStatesAlmostEqual(self, first: tuple[object, ...], second: tuple[object, ...]) -> None:
        self.assertEqual(len(first), len(second))
        for actual, expected in zip(first, second):
            self.assertEqual(type(actual), type(expected))
            for field in fields(actual):
                actual_value = getattr(actual, field.name)
                expected_value = getattr(expected, field.name)
                if isinstance(actual_value, float):
                    self.assertAlmostEqual(actual_value, expected_value, places=9, msg=field.name)
                else:
                    self.assertEqual(actual_value, expected_value, field.name)

    def test_registry_has_four_fixed_recipes_and_metadata(self) -> None:
        self.assertEqual(
            tuple(PATTERNS),
            (
                "iris_c6_time_screw",
                "wave_loom_c5_relay",
                "elastic_d4_choreography",
                "liquid_c2_centered_lattice",
            ),
        )
        self.assertEqual(
            {key: recipe.phase_divisor for key, recipe in PATTERNS.items()},
            {
                "iris_c6_time_screw": 6,
                "wave_loom_c5_relay": 5,
                "elastic_d4_choreography": 4,
                "liquid_c2_centered_lattice": 2,
            },
        )
        for key, recipe in PATTERNS.items():
            self.assertEqual(recipe.key, key)
            self.assertTrue(recipe.filename.endswith(".gif"))
            self.assertTrue(recipe.title)
            self.assertIsInstance(recipe.catalog_selector, dict)

    def test_all_analytic_patterns_close_at_one_period(self) -> None:
        for state_function in (
            iris_c6_state,
            wave_loom_c5_state,
            elastic_d4_state,
            liquid_c2_state,
        ):
            self.assertStatesAlmostEqual(state_function(0.0), state_function(1.0))

    def test_c6_iris_rotation_advances_one_sixth_period(self) -> None:
        for phase in self.SAMPLE_PHASES:
            mapped = advance_slots(iris_c6_state(phase), 6)
            target = iris_c6_state(phase + 1.0 / 6.0)
            self.assertStatesAlmostEqual(mapped, target)

    def test_c5_wave_translation_advances_one_fifth_period(self) -> None:
        for phase in self.SAMPLE_PHASES:
            mapped = advance_slots(wave_loom_c5_state(phase), 5)
            target = wave_loom_c5_state(phase + 1.0 / 5.0)
            self.assertStatesAlmostEqual(mapped, target)

    def test_d4_elastic_rotation_and_mirror_time_reversal(self) -> None:
        for phase in self.SAMPLE_PHASES:
            states = elastic_d4_state(phase)
            rotated = advance_slots(states, 4)
            reflected = reflect_elastic_d4(states)
            self.assertStatesAlmostEqual(rotated, elastic_d4_state(phase + 0.25))
            self.assertStatesAlmostEqual(reflected, elastic_d4_state(-phase))

            # On slot indices the spatial generators satisfy M R M = R^-1.
            mrm = reflect_elastic_d4(advance_slots(reflect_elastic_d4(states), 4))
            inverse = advance_slots(advance_slots(advance_slots(states, 4), 4), 4)
            self.assertStatesAlmostEqual(mrm, inverse)

    def test_c2_centered_translation_advances_half_a_period(self) -> None:
        for phase in self.SAMPLE_PHASES:
            mapped = centered_liquid_step(liquid_c2_state(phase))
            target = liquid_c2_state(phase + 0.5)
            self.assertStatesAlmostEqual(mapped, target)


class CatalogPatternGifTests(unittest.TestCase):
    def test_frame_count_rounds_up_to_each_recipe_divisor(self) -> None:
        self.assertEqual(compatible_frame_count(13, 6), 18)
        self.assertEqual(compatible_frame_count(13, 5), 15)
        self.assertEqual(compatible_frame_count(3, 4), 8)
        self.assertEqual(compatible_frame_count(1, 2), 4)

    def test_render_frames_samples_no_duplicate_endpoint(self) -> None:
        frames = render_pattern_frames(
            "iris_c6_time_screw",
            frame_count=12,
            size=240,
            supersample=1,
        )
        self.assertEqual(len(frames), 12)
        self.assertEqual(frames[0].size, (240, 240))
        self.assertIsNotNone(frames[0].getbbox())
        self.assertIsNotNone(frames[-1].getbbox())
        self.assertIsNotNone(frames[0].copy().convert("RGB"))
        self.assertNotEqual(frames[0].tobytes(), frames[-1].tobytes())

    def test_smoke_and_audit_every_catalog_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "catalog"
            audits = render_catalog_gallery(
                output,
                target_frames=12,
                fps=20,
                size=240,
                supersample=1,
            )
            report = json.loads((output / "loop_report.json").read_text(encoding="utf-8"))
            gif_names = {path.name for path in (output / "gifs").glob("*.gif")}

        self.assertEqual(len(audits), len(PATTERNS))
        self.assertTrue(report["all_pass"], report)
        self.assertEqual(gif_names, {recipe.filename for recipe in PATTERNS.values()})
        for audit in audits:
            self.assertTrue(audit.passes, (audit.path, audit.checks))
            self.assertEqual(audit.loop, 0)
            self.assertFalse(audit.first_last_identical)
            self.assertEqual(set(audit.durations_ms), {50})


if __name__ == "__main__":
    unittest.main()
