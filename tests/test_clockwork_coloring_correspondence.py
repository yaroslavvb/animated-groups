from __future__ import annotations

from collections import Counter
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_clockwork_coloring_correspondence as correspondence  # noqa: E402
import generate_tos_book_excerpts as book_excerpts  # noqa: E402


class CorrespondenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.section_ids: list[str] = []
        self.family_ids: list[str] = []
        self.empty_family_ids: list[str] = []
        self.trivial_product_ids: list[str] = []
        self.tabbar_count = 0
        self.tabs: list[tuple[str, str, str]] = []
        self.catalog_links: list[str] = []
        self.plate_images: list[tuple[str, str, str, str]] = []
        self.book_links: list[tuple[str, str, str]] = []
        self.book_excerpt_links: list[dict[str, str | None]] = []
        self.book_dialog_ids: list[str] = []
        self.book_excerpt_images: list[dict[str, str | None]] = []
        self.film_group_ids: list[str] = []
        self.canvases: list[tuple[str, str, str]] = []
        self.buttons: list[tuple[bool, str, str | None]] = []
        self.sliders: list[tuple[bool, str, str, str | None]] = []
        self.scripts: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "section" and "correspondence-entry" in classes:
            self.section_ids.append(attributes.get("id", ""))
        if tag == "section" and "wallpaper-family" in classes:
            self.family_ids.append(attributes.get("id", ""))
            if "is-empty" in classes:
                self.empty_family_ids.append(attributes.get("id", ""))
        if tag == "p" and "data-trivial-product" in attributes:
            self.trivial_product_ids.append(attributes.get("id", ""))
        if tag == "nav" and "clockwork-tabbar" in classes:
            self.tabbar_count += 1
        if tag == "a" and "data-clockwork-tab" in attributes:
            self.tabs.append(
                (
                    attributes.get("id", ""),
                    attributes.get("href", ""),
                    attributes.get("data-panel-id", ""),
                )
            )
        if tag == "a" and (attributes.get("href") or "").startswith(
            correspondence.CATALOG_ROOT
        ):
            self.catalog_links.append(attributes["href"] or "")
        if tag == "a" and "book-page-link" in classes:
            self.book_links.append(
                (
                    attributes.get("href", ""),
                    attributes.get("data-printed-page", ""),
                    attributes.get("data-pdf-page", ""),
                )
            )
        if tag == "a" and attributes.get("data-book-excerpt"):
            self.book_excerpt_links.append(attributes)
        if tag == "dialog" and "book-excerpt-dialog" in classes:
            self.book_dialog_ids.append(attributes.get("id", ""))
        if tag == "img" and "data-book-excerpt-image" in attributes:
            self.book_excerpt_images.append(attributes)
        if tag == "figure" and "clockwork-film" in classes:
            self.film_group_ids.append(attributes.get("data-group-id", ""))
        if tag == "canvas" and "clockwork-canvas" in classes:
            self.canvases.append(
                (
                    attributes.get("id", ""),
                    attributes.get("width", ""),
                    attributes.get("height", ""),
                )
            )
        if tag == "button" and "data-film-toggle" in attributes:
            self.buttons.append(
                (
                    "disabled" in attributes,
                    attributes.get("aria-pressed", ""),
                    attributes.get("aria-controls"),
                )
            )
        if tag == "input" and "data-film-slider" in attributes:
            self.sliders.append(
                (
                    "disabled" in attributes,
                    attributes.get("value", ""),
                    attributes.get("type", ""),
                    attributes.get("id"),
                )
            )
        if tag == "script":
            self.scripts.append(
                (attributes.get("src", ""), attributes.get("type", ""))
            )
        if tag == "img" and (attributes.get("src") or "").startswith(
            "output/clockwork-colorings/"
        ):
            self.plate_images.append(
                (
                    attributes.get("src", ""),
                    attributes.get("alt", ""),
                    attributes.get("width", ""),
                    attributes.get("height", ""),
                )
            )


class ClockworkColoringCorrespondenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(correspondence.DATA.read_text(encoding="utf-8"))
        cls.page = correspondence.PAGE.read_text(encoding="utf-8")
        cls.parser = CorrespondenceParser()
        cls.parser.feed(cls.page)
        cls.display_groups = [
            group
            for base in correspondence.BASE_ORDER
            for group in cls.payload["groups"]
            if group["parent"]["hm"] == base and group["clock_order"] > 1
        ]
        cls.trivial_groups = [
            group
            for base in correspondence.BASE_ORDER
            for group in cls.payload["groups"]
            if group["parent"]["hm"] == base and group["clock_order"] == 1
        ]

    def test_68_record_source_renders_exactly_51_nontrivial_sections(self) -> None:
        groups = self.payload["groups"]
        manifest = json.loads(correspondence.MANIFEST.read_text(encoding="utf-8"))
        ids = [group["id"] for group in groups]
        display_ids = [group["id"] for group in self.display_groups]
        trivial_ids = [group["id"] for group in self.trivial_groups]
        self.assertEqual(len(groups), 68)
        self.assertEqual(len(display_ids), correspondence.DISPLAYED_GROUP_COUNT)
        self.assertEqual(len(trivial_ids), correspondence.OMITTED_TRIVIAL_COUNT)
        self.assertEqual(self.parser.section_ids, display_ids)
        self.assertTrue(set(display_ids).isdisjoint(trivial_ids))
        self.assertEqual(self.parser.trivial_product_ids, trivial_ids)
        self.assertEqual(ids, [group["id"] for group in manifest["groups"]])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            [group["parent"]["hm"] for group in self.trivial_groups],
            list(correspondence.BASE_ORDER),
        )
        for group in self.trivial_groups:
            self.assertTrue(group["product"])
            self.assertEqual(group["clock_order"], 1)
            self.assertEqual(group["parent"], group["kernel"])

    def test_17_wallpaper_sections_have_tabs_only_for_nontrivial_groups(self) -> None:
        self.assertEqual(
            self.parser.family_ids,
            [f"wallpaper-{base}" for base in correspondence.BASE_ORDER],
        )
        display_ids = [group["id"] for group in self.display_groups]
        self.assertEqual(
            self.parser.tabs,
            [(f"tab-{group_id}", f"#{group_id}", group_id) for group_id in display_ids],
        )
        self.assertEqual(self.parser.tabbar_count, 14)
        self.assertEqual(
            self.parser.empty_family_ids,
            ["wallpaper-p1", "wallpaper-pm", "wallpaper-pg"],
        )
        for base in correspondence.BASE_ORDER:
            summary, note = correspondence.WALLPAPER_SUMMARIES[base]
            self.assertIn(escape(summary), self.page)
            self.assertIn(escape(note), self.page)

        self.assertIn("51 nontrivial forward groups", self.page)
        self.assertIn("17 one-colour products omitted", self.page)
        self.assertIn("No nontrivial forward lift occurs", self.page)
        self.assertIn("Nontrivial orders · none", self.page)

        script = (ROOT / "clockwork-coloring-correspondence.js").read_text(encoding="utf-8")
        self.assertIn("initializeClockworkTabs", script)
        self.assertIn('setAttribute("role", "tablist")', script)
        self.assertIn('setAttribute("role", "tab")', script)
        self.assertIn('setAttribute("role", "tabpanel")', script)
        self.assertIn('event.key === "ArrowRight"', script)
        self.assertIn('event.key === "Home"', script)
        self.assertIn('window.addEventListener("hashchange"', script)
        self.assertIn('window.addEventListener("popstate"', script)

    def test_every_row_has_an_exact_forward_catalog_deep_link(self) -> None:
        expected = [
            f"{correspondence.CATALOG_ROOT}#{group['id']}"
            for group in self.display_groups
        ]
        self.assertEqual(self.parser.catalog_links, expected)

    def test_tos_notation_and_clock_orders_are_complete(self) -> None:
        groups = self.payload["groups"]
        self.assertEqual(len(correspondence.BOOK_TWO_FOLD_SIGNATURE_BY_TYPE), 36)
        self.assertEqual(len(correspondence.BOOK_HIGHER_SIGNATURE_BY_ID), 15)
        counts = Counter(group["clock_order"] for group in groups)
        self.assertEqual(
            {n: counts.get(n, 0) for n in range(1, 7)},
            correspondence.EXPECTED_ORDER_COUNTS,
        )
        for group in groups:
            self.assertTrue(group["parent"]["orbifold"])
            self.assertTrue(group["kernel"]["orbifold"])
            self.assertEqual(
                group["tos_notation"],
                correspondence.tos_notation(
                    group["parent"]["orbifold"],
                    group["kernel"]["orbifold"],
                    group["clock_order"],
                ),
            )
            self.assertEqual(
                group["book_color_signature"],
                correspondence.book_color_signature(
                    group["id"],
                    group["parent"]["orbifold"],
                    group["tos_notation"],
                    group["clock_order"],
                ),
            )
            self.assertNotIn("//", group["tos_notation"])
            if group["parent"]["hm"] == "p1":
                self.assertEqual(group["parent"]["orbifold"], "◦")
            if group["kernel"]["hm"] == "p1":
                self.assertEqual(group["kernel"]["orbifold"], "◦")
            self.assertEqual(len(group["phase_residues"]), group["clock_order"])
        for group in self.display_groups:
            self.assertIn(escape(group["clockwork_description"]), self.page)
            self.assertIn(escape(group["coloring_description"]), self.page)

        g60 = next(group for group in groups if group["id"] == "g60")
        self.assertEqual(g60["book_color_signature"], "*¹2²2¹2²2")
        self.assertIn(
            '*<sup>1</sup>2<sup>2</sup>2<sup>1</sup>2<sup>2</sup>2',
            self.page,
        )
        self.assertIn(
            '<span class="clockwork-symbol">*2<sub>1</sub>~2<sub>1</sub>2<sub>1</sub>~2<sub>1</sub></span>',
            self.page,
        )

    def test_visible_copy_is_orbifold_first_not_crystallographic(self) -> None:
        forbidden_terms = (
            "classified in",
            "triclinic",
            "monoclinic",
            "orthorhombic",
            "tetragonal",
            "trigonal",
            "hexagonal",
            "bravais",
            "lattice",
            "symmorphic",
            "p31m/3 p3m1",
        )
        page_lower = self.page.lower()
        for term in forbidden_terms:
            self.assertNotIn(term, page_lower)

        self.assertNotIn('class="family-hm"', self.page)
        self.assertNotIn('class="chip-hm"', self.page)
        for conventional_name in correspondence.BASE_ORDER:
            self.assertNotIn(f"({conventional_name})", self.page)

        self.assertEqual(self.page.count("Orbifold family"), 17)
        self.assertEqual(self.page.count("Projected group G"), 51)
        self.assertEqual(self.page.count("Colour-fixing subgroup K"), 51)
        self.assertEqual(self.page.count("Static perfect-colouring plate"), 51)
        self.assertIn("Jump to an underlying orbifold signature", self.page)

        for group in self.payload["groups"]:
            self.assertTrue({"system", "bravais", "symmorphic"} <= group.keys())
            self.assertNotIn("classified in", group["clockwork_description"].lower())
            self.assertIn(
                f"orbifold signature {group['parent']['orbifold']}",
                group["clockwork_description"],
            )
            if group["clock_order"] > 1:
                self.assertIn(
                    f"orbifold signature {group['kernel']['orbifold']}",
                    group["coloring_description"],
                )

    def test_every_row_has_a_book_page_and_honest_coverage_status(self) -> None:
        groups = self.payload["groups"]
        statuses = Counter(group["book_audit"]["status"] for group in groups)
        self.assertEqual(dict(statuses), correspondence.EXPECTED_BOOK_AUDIT_COUNTS)
        self.assertEqual(
            self.payload["meta"]["book_audit_counts"],
            correspondence.EXPECTED_BOOK_AUDIT_COUNTS,
        )
        expected_primary = []
        for group in self.display_groups:
            primary = [
                reference
                for reference in group["book_audit"]["references"]
                if reference["role"] == "primary"
            ]
            self.assertEqual(len(primary), 1, group["id"])
            reference = primary[0]
            expected_primary.append(
                (
                    reference["url"],
                    str(reference["printed_page"]),
                    str(reference["pdf_page"]),
                )
            )
            self.assertEqual(reference["pdf_page"], reference["printed_page"] + 19)
        self.assertEqual(self.parser.book_links, expected_primary)

        for group in groups:
            order = group["clock_order"]
            audit = group["book_audit"]
            if order == 2:
                self.assertIn(group["tos_notation"], correspondence.TOS_TWO_FOLD_TYPES)
                self.assertEqual(audit["status"], "direct-table")
            elif order == 3 and group["id"] != "g234":
                self.assertIn(
                    group["tos_notation"], correspondence.TOS_THREE_FOLD_DIRECT_TYPES
                )
                self.assertEqual(audit["status"], "direct-table")
            elif order in (4, 6):
                self.assertEqual(audit["status"], "composite-extension")
                self.assertEqual(len(audit["prime_chain"]), 2)
                self.assertIn(group["id"], correspondence.COMPOSITE_BOOK_CHAINS)

        exceptional = next(group for group in groups if group["id"] == "g234")
        self.assertEqual(exceptional["tos_notation"], "3*3³/*333")
        self.assertEqual(exceptional["book_audit"]["status"], "internal-discrepancy")
        self.assertEqual(
            [reference["printed_page"] for reference in exceptional["book_audit"]["references"]],
            [164, 156, 158],
        )
        self.assertEqual(
            exceptional["book_audit"]["independent_reference"]["url"],
            correspondence.FARRIS_URL,
        )

    def test_all_book_links_open_exact_annotated_excerpts_with_external_fallbacks(self) -> None:
        expected_references = []
        for group in self.display_groups:
            expected_references.extend(group["book_audit"]["references"])
            for step in group["book_audit"]["prime_chain"]:
                expected_references.append(
                    {
                        "url": step["url"],
                        "printed_page": step["printed_page"],
                        "pdf_page": step["pdf_page"],
                        "excerpt_key": step["excerpt_key"],
                    }
                )

        self.assertEqual(len(expected_references), 80)
        self.assertEqual(len(self.parser.book_excerpt_links), 80)
        for attributes, reference in zip(self.parser.book_excerpt_links, expected_references):
            excerpt = correspondence.BOOK_EXCERPTS[reference["excerpt_key"]]
            self.assertEqual(attributes.get("href"), reference["url"])
            self.assertEqual(attributes.get("data-printed-page"), str(reference["printed_page"]))
            self.assertEqual(attributes.get("data-pdf-page"), str(reference["pdf_page"]))
            self.assertEqual(attributes.get("data-book-excerpt"), reference["excerpt_key"])
            self.assertEqual(attributes.get("data-book-image"), excerpt["image"])
            self.assertEqual(attributes.get("data-book-title"), excerpt["title"])
            self.assertEqual(attributes.get("data-book-context"), excerpt["context"])
            self.assertEqual(attributes.get("data-book-alt"), excerpt["alt"])
            self.assertEqual(attributes.get("aria-haspopup"), "dialog")
            self.assertEqual(attributes.get("aria-controls"), "book-excerpt-dialog")

        expected_excerpt_keys = {reference["excerpt_key"] for reference in expected_references}
        self.assertEqual(len(expected_excerpt_keys), 44)
        self.assertEqual(
            {attributes["data-book-excerpt"] for attributes in self.parser.book_excerpt_links},
            expected_excerpt_keys,
        )

    def test_the_single_accessible_dialog_lazy_loads_62_contextual_watermarked_webps(self) -> None:
        self.assertEqual(self.parser.book_dialog_ids, ["book-excerpt-dialog"])
        self.assertEqual(len(self.parser.book_excerpt_images), 1)
        self.assertNotIn("src", self.parser.book_excerpt_images[0])
        self.assertEqual(len(correspondence.BOOK_EXCERPTS), 62)
        for key, excerpt in correspondence.BOOK_EXCERPTS.items():
            path = ROOT / excerpt["image"]
            self.assertTrue(path.is_file(), key)
            self.assertEqual(excerpt["pdf_page"], excerpt["printed_page"] + 19)
            focus_x, focus_y, focus_width, focus_height = excerpt["crop"]
            context_x, context_y, context_width, context_height = (
                book_excerpts.expanded_crop(excerpt["crop"])
            )
            highlight_x, highlight_y, highlight_width, highlight_height = excerpt["highlight"]

            self.assertGreaterEqual(
                context_width * context_height,
                focus_width * focus_height * 5,
                key,
            )
            self.assertGreaterEqual(context_x, 0, key)
            self.assertGreaterEqual(context_y, 0, key)
            self.assertLessEqual(context_x + context_width, book_excerpts.PDF_WIDTH, key)
            self.assertLessEqual(context_y + context_height, book_excerpts.PDF_HEIGHT, key)
            self.assertLessEqual(context_x, focus_x, key)
            self.assertLessEqual(context_y, focus_y, key)
            self.assertGreaterEqual(context_x + context_width, focus_x + focus_width, key)
            self.assertGreaterEqual(context_y + context_height, focus_y + focus_height, key)
            self.assertLessEqual(context_x, highlight_x, key)
            self.assertLessEqual(context_y, highlight_y, key)
            self.assertGreaterEqual(
                context_x + context_width,
                highlight_x + highlight_width,
                key,
            )
            self.assertGreaterEqual(
                context_y + context_height,
                highlight_y + highlight_height,
                key,
            )
            with Image.open(path) as image:
                self.assertEqual(image.format, "WEBP")
                width, height = image.size
            content_width = width - 24
            content_height = height - 78
            focus_pixel_area = (
                focus_width * book_excerpts.RENDER_DPI / 72
                * focus_height * book_excerpts.RENDER_DPI / 72
            )
            self.assertGreaterEqual(content_width * content_height, focus_pixel_area * 5, key)
            self.assertLessEqual(
                width,
                book_excerpts.PDF_WIDTH * book_excerpts.RENDER_DPI / 72 + 24,
                key,
            )
            self.assertLessEqual(
                height,
                book_excerpts.PDF_HEIGHT * book_excerpts.RENDER_DPI / 72 + 78,
                key,
            )

        self.assertIn("© COPYRIGHTED EXCERPT", self.page)
        self.assertIn("not a complete page", self.page)
        self.assertIn("at least five times the original focus area", self.page)
        self.assertIn("data-book-zoom-toggle", self.page)
        script = (ROOT / "clockwork-coloring-correspondence.js").read_text(encoding="utf-8")
        self.assertIn("initializeBookExcerptDialog", script)
        self.assertIn("typeof dialog.showModal", script)
        self.assertIn('dialog.dataset.mode = supportsNativeDialog ? "native" : "fallback"', script)
        self.assertIn('dialog.classList.add("is-fallback-open")', script)
        self.assertIn('document.querySelectorAll("a[data-book-excerpt]")', script)
        self.assertIn('event.key === "Escape"', script)
        self.assertIn("event.metaKey", script)
        self.assertIn("opener.focus()", script)
        self.assertIn("function setZoom(actualSize)", script)
        self.assertIn('media.dataset.zoom = actualSize ? "actual" : "fit"', script)
        self.assertIn("media.scrollTop = 0", script)
        excerpt_script = (ROOT / "scripts" / "generate_tos_book_excerpts.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('WATERMARK = "© COPYRIGHTED EXCERPT"', excerpt_script)
        self.assertIn('highlight = _box(spec["highlight"]', excerpt_script)

    def test_inverse_clock_pairs_explain_68_to_64(self) -> None:
        paired_rows = {
            group["id"]: group["inverse_clock_mate"]
            for group in self.payload["groups"]
            if group["inverse_clock_mate"]
        }
        self.assertEqual(paired_rows, correspondence.INVERSE_CLOCK_MATE)
        unordered = {frozenset((group_id, mate)) for group_id, mate in paired_rows.items()}
        self.assertEqual(len(unordered), 4)
        self.assertEqual(
            self.payload["meta"]["traditional_color_classes_after_clock_inversion"],
            64,
        )
        self.assertEqual(len(self.display_groups) - len(unordered), 47)
        self.assertIn("47 nontrivial", self.page)

    def test_every_static_plate_exists_and_contains_its_phase_palette(self) -> None:
        self.assertEqual(len(self.parser.plate_images), correspondence.DISPLAYED_GROUP_COUNT)
        by_path = {group["image"]: group for group in self.payload["groups"]}
        displayed_paths = {group["image"] for group in self.display_groups}
        self.assertEqual(
            {relative for relative, _alt, _width, _height in self.parser.plate_images},
            displayed_paths,
        )
        for relative, alt, width, height in self.parser.plate_images:
            self.assertIn(relative, by_path)
            self.assertTrue(alt)
            self.assertEqual((width, height), ("720", "420"))
        for relative, group in by_path.items():
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            with Image.open(path) as image:
                self.assertEqual(image.format, "WEBP")
                self.assertEqual(image.size, (720, 420))
                colors = {
                    color
                    for _count, color in image.convert("RGB").getcolors(
                        maxcolors=720 * 420
                    ) or []
                }
            expected_colors = {
                tuple(bytes.fromhex(residue["color"].lstrip("#")))
                for residue in group["phase_residues"]
            }
            self.assertTrue(expected_colors.issubset(colors), relative)

    def test_every_live_phase_circle_meets_the_measured_reference_size(self) -> None:
        geometry_module = ROOT / "clockwork-coloring-geometry.js"
        self.assertTrue(geometry_module.is_file())
        node_script = r"""
import fs from "node:fs";
import {
  MIN_PHASE_CIRCLE_DIAMETER_PX,
  buildClockworkGeometry,
} from "./clockwork-coloring-geometry.js";
const payload = JSON.parse(
  fs.readFileSync("data/clockwork-coloring-correspondence.json", "utf8"),
);
const sizes = [[507, 296], [411, 240], [325, 190], [260, 152]];
const measurements = [];
for (const group of payload.groups.filter((record) => record.clock_order > 1)) {
  for (const [width, height] of sizes) {
    const geometry = buildClockworkGeometry(group.render, width, height, 1);
    measurements.push({
      id: group.id,
      width,
      height,
      diameter: geometry.circleDiameter,
    });
  }
}
process.stdout.write(JSON.stringify({
  floor: MIN_PHASE_CIRCLE_DIAMETER_PX,
  measurements,
}));
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["floor"], correspondence.MIN_VISIBLE_MOTIF_DIAMETER_PX)
        self.assertEqual(
            len(report["measurements"]),
            correspondence.DISPLAYED_GROUP_COUNT * 4,
        )
        for measurement in report["measurements"]:
            self.assertGreaterEqual(
                measurement["diameter"] + 1e-6,
                report["floor"],
                f"{measurement['id']} at {measurement['width']}×{measurement['height']}",
            )

        controller = (ROOT / "clockwork-coloring-correspondence.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('from "./clockwork-coloring-geometry.js"', controller)
        self.assertIn("buildClockworkGeometry(this.record.render", controller)
        self.assertNotIn("MIN_CELLS", controller)

    def test_every_static_plate_uses_the_same_reference_scale(self) -> None:
        minimum_visible = float("inf")
        for group in self.display_groups:
            _b1, _b2, radius, _ranges = correspondence._site_geometry(
                group["render"],
                correspondence.IMAGE_WIDTH * correspondence.ANTIALIAS,
                correspondence.IMAGE_HEIGHT * correspondence.ANTIALIAS,
            )
            output_radius = radius / correspondence.ANTIALIAS
            self.assertGreaterEqual(
                output_radius + 1e-6,
                correspondence.PLATE_MIN_MOTIF_RADIUS_PX,
                group["id"],
            )
            visible_diameter = (
                correspondence.PLATE_MOTIF_DIAMETER_FACTOR
                * output_radius
                * correspondence.REFERENCE_STAGE_WIDTH_PX
                / correspondence.IMAGE_WIDTH
            )
            minimum_visible = min(minimum_visible, visible_diameter)
        self.assertGreaterEqual(
            minimum_visible,
            correspondence.MIN_VISIBLE_MOTIF_DIAMETER_PX,
        )

    def test_all_51_nontrivial_films_are_local_and_stopped_by_default(self) -> None:
        ids = [group["id"] for group in self.display_groups]
        self.assertEqual(self.parser.film_group_ids, ids)
        self.assertEqual(
            self.parser.canvases,
            [(f"{group_id}-film", "1", "1") for group_id in ids],
        )
        self.assertEqual(len(self.parser.buttons), correspondence.DISPLAYED_GROUP_COUNT)
        self.assertTrue(all(disabled for disabled, _pressed, _controls in self.parser.buttons))
        self.assertTrue(all(pressed == "false" for _disabled, pressed, _controls in self.parser.buttons))
        self.assertEqual(
            [controls for _disabled, _pressed, controls in self.parser.buttons],
            [f"{group_id}-film" for group_id in ids],
        )
        self.assertEqual(len(self.parser.sliders), correspondence.DISPLAYED_GROUP_COUNT)
        self.assertTrue(
            all(
                disabled and value == "0" and input_type == "range"
                for disabled, value, input_type, _slider_id in self.parser.sliders
            )
        )
        self.assertEqual(
            self.parser.scripts,
            [("clockwork-coloring-correspondence.js", "module")],
        )
        script_path = ROOT / "clockwork-coloring-correspondence.js"
        self.assertTrue(script_path.is_file())
        script = script_path.read_text(encoding="utf-8")
        self.assertIn("this.playingIntent = false", script)
        self.assertIn("phase - placement.tau", script)
        self.assertIn("const HAND_TAIL = 1.4", script)
        self.assertIn("const tip = -Math.PI / 2 + frac(theta) * TWO_PI", script)
        self.assertNotIn("const lit = order > 1", script)
        self.assertNotIn("FRAME_MS", script)
        self.assertIn('this.controls.addEventListener("keydown"', script)
        self.assertIn('event.key === "ArrowRight"', script)
        self.assertIn('event.key === "Home"', script)
        self.assertIn("fixed phase ruler, smooth hand", self.page)
        self.assertNotIn("The upper canvas repeats one continuously animated asymmetric motif", self.page)
        self.assertNotIn("autoplay", self.page.lower())
        self.assertNotIn("autoplay", script.lower())
        self.assertNotIn("<iframe", self.page)
        self.assertNotIn("<video", self.page)
        self.assertNotIn('src="https://yaroslavvb.github.io/animated-groups-fable', self.page)
        self.assertNotIn('href="https://yaroslavvb.github.io/animated-groups-fable/js/', self.page)
        self.assertNotIn("https://yaroslavvb.github.io/animated-groups-fable", script)
        self.assertIn("no runtime data or code is loaded from", self.page)
        self.assertIn("paused by default", self.page)

    def test_navigation_links_the_correspondence_from_both_existing_pages(self) -> None:
        for page in (ROOT / "index.html", ROOT / "future-directions.html"):
            self.assertIn(
                'href="clockwork-coloring-correspondence.html">Correspondence</a>',
                page.read_text(encoding="utf-8"),
            )

    def test_generated_outputs_are_current(self) -> None:
        correspondence.validate_payload(self.payload)
        self.assertEqual(correspondence.check_outputs(self.payload), [])


if __name__ == "__main__":
    unittest.main()
