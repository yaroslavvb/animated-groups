from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ColorForwardReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = (ROOT / "future-directions.html").read_text(encoding="utf-8")
        cls.script = (ROOT / "future-directions.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "future-directions.css").read_text(encoding="utf-8")

    def test_main_gallery_links_the_report(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="future-directions.html">Colours</a>', index)

    def test_report_uses_the_correct_repository_and_root_paths(self) -> None:
        self.assertIn("https://github.com/yaroslavvb/animated-groups", self.page)
        for path in (
            "data/color-forward-census.json",
            "data/color-forward-census.csv",
            "data/color-forward-by-orbifold.csv",
            "data/color-forward-manifest.json",
        ):
            self.assertIn(path, self.page)
            self.assertTrue((ROOT / path).is_file(), path)

    def test_report_states_projection_is_not_single_frame_symmetry(self) -> None:
        self.assertIn("Spatial projection is not the symmetry of one frame", self.page)
        self.assertIn("zero-phase kernel H", self.page)
        self.assertIn("17 wallpaper projection categories", self.page)

    def test_visible_audit_uses_orbifold_not_hm_labels(self) -> None:
        self.assertIn('id="audit-title">Audit by plane orbifold</h2>', self.page)
        self.assertIn("row.orbifold", self.script)
        self.assertNotIn("return [row.wallpaper_group", self.script)
        self.assertIn('"orbifold"', self.script)
        self.assertIn("333", self.page)
        self.assertNotIn("wallpaper group p3", self.page)

    def test_all_seventeen_orbifolds_are_available_to_the_renderer(self) -> None:
        payload = json.loads(
            (ROOT / "data" / "color-forward-census.json").read_text(encoding="utf-8")
        )
        expected = [
            "◦", "2222", "**", "××", "*×", "*2222", "22*", "22×",
            "2*22", "442", "*442", "4*2", "333", "*333", "3*3",
            "632", "*632",
        ]
        self.assertEqual(
            [row["orbifold"] for row in payload["by_wallpaper"]],
            expected,
        )
        self.assertEqual(len({row["wallpaper_group"] for row in payload["by_wallpaper"]}), 17)

    def test_tables_remain_horizontally_scrollable(self) -> None:
        self.assertIn(".table-scroll", self.styles)
        self.assertIn("overflow-x: auto", self.styles)
        self.assertIn("min-width: 680px", self.styles)

    def test_orbifold_mirrors_render_as_baseline_book_glyphs(self) -> None:
        self.assertIn("function renderOrbifoldNotation", self.script)
        self.assertIn('star.textContent = "∗"', self.script)
        self.assertIn('star.className = "orbifold-star"', self.script)
        self.assertIn('element.setAttribute("aria-label", notation)', self.script)
        self.assertEqual(self.script.count(
            "firstColumnRenderer: renderOrbifoldNotation"
        ), 2)
        self.assertIn(".orbifold-star {", self.styles)
        self.assertIn('font-family: "STIX Two Math", "Cambria Math"', self.styles)
        self.assertIn("vertical-align: baseline", self.styles)
        self.assertIn("future-directions.css?v=book-orbifold-stars", self.page)
        self.assertIn("future-directions.js?v=book-orbifold-stars", self.page)


if __name__ == "__main__":
    unittest.main()
