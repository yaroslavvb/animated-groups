from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def _classes(attributes: dict[str, str | None]) -> set[str]:
    return set((attributes.get("class") or "").split())


def _normalized_notation(value: str) -> str:
    """Ignore layout whitespace while retaining every mathematical symbol."""

    return "".join(value.split())


class _CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.symmetry_articles = 0
        self.symmetry_figures = 0
        self.motion_images: list[dict[str, str | None]] = []
        self.orbifold_notation: list[str | None] = []
        self.orbifold_tex: list[str] = []
        self.motion_buttons: list[dict[str, str | None]] = []
        self.motion_button_text: list[str] = []
        self.links: list[str] = []
        self._symmetry_articles: list[bool] = []
        self._orbifold_parts: list[str] | None = None
        self._orbifold_tag: str | None = None
        self._button_parts: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        classes = _classes(attributes)

        if tag == "article":
            is_symmetry = "symmetry" in classes
            self._symmetry_articles.append(is_symmetry)
            if is_symmetry:
                self.symmetry_articles += 1
        elif tag == "figure" and any(self._symmetry_articles):
            self.symmetry_figures += 1
        elif tag == "img" and "motion-image" in classes:
            self.motion_images.append(attributes)

        if "orbifold" in classes:
            self.orbifold_notation.append(attributes.get("data-notation"))
            self._orbifold_parts = []
            self._orbifold_tag = tag

        if tag == "button" and "motion-toggle" in classes:
            self.motion_buttons.append(attributes)
            self._button_parts = []

        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self._symmetry_articles:
            self._symmetry_articles.pop()
        if tag == self._orbifold_tag and self._orbifold_parts is not None:
            self.orbifold_tex.append("".join(self._orbifold_parts))
            self._orbifold_parts = None
            self._orbifold_tag = None
        if tag == "button" and self._button_parts is not None:
            self.motion_button_text.append("".join(self._button_parts))
            self._button_parts = None

    def handle_data(self, data: str) -> None:
        if self._orbifold_parts is not None:
            self._orbifold_parts.append(data)
        if self._button_parts is not None:
            self._button_parts.append(data)


class SiteCatalogTests(unittest.TestCase):
    EXPECTED_ORBIFOLDS = (
        "*1• ⟦m ↦ τ1/2⟧",
        "4• ⟦r ↦ τ1/4⟧",
        "∞∞ ⟦a ↦ τ1/3⟧",
        "×× ⟦g(0,b/2) ↦ τ1/2⟧",
        "∞∞ ⟦q(a/2,0) ↦ ι0⟧",
        "4• ⟦r ↦ ι0⟧",
        "*3• ⟦r ↦ τ1/3, m ↦ ι0⟧",
        "6• ⟦r ↦ τ1/6⟧",
        "o ⟦a ↦ τ1/5⟧",
        "*4• ⟦r ↦ τ1/4, m ↦ ι0⟧",
        "o ⟦ℓ(a/2,b/2) ↦ τ1/2⟧",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = _CatalogParser()
        cls.parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
        cls.parser.close()

    def test_linear_catalog_has_eleven_rows_and_three_motifs_each(self) -> None:
        self.assertEqual(self.parser.symmetry_articles, 11)
        self.assertEqual(self.parser.symmetry_figures, 33)
        self.assertEqual(len(self.parser.motion_images), 33)

    def test_motion_images_have_unique_poster_gif_and_video_sources(self) -> None:
        source_sets: list[tuple[str, str, str]] = []
        for attributes in self.parser.motion_images:
            source = attributes.get("src") or ""
            poster = attributes.get("data-poster-src") or ""
            gif = attributes.get("data-motion-src") or ""
            video = attributes.get("data-video-src") or ""
            self.assertEqual(source, poster)
            self.assertTrue(poster.lower().endswith(".webp"), poster)
            self.assertTrue(gif.lower().endswith(".gif"), gif)
            self.assertTrue(video.lower().endswith(".mp4"), video)
            self.assertTrue((ROOT / poster).is_file(), poster)
            self.assertTrue((ROOT / gif).is_file(), gif)
            self.assertTrue((ROOT / video).is_file(), video)

            video_bytes = (ROOT / video).read_bytes()
            self.assertEqual(video_bytes[4:8], b"ftyp", video)
            self.assertGreater(video_bytes.find(b"moov"), 0, video)
            self.assertGreater(video_bytes.find(b"mdat"), 0, video)
            self.assertLess(video_bytes.find(b"moov"), video_bytes.find(b"mdat"), video)
            source_sets.append((poster, gif, video))
        self.assertEqual(len(set(source_sets)), 33)

    @unittest.skipUnless(shutil.which("ffprobe"), "ffprobe is required for MP4 audit")
    def test_every_video_proxy_has_sixty_frames_at_twenty_fps(self) -> None:
        ffprobe = shutil.which("ffprobe")
        assert ffprobe is not None
        for attributes in self.parser.motion_images:
            video = ROOT / (attributes.get("data-video-src") or "")
            result = subprocess.run(
                (
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-count_frames",
                    "-show_entries",
                    "stream=codec_name,width,height,r_frame_rate,nb_read_frames:format=duration",
                    "-of",
                    "json",
                    str(video),
                ),
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            stream = payload["streams"][0]
            self.assertEqual(stream["codec_name"], "h264", video)
            self.assertEqual(stream["r_frame_rate"], "20/1", video)
            self.assertEqual(int(stream["nb_read_frames"]), 60, video)
            self.assertAlmostEqual(float(payload["format"]["duration"]), 3.0, places=3)
            gif = ROOT / (attributes.get("data-motion-src") or "")
            with Image.open(gif) as source:
                expected_size = source.size
            self.assertEqual(
                (int(stream["width"]), int(stream["height"])),
                expected_size,
            )

    def test_every_poster_exactly_matches_its_gif_first_frame(self) -> None:
        for attributes in self.parser.motion_images:
            poster_path = ROOT / (attributes.get("data-poster-src") or "")
            gif_path = ROOT / (attributes.get("data-motion-src") or "")
            with Image.open(gif_path) as motion:
                motion.seek(0)
                expected = motion.convert("RGB")
            with Image.open(poster_path) as poster:
                actual = poster.convert("RGB")

            self.assertEqual(actual.size, expected.size, poster_path)
            self.assertEqual(actual.tobytes(), expected.tobytes(), poster_path)

    def test_motion_button_starts_hidden_as_a_play_action(self) -> None:
        self.assertEqual(len(self.parser.motion_buttons), 1)
        attributes = self.parser.motion_buttons[0]
        self.assertIn("hidden", attributes)
        self.assertNotIn("aria-pressed", attributes)
        self.assertEqual(
            _normalized_notation(self.parser.motion_button_text[0]),
            _normalized_notation("▶ Play all animations"),
        )

    def test_motion_controls_create_seekable_individual_video_players(self) -> None:
        script = (ROOT / "site-controls-v2.js").read_text(encoding="utf-8")
        self.assertIn("document.createElement('video')", script)
        self.assertIn("animation-controls", script)
        self.assertIn("animation-toggle", script)
        self.assertIn("phase-slider", script)
        self.assertIn("slider.min = '0'", script)
        self.assertIn("slider.max = String(FRAME_COUNT - 1)", script)
        self.assertIn("player.video.currentTime = frame / FPS", script)
        self.assertIn("player.slider.addEventListener('input'", script)
        self.assertIn("pausePlayer(player)", script)
        self.assertIn("Stop all animations", script)
        self.assertIn("IntersectionObserver", script)
        self.assertIn("Animation unavailable for", script)
        self.assertIn("if (player.loaded && !player.error)", script)
        self.assertIn("globalButton.disabled = true", script)
        self.assertIn("schedulePhaseUpdates()", script)
        self.assertIn("const playback = player.video.play()", script)
        self.assertIn("playPlayer(player, { userInitiated: true })", script)
        self.assertLess(
            script.index("const playback = player.video.play()"),
            script.index("await Promise.all([loading, playback])"),
        )
        self.assertNotIn("images.every", script)

    def test_legacy_controller_survives_stale_gallery_markup(self) -> None:
        script = (ROOT / "site.js").read_text(encoding="utf-8")
        self.assertIn("images.every((image) => image.dataset.videoSrc)", script)
        self.assertIn("controller.src = 'site-controls-v2.js'", script)
        self.assertIn("image.dataset.motionSrc", script)
        self.assertIn("startLegacyControls", script)

    def test_video_generator_preserves_the_sampled_cycle(self) -> None:
        script = (ROOT / "scripts" / "generate_videos.py").read_text(encoding="utf-8")
        self.assertIn('"-frames:v"', script)
        self.assertIn('"libx264"', script)
        self.assertIn('"+faststart"', script)
        self.assertIn("keyframe_interval", script)

    def test_mathjax_is_pinned_configured_and_does_not_block_controls(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        site_script = '<script src="site-controls-v2.js" defer></script>'
        mathjax_script = (
            '<script src="https://cdn.jsdelivr.net/npm/'
            'mathjax@4.1.3/tex-chtml.js" defer></script>'
        )
        self.assertIn('<script src="mathjax-config.js"></script>', index)
        self.assertIn(site_script, index)
        self.assertIn(mathjax_script, index)
        self.assertLess(index.index(site_script), index.index(mathjax_script))
        self.assertNotIn("site-controls-v2.js?", index)

        config = (ROOT / "mathjax-config.js").read_text(encoding="utf-8")
        self.assertIn("ST:", config)
        self.assertIn("displayOverflow: 'linebreak'", config)
        self.assertIn("inline: true", config)
        self.assertNotIn("assistive-mml", config)

    def test_page_uses_the_white_light_theme(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        styles = (ROOT / "site-controls-v2.css").read_text(encoding="utf-8")
        legacy_styles = (ROOT / "site.css").read_text(encoding="utf-8")
        self.assertIn('<meta name="theme-color" content="#ffffff">', index)
        self.assertIn('href="site-controls-v2.css"', index)
        self.assertEqual(styles, legacy_styles)
        self.assertIn("color-scheme: light", styles)
        self.assertIn("--background: #ffffff", styles)
        self.assertIn(".media img[hidden],\n.media video[hidden]", styles)
        self.assertNotIn("color-scheme: dark", styles)
        self.assertNotIn("#111315", styles)

    def test_ke_wu_connection_and_row_provenance_are_visible(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="ke-wu"', index)
        self.assertIn("https://arxiv.org/abs/2604.05619", index)
        self.assertIn("https://arxiv.org/html/2604.05619v1#S2.E1", index)
        self.assertIn(
            "Two-Dimensional Space-Time Groups: Classification and Applications",
            index,
        )
        self.assertEqual(index.count('class="paper-status"'), 11)
        self.assertEqual(
            index.count("<strong>Ke–Wu coordinate operation.</strong>"),
            4,
        )
        self.assertEqual(
            index.count("<strong>Ke–Wu magnetic point group.</strong>"),
            1,
        )
        self.assertEqual(index.count("<strong>Project construction.</strong>"), 6)

    def test_page_states_its_mathematical_scope_without_exhibit_copy(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(
            '<h1 id="page-title">Visualizations of two-dimensional spacetime groups</h1>',
            index,
        )
        self.assertIn("finite periodic renderings of exact equivariant motif models", index)
        self.assertIn(r"S^1_T=\mathbb R/T\mathbb Z", index)
        self.assertIn("Relation to the Ke–Wu classification", index)

        for informal_copy in (
            "Space and time, coupled",
            ">D3 dihedral choreography<",
            ">C6 kinetic-iris time screw<",
            ">C5 wave-loom relay<",
            ">D4 elastic-square choreography<",
            ">C2 centered-lattice liquid cells<",
            "phase chase",
            "hands one fifth",
        ):
            self.assertNotIn(informal_copy, index)

    def test_spacetime_orbifold_notation_is_complete_ordered_and_tex(self) -> None:
        self.assertEqual(len(self.parser.orbifold_notation), 11)
        self.assertTrue(
            all(
                notation and notation.strip()
                for notation in self.parser.orbifold_notation
            )
        )
        actual = tuple(
            _normalized_notation(notation or "")
            for notation in self.parser.orbifold_notation
        )
        expected = tuple(map(_normalized_notation, self.EXPECTED_ORBIFOLDS))
        self.assertEqual(actual, expected)

        self.assertEqual(len(self.parser.orbifold_tex), 11)
        for raw_tex in self.parser.orbifold_tex:
            expression = raw_tex.strip()
            self.assertTrue(expression)
            self.assertTrue(
                (
                    expression.startswith(r"\(")
                    and expression.endswith(r"\)")
                )
                or (
                    expression.startswith(r"\[")
                    and expression.endswith(r"\]")
                ),
                expression,
            )
            self.assertGreater(len(expression), 4)

    def test_notation_note_is_linked_and_marks_the_extension_as_proposed(self) -> None:
        self.assertTrue(
            any(
                href.partition("#")[0].endswith("docs/orbifold_notation.md")
                for href in self.parser.links
            )
        )
        note = (ROOT / "docs" / "orbifold_notation.md").read_text(encoding="utf-8")
        note_lower = note.lower()
        self.assertIn("proposed", note_lower)
        self.assertIn("not standard", note_lower)


if __name__ == "__main__":
    unittest.main()
