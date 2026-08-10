from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from animated_groups.groups import MotifState
from animated_groups.motif_variants import (
    LEGACY_EXAMPLES,
    VARIANT_STYLES,
    render_legacy_variant_frames,
    render_legacy_variant_gallery,
)


EXPECTED_KEYS = (
    "time_glide",
    "time_screw",
    "diagonal_relay",
    "mixed_time_glide",
    "glide_time_reversal",
    "rotary_time_reversal",
    "dihedral_choreography",
)


class MotifVariantTests(unittest.TestCase):
    def assertStateClose(self, first: MotifState, second: MotifState) -> None:
        self.assertEqual(first.orbit, second.orbit)
        self.assertAlmostEqual(first.x, second.x, places=9)
        self.assertAlmostEqual(first.y, second.y, places=9)
        angle_delta = (first.angle - second.angle + math.pi) % (2.0 * math.pi) - math.pi
        self.assertAlmostEqual(angle_delta, 0.0, places=9)
        self.assertAlmostEqual(first.scale, second.scale, places=9)
        self.assertEqual(first.color, second.color)
        self.assertEqual(first.chirality, second.chirality)
        self.assertAlmostEqual(first.glow, second.glow, places=9)

    def test_registry_is_stable_and_complete(self) -> None:
        self.assertEqual(tuple(LEGACY_EXAMPLES), EXPECTED_KEYS)
        self.assertEqual(VARIANT_STYLES, ("discs", "bars"))
        self.assertEqual(
            tuple(metadata.divisor for metadata in LEGACY_EXAMPLES.values()),
            (2, 4, 3, 2, 2, 4, 3),
        )

    def test_all_fourteen_combinations_render(self) -> None:
        for example, metadata in LEGACY_EXAMPLES.items():
            frame_count = 2 * metadata.divisor
            for style in VARIANT_STYLES:
                frames = render_legacy_variant_frames(
                    example,
                    style,
                    frame_count=frame_count,
                    size=96,
                    supersample=1,
                )
                self.assertEqual(len(frames), frame_count)
                self.assertTrue(all(frame.mode == "RGB" for frame in frames))
                self.assertTrue(all(frame.size == (96, 96) for frame in frames))

    def test_registry_states_close_at_the_exact_period(self) -> None:
        for metadata in LEGACY_EXAMPLES.values():
            start = sorted(metadata.state_function(0.0), key=lambda state: state.orbit)
            finish = sorted(metadata.state_function(1.0), key=lambda state: state.orbit)
            self.assertEqual(len(start), len(finish))
            for first, second in zip(start, finish):
                self.assertStateClose(first, second)

    def test_frame_validation_preserves_sampling_divisors(self) -> None:
        with self.assertRaisesRegex(ValueError, "divisible"):
            render_legacy_variant_frames("time_screw", "discs", frame_count=10, size=96)
        with self.assertRaisesRegex(ValueError, "unknown motif style"):
            render_legacy_variant_frames("time_glide", "trail", frame_count=4, size=96)

    def test_small_gallery_gifs_decode_as_infinite_regular_loops(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audits = render_legacy_variant_gallery(
                directory,
                target_frames=8,
                fps=20,
                size=96,
                supersample=1,
            )
            self.assertEqual(len(audits), 14)
            self.assertTrue(all(audit.passes for audit in audits), [
                (Path(audit.path).name, audit.checks, audit.seam_ratio)
                for audit in audits
                if not audit.passes
            ])
            self.assertTrue(all(audit.loop == 0 for audit in audits))
            self.assertTrue(all(not audit.first_last_identical for audit in audits))
            self.assertEqual(
                {path.name for path in Path(directory).glob("*.gif")},
                {
                    f"{example}__{style}.gif"
                    for example in EXPECTED_KEYS
                    for style in VARIANT_STYLES
                },
            )
            with Image.open(Path(directory) / "time_screw__bars.gif") as image:
                self.assertEqual(image.n_frames, 8)
                self.assertEqual(image.info.get("loop"), 0)


if __name__ == "__main__":
    unittest.main()
