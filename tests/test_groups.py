from __future__ import annotations

import math
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr

from animated_groups.groups import (
    MotifState,
    diagonal_relay_states,
    dihedral_choreography_states,
    dihedral_reflection_step,
    glide_time_reversal_states,
    glide_time_reversal_step,
    mixed_time_glide_states,
    mixed_time_glide_step,
    reflect_x,
    rotate,
    rotary_time_reversal_states,
    rotary_time_reversal_step,
    sorted_states,
    time_glide_states,
    time_screw_states,
    translate_cell,
)
from animated_groups.cli import main
from animated_groups.rendering import audit_gif, gif_duration_ms, render_frames, save_looping_gif


class StateAssertions(unittest.TestCase):
    def assertAngleAlmostEqual(self, first: float, second: float, places: int = 9) -> None:
        difference = (first - second + math.pi) % (2.0 * math.pi) - math.pi
        self.assertAlmostEqual(difference, 0.0, places=places)

    def assertStateAlmostEqual(self, first: MotifState, second: MotifState) -> None:
        self.assertEqual(first.orbit, second.orbit)
        self.assertAlmostEqual(first.x, second.x, places=9)
        self.assertAlmostEqual(first.y, second.y, places=9)
        self.assertAngleAlmostEqual(first.angle, second.angle)
        self.assertAlmostEqual(first.scale, second.scale, places=9)
        self.assertEqual(first.color, second.color)
        self.assertEqual(first.chirality, second.chirality)
        self.assertAlmostEqual(first.glow, second.glow, places=9)
        self.assertEqual(first.glyph, second.glyph)

    def assertConfigurationsEqual(
        self,
        first: tuple[MotifState, ...],
        second: tuple[MotifState, ...],
    ) -> None:
        first = sorted_states(first)
        second = sorted_states(second)
        self.assertEqual(len(first), len(second))
        for actual, expected in zip(first, second):
            self.assertStateAlmostEqual(actual, expected)


class SpacetimeGroupTests(StateAssertions):
    SAMPLE_PHASES = (0.0, 0.071, 0.239, 0.5, 0.813)

    def test_time_glide_generator(self) -> None:
        for phase in self.SAMPLE_PHASES:
            mapped = tuple(reflect_x(state) for state in time_glide_states(phase))
            target = time_glide_states(phase + 0.5)
            self.assertConfigurationsEqual(mapped, target)

    def test_time_screw_generators(self) -> None:
        for order in (3, 4, 6):
            for phase in self.SAMPLE_PHASES:
                mapped = tuple(rotate(state, order) for state in time_screw_states(phase, order))
                target = time_screw_states(phase + 1.0 / order, order)
                self.assertConfigurationsEqual(mapped, target)

    def test_diagonal_relay_generator(self) -> None:
        for order in (2, 3, 4, 5, 6):
            for phase in self.SAMPLE_PHASES:
                mapped = tuple(translate_cell(state, order) for state in diagonal_relay_states(phase, order))
                target = diagonal_relay_states(phase + 1.0 / order, order)
                self.assertConfigurationsEqual(mapped, target)

    def test_mixed_space_time_glide_generator(self) -> None:
        for phase in self.SAMPLE_PHASES:
            states = mixed_time_glide_states(phase)
            mapped = tuple(mixed_time_glide_step(state) for state in states)
            target = mixed_time_glide_states(phase + 0.5)
            self.assertConfigurationsEqual(mapped, target)
            squared = tuple(
                mixed_time_glide_step(mixed_time_glide_step(state))
                for state in states
            )
            self.assertConfigurationsEqual(squared, states)

    def test_glide_time_reversal_generator(self) -> None:
        for phase in self.SAMPLE_PHASES:
            mapped = tuple(
                glide_time_reversal_step(state)
                for state in glide_time_reversal_states(phase)
            )
            target = glide_time_reversal_states(-phase)
            self.assertConfigurationsEqual(mapped, target)
            squared = tuple(glide_time_reversal_step(state) for state in mapped)
            self.assertConfigurationsEqual(squared, glide_time_reversal_states(phase))

    def test_rotary_time_reversal_is_nonsplit_c4(self) -> None:
        for phase in self.SAMPLE_PHASES:
            states = rotary_time_reversal_states(phase)
            mapped = tuple(rotary_time_reversal_step(state) for state in states)
            self.assertConfigurationsEqual(mapped, rotary_time_reversal_states(-phase))

            # Q^2 is the instantaneous pure 180-degree spatial symmetry.
            squared = tuple(
                rotary_time_reversal_step(rotary_time_reversal_step(state))
                for state in states
            )
            self.assertConfigurationsEqual(squared, states)

    def test_dihedral_choreography_generators(self) -> None:
        for phase in self.SAMPLE_PHASES:
            states = dihedral_choreography_states(phase)
            screw = tuple(rotate(state, 3) for state in states)
            mirror_rewind = tuple(dihedral_reflection_step(state) for state in states)
            self.assertConfigurationsEqual(screw, dihedral_choreography_states(phase + 1.0 / 3.0))
            self.assertConfigurationsEqual(mirror_rewind, dihedral_choreography_states(-phase))

            # Spatial/color actions obey M S M = S^-1.
            msm = tuple(
                dihedral_reflection_step(
                    rotate(dihedral_reflection_step(state), 3)
                )
                for state in states
            )
            inverse_screw = tuple(rotate(rotate(state, 3), 3) for state in states)
            self.assertConfigurationsEqual(msm, inverse_screw)
            mirror_squared = tuple(dihedral_reflection_step(state) for state in mirror_rewind)
            screw_cubed = tuple(rotate(rotate(rotate(state, 3), 3), 3) for state in states)
            self.assertConfigurationsEqual(mirror_squared, states)
            self.assertConfigurationsEqual(screw_cubed, states)

    def test_all_definitions_close_at_one_period(self) -> None:
        self.assertConfigurationsEqual(time_glide_states(0.0), time_glide_states(1.0))
        for order in (3, 4, 6):
            self.assertConfigurationsEqual(time_screw_states(0.0, order), time_screw_states(1.0, order))
        for order in (2, 3, 4, 5, 6):
            self.assertConfigurationsEqual(
                diagonal_relay_states(0.0, order),
                diagonal_relay_states(1.0, order),
            )
        for state_function in (
            mixed_time_glide_states,
            glide_time_reversal_states,
            rotary_time_reversal_states,
            dihedral_choreography_states,
        ):
            self.assertConfigurationsEqual(state_function(0.0), state_function(1.0))

    def test_new_mixed_generators_do_not_factor_at_generic_time(self) -> None:
        phase = 0.137
        cases = (
            (
                mixed_time_glide_states,
                mixed_time_glide_step,
                phase + 0.5,
            ),
            (
                glide_time_reversal_states,
                glide_time_reversal_step,
                -phase,
            ),
            (
                rotary_time_reversal_states,
                rotary_time_reversal_step,
                -phase,
            ),
        )
        for state_function, spatial_step, transformed_phase in cases:
            states = state_function(phase)
            spatial_only = tuple(spatial_step(state) for state in states)
            time_only = state_function(transformed_phase)
            with self.assertRaises(AssertionError):
                self.assertConfigurationsEqual(spatial_only, states)
            with self.assertRaises(AssertionError):
                self.assertConfigurationsEqual(time_only, states)

    def test_relay_has_no_independent_fractional_factors(self) -> None:
        phase = 0.137
        states = diagonal_relay_states(phase, 3)
        translated_only = tuple(
            MotifState(
                orbit=state.orbit,
                x=(state.x + 2.0 / 3.0 + 1.0) % 2.0 - 1.0,
                y=state.y,
                angle=state.angle,
                scale=state.scale,
                color=state.color,
                chirality=state.chirality,
                glow=state.glow,
            )
            for state in states
        )
        time_shifted_only = diagonal_relay_states(phase + 1.0 / 3.0, 3)

        with self.assertRaises(AssertionError):
            self.assertConfigurationsEqual(translated_only, states)
        with self.assertRaises(AssertionError):
            self.assertConfigurationsEqual(time_shifted_only, states)


class GifTests(unittest.TestCase):
    def test_saved_gif_is_infinite_and_has_a_regular_seam(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "glide.gif"
            frames = render_frames(
                "time_glide",
                frame_count=12,
                size=240,
                supersample=1,
            )
            save_looping_gif(frames, path, fps=30)
            audit = audit_gif(path, expected_frames=12, expected_duration_ms=30)

        self.assertTrue(audit.passes, audit.checks)
        self.assertEqual(audit.loop, 0)
        self.assertEqual(audit.frame_count, 12)
        self.assertEqual(set(audit.durations_ms), {30})
        self.assertAlmostEqual(audit.effective_fps, 1000.0 / 30.0)
        self.assertFalse(audit.first_last_identical)

    def test_gif_timing_is_explicitly_quantized_to_centiseconds(self) -> None:
        self.assertEqual(gif_duration_ms(20), 50)
        self.assertEqual(gif_duration_ms(30), 30)
        self.assertEqual(gif_duration_ms(60), 20)
        with self.assertRaises(ValueError):
            gif_duration_ms(101)

    def test_all_new_examples_render_as_regular_infinite_loops(self) -> None:
        examples = (
            "mixed_time_glide",
            "glide_time_reversal",
            "rotary_time_reversal",
            "dihedral_choreography",
        )
        with tempfile.TemporaryDirectory() as directory:
            for example in examples:
                path = Path(directory) / f"{example}.gif"
                frames = render_frames(example, frame_count=12, size=240, supersample=1)
                save_looping_gif(frames, path, fps=20)
                audit = audit_gif(path, expected_frames=12, expected_duration_ms=50)
                self.assertTrue(audit.passes, (example, audit.checks))

    def test_generate_all_rejects_bad_frame_count_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["all", "--frames", "6", "--output-dir", str(output)])
            self.assertEqual(raised.exception.code, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
