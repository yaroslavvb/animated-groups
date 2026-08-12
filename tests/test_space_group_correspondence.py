from __future__ import annotations

from collections import defaultdict
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_space_group_correspondence as correspondence  # noqa: E402


class SpaceCorrespondenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.family_ids: list[str] = []
        self.empty_family_ids: list[str] = []
        self.tabs_containers = 0
        self.tablists = 0
        self.tabs: list[tuple[str, str, str]] = []
        self.panels: list[str] = []
        self.directory_families: list[str] = []
        self.directory_groups: list[tuple[str, str]] = []
        self.trivial_products: list[str] = []
        self.viewers: list[str] = []
        self.stages = 0
        self.canvases: list[tuple[bool, str, str]] = []
        self.controls: list[bool] = []
        self.toggle_labels = 0
        self.sliders: list[tuple[bool, str, str, str, str]] = []
        self.outputs = 0
        self.static_tab_roles: list[tuple[str, str]] = []
        self.article_images: dict[str, list[tuple[str, bool]]] = defaultdict(list)
        self.current_article: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "section" and "wallpaper-family" in classes:
            self.family_ids.append(attributes.get("id", ""))
            if "is-empty" in classes:
                self.empty_family_ids.append(attributes.get("id", ""))
        if "data-space-tabs" in attributes:
            self.tabs_containers += 1
        if "data-space-tablist" in attributes:
            self.tablists += 1
        if tag == "a" and "data-space-tab" in attributes:
            self.tabs.append(
                (
                    attributes.get("id", ""),
                    attributes.get("href", ""),
                    attributes.get("data-panel-id", ""),
                )
            )
            if attributes.get("role"):
                self.static_tab_roles.append((tag, attributes["role"] or ""))
        if tag == "a" and "directory-family-link" in classes:
            self.directory_families.append(attributes.get("href", ""))
        if tag == "a" and attributes.get("data-directory-group"):
            self.directory_groups.append(
                (
                    attributes.get("data-directory-group", ""),
                    attributes.get("href", ""),
                )
            )
        if tag == "article" and "data-space-tabpanel" in attributes:
            self.current_article = attributes.get("id", "")
            self.panels.append(self.current_article)
            if attributes.get("role"):
                self.static_tab_roles.append((tag, attributes["role"] or ""))
        if tag == "aside" and "data-trivial-product" in attributes:
            self.trivial_products.append(attributes.get("id", ""))
        if "data-space-tablist" in attributes and attributes.get("role"):
            self.static_tab_roles.append((tag, attributes["role"] or ""))
        if tag == "figure" and "data-space-viewer" in attributes:
            self.viewers.append(attributes.get("data-group-id", ""))
        if "space-stage" in classes:
            self.stages += 1
        if tag == "img" and self.current_article is not None:
            self.article_images[self.current_article].append(
                (attributes.get("src", ""), "data-space-static" in attributes)
            )
        if tag == "canvas" and "data-space-canvas" in attributes:
            self.canvases.append(
                (
                    "hidden" in attributes,
                    attributes.get("width", ""),
                    attributes.get("height", ""),
                )
            )
        if "data-space-controls" in attributes:
            self.controls.append("hidden" in attributes)
        if "data-space-toggle-label" in attributes:
            self.toggle_labels += 1
        if tag == "input" and "data-space-slider" in attributes:
            self.sliders.append(
                (
                    "disabled" in attributes,
                    attributes.get("min", ""),
                    attributes.get("max", ""),
                    attributes.get("step", ""),
                    attributes.get("value", ""),
                )
            )
        if tag == "output" and "data-space-output" in attributes:
            self.outputs += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "article":
            self.current_article = None


class SpaceGroupCorrespondenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(correspondence.DATA.read_text(encoding="utf-8"))
        cls.page = correspondence.PAGE.read_text(encoding="utf-8")
        cls.parser = SpaceCorrespondenceParser()
        cls.parser.feed(cls.page)
        cls.ordered_groups = [
            record
            for base in correspondence.BASE_ORDER
            for record in cls.payload["groups"]
            if record["parent"]["hm"] == base
        ]
        cls.displayed_groups = [
            record for record in cls.ordered_groups if record["clock_order"] > 1
        ]
        cls.trivial_groups = [
            record for record in cls.ordered_groups if record["clock_order"] == 1
        ]
        cls.contributing_bases = [
            base
            for base in correspondence.BASE_ORDER
            if any(
                record["parent"]["hm"] == base and record["clock_order"] > 1
                for record in cls.payload["groups"]
            )
        ]

    def test_pinned_map_is_bijection_onto_the_68_polar_types(self) -> None:
        groups = self.payload["groups"]
        self.assertEqual(len(groups), 68)
        self.assertEqual(len(correspondence.SPACE_GROUP_BY_ID), 68)
        self.assertEqual(
            {group["id"] for group in groups},
            set(correspondence.SPACE_GROUP_BY_ID),
        )
        numbers = [group["space_group"]["it_number"] for group in groups]
        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertEqual(set(numbers), correspondence.POLAR_IT_NUMBERS)
        self.assertEqual(
            self.payload["meta"]["polar_it_numbers"],
            sorted(correspondence.POLAR_IT_NUMBERS),
        )

        # These low-symmetry settings are easy to mis-order when sorting by
        # wallpaper family rather than by the catalog record ID.
        low_symmetry = {
            "g1": (1, "P1", "P 1", "P 1", ""),
            "g5": (3, "P2", "P 1 2 1", "P 2y", "b"),
            "g6": (4, "P2_1", "P 1 2_1 1", "P 2yb", "b"),
            "g7": (5, "C2", "C 1 2 1", "C 2y", "b1"),
            "g8": (8, "Cm", "C 1 m 1", "C -2y", "b1"),
            "g9": (9, "Cc", "C 1 c 1", "C -2yc", "b1"),
            "g10": (6, "Pm", "P 1 m 1", "P -2y", "b"),
            "g11": (7, "Pc", "P 1 c 1", "P -2yc", "b1"),
        }
        self.assertEqual(
            {group_id: correspondence.SPACE_GROUP_BY_ID[group_id] for group_id in low_symmetry},
            low_symmetry,
        )

    def test_json_is_an_exact_derivation_of_the_clockwork_source(self) -> None:
        rebuilt = correspondence.build_payload()
        correspondence.validate_payload(rebuilt)
        self.assertEqual(rebuilt, self.payload)
        source = json.loads(correspondence.SOURCE_DATA.read_text(encoding="utf-8"))
        self.assertEqual(
            [group["id"] for group in self.payload["groups"]],
            [group["id"] for group in source["groups"]],
        )
        for lifted, original in zip(self.payload["groups"], source["groups"]):
            self.assertEqual(lifted["image"], original["image"])
            self.assertEqual(lifted["render"], original["render"])

    def test_every_planar_operation_has_the_explicit_height_lift(self) -> None:
        for group in self.payload["groups"]:
            planar = group["render"]["ops"]
            lifted = group["lift_operations"]
            self.assertEqual(len(lifted), len(planar), group["id"])
            for operation, operation_3d in zip(planar, lifted):
                matrix = operation["M"]
                self.assertEqual(
                    operation_3d["R"],
                    [
                        [matrix[0][0], matrix[0][1], 0],
                        [matrix[1][0], matrix[1][1], 0],
                        [0, 0, 1],
                    ],
                    group["id"],
                )
                self.assertEqual(
                    operation_3d["t"],
                    [operation["v"][0], operation["v"][1], operation["tau"]],
                    group["id"],
                )
            self.assertEqual(
                group["lift_formula"],
                "(x, y, z) ↦ (M(x, y) + v, z + τ)",
            )
            self.assertEqual(
                group["space_group"]["polar_axis"],
                "z (constructed lift coordinate; before conventional-setting normalization)",
            )

        # The constructed z coordinate need not retain the letter c after the
        # database normalizes a group to its conventional setting.  In
        # particular, these monoclinic groups use the conventional unique-b
        # setting, so the public copy must describe z as the lift direction.
        self.assertNotIn("crystallographic <em>c</em> direction", self.page)
        self.assertIn("listed conventional crystallographic setting", self.page)

    def test_all_17_sections_display_only_the_51_nontrivial_pairs(self) -> None:
        expected_ids = [group["id"] for group in self.displayed_groups]
        trivial_ids = [group["id"] for group in self.trivial_groups]
        self.assertEqual(len(expected_ids), correspondence.DISPLAYED_GROUP_COUNT)
        self.assertEqual(len(trivial_ids), correspondence.OMITTED_TRIVIAL_COUNT)
        self.assertEqual(
            self.parser.family_ids,
            [f"wallpaper-{base}" for base in correspondence.BASE_ORDER],
        )
        self.assertEqual(
            self.parser.empty_family_ids,
            ["wallpaper-p1", "wallpaper-pm", "wallpaper-pg"],
        )
        self.assertEqual(self.parser.tabs_containers, correspondence.DISPLAYED_FAMILY_COUNT)
        self.assertEqual(self.parser.tablists, correspondence.DISPLAYED_FAMILY_COUNT)
        # The no-JS page keeps native nav/link/article semantics and displays
        # every panel.  The controller installs the tab roles, aria-selected,
        # and hidden state together only after it has initialized successfully.
        self.assertEqual(self.parser.static_tab_roles, [])
        self.assertEqual(
            self.parser.directory_families,
            [f"#wallpaper-{base}" for base in self.contributing_bases],
        )
        self.assertEqual(
            self.parser.tabs,
            [(f"tab-{group_id}", f"#{group_id}", group_id) for group_id in expected_ids],
        )
        self.assertEqual(self.parser.panels, expected_ids)
        self.assertEqual(self.parser.viewers, expected_ids)
        self.assertEqual(
            self.parser.directory_groups,
            [(group_id, f"#{group_id}") for group_id in expected_ids],
        )
        self.assertEqual(self.parser.trivial_products, trivial_ids)
        self.assertTrue(set(expected_ids).isdisjoint(trivial_ids))
        self.assertIn("51 displayed multi-colour lifts", self.page)
        self.assertIn("68-type audit", self.page)
        self.assertIn("51 displayed groups · 14 contributing families", self.page)

    def test_filter_metadata_ids_and_trivial_deep_links_are_auditable(self) -> None:
        self.assertEqual(
            self.payload["meta"]["displayed_nontrivial_groups"],
            correspondence.DISPLAYED_GROUP_COUNT,
        )
        self.assertEqual(
            self.payload["meta"]["displayed_wallpaper_families"],
            correspondence.DISPLAYED_FAMILY_COUNT,
        )
        self.assertEqual(
            self.payload["meta"]["omitted_trivial_products"],
            correspondence.OMITTED_TRIVIAL_COUNT,
        )

        element_ids = re.findall(r'(?<=\s)id="([^"]+)"', self.page)
        self.assertEqual(len(element_ids), len(set(element_ids)))
        for group in self.trivial_groups:
            group_id = group["id"]
            base = group["parent"]["hm"]
            self.assertNotIn(f'data-directory-group="{group_id}"', self.page)
            self.assertNotIn(f'data-panel-id="{group_id}"', self.page)
            self.assertIn(
                f'aria-label="Trivial one-colour product {group_id} over wallpaper group {base}"',
                self.page,
            )

        controller = (ROOT / "space-group-correspondence.js").read_text(encoding="utf-8")
        self.assertIn(
            'document.getElementById(id)?.scrollIntoView({ block: "start" })',
            controller,
        )

    def test_each_panel_orders_the_2d_plate_before_the_static_3d_plate(self) -> None:
        for group in self.displayed_groups:
            group_id = group["id"]
            self.assertEqual(
                self.parser.article_images[group_id],
                [
                    (group["image"], False),
                    (group["space_group"]["image"], True),
                    (group["space_group"]["reference_preview_image"], False),
                ],
                group_id,
            )
        # CSS shows static images until JS marks each stage ready.  The controls
        # are present but disabled until the corresponding viewer activates.
        self.assertEqual(self.parser.stages, correspondence.DISPLAYED_GROUP_COUNT)
        self.assertEqual(
            self.parser.canvases,
            [(False, "720", "480")] * correspondence.DISPLAYED_GROUP_COUNT,
        )
        self.assertEqual(
            self.parser.controls, [False] * correspondence.DISPLAYED_GROUP_COUNT
        )
        self.assertEqual(self.parser.toggle_labels, correspondence.DISPLAYED_GROUP_COUNT)
        self.assertEqual(
            self.parser.sliders,
            [(True, "0", "1", "0.001", "0.095")]
            * correspondence.DISPLAYED_GROUP_COUNT,
        )
        self.assertEqual(self.parser.outputs, correspondence.DISPLAYED_GROUP_COUNT)
        self.assertIn('class="space-stage" data-state="static"', self.page)
        self.assertIn('class="space-canvas" data-space-canvas', self.page)

    def test_scope_is_precise_and_visible(self) -> None:
        self.assertEqual(
            self.payload["meta"]["scope_caveat"], correspondence.SCOPE_CAVEAT
        )
        self.assertIn(correspondence.SCOPE_CAVEAT, self.page)
        self.assertIn("all 230 space groups", correspondence.SCOPE_CAVEAT)
        self.assertIn("regular-cyclic subset", correspondence.SCOPE_CAVEAT)
        self.assertIn("spglib 2.6.0", self.page)

    def test_generated_page_has_no_wolfram_or_mathematica_content(self) -> None:
        self.assertNotIn("Wolfram", self.page)
        self.assertNotIn("Mathematica", self.page)
        self.assertNotIn("FiniteGroupData", self.page)
        self.assertNotIn("wolfram-group-line", self.page)
        self.assertNotIn("trivial-wolfram-line", self.page)
        css = (ROOT / "space-group-correspondence.css").read_text(encoding="utf-8")
        self.assertNotIn("wolfram-group-line", css)
        self.assertNotIn("trivial-wolfram-line", css)

    def test_each_displayed_space_group_links_to_ucl_with_a_local_preview(self) -> None:
        self.assertEqual(
            set(correspondence.UCL_PAGE_BY_NUMBER),
            correspondence.POLAR_IT_NUMBERS,
        )
        for group in self.payload["groups"]:
            space_group = group["space_group"]
            expected_url = (
                f"{correspondence.UCL_SPACE_GROUP_BASE}/"
                f"{correspondence.UCL_PAGE_BY_NUMBER[space_group['it_number']]}"
            )
            self.assertEqual(space_group["ucl_reference_url"], expected_url)
            self.assertEqual(
                space_group["reference_preview_image"], space_group["image"]
            )

        for group in self.displayed_groups:
            article = re.search(
                rf'<article[^>]+id="{group["id"]}"[^>]*>.*?</article>',
                self.page,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(article, group["id"])
            markup = article.group(0)
            self.assertEqual(markup.count(group["space_group"]["ucl_reference_url"]), 2)
            self.assertEqual(markup.count('class="space-reference-preview"'), 1)
            self.assertIn(
                f'src="{group["space_group"]["reference_preview_image"]}"',
                markup,
            )

        self.assertEqual(
            self.page.count('class="space-reference-link"'),
            correspondence.DISPLAYED_GROUP_COUNT,
        )
        self.assertEqual(
            self.page.count('class="space-reference-preview"'),
            correspondence.DISPLAYED_GROUP_COUNT,
        )
        self.assertIn("published licence prohibits Internet distribution", self.page)
        css = (ROOT / "space-group-correspondence.css").read_text(encoding="utf-8")
        self.assertIn(".space-reference:hover .space-reference-preview", css)
        self.assertIn(".space-reference:focus-within .space-reference-preview", css)

    def test_all_static_plates_are_lossless_webp_at_the_pinned_size(self) -> None:
        for group in self.payload["groups"]:
            image_path = ROOT / group["space_group"]["image"]
            self.assertTrue(image_path.is_file(), group["id"])
            with Image.open(image_path) as image:
                self.assertEqual(image.format, "WEBP", group["id"])
                self.assertEqual(
                    image.size,
                    (correspondence.IMAGE_WIDTH, correspondence.IMAGE_HEIGHT),
                    group["id"],
                )
                self.assertEqual(image.mode, "RGB", group["id"])
                self.assertIsNotNone(image.getbbox(), group["id"])
            # A WebP RIFF chunk tagged VP8L is the lossless bitstream.
            self.assertEqual(image_path.read_bytes()[12:16], b"VP8L", group["id"])

    def test_generator_check_mode_passes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_space_group_correspondence.py"),
                "--check",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("outputs are current", result.stdout)


if __name__ == "__main__":
    unittest.main()
