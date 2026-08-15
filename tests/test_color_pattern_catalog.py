from __future__ import annotations

from collections import Counter, defaultdict
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_color_pattern_catalog as catalog  # noqa: E402
from chaim_short_signatures import (  # noqa: E402
    THREE_FOLD_SHORT_SIGNATURE_BY_TYPE,
    TWO_FOLD_SHORT_SIGNATURE_BY_TYPE,
)
from color_pattern_book_excerpt_specs import (  # noqa: E402
    GS_PAGE_SLOTS,
    SOT_THREE_ROW,
    SOT_TWO_ROW,
    build_excerpt_specs,
)


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.wallpaper_sections: list[str] = []
        self.group_tabs: list[dict[str, str | None]] = []
        self.panel_hosts = 0
        self.pattern_tabs = 0
        self.nav_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "section" and "wallpaper-family" in classes:
            self.wallpaper_sections.append(attributes.get("data-wallpaper-id") or "")
        if tag == "a" and attributes.get("data-group-id"):
            self.group_tabs.append(attributes)
        if "data-group-panel" in attributes:
            self.panel_hosts += 1
        if tag == "a" and attributes.get("data-pattern-id"):
            self.pattern_tabs += 1
        if tag == "a" and attributes.get("href"):
            self.nav_links.append(attributes["href"] or "")


class ColorPatternCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads((ROOT / "data" / "color-pattern-catalog.json").read_text(encoding="utf-8"))
        cls.page = (ROOT / "color-pattern-catalog.html").read_text(encoding="utf-8")
        cls.parser = CatalogParser()
        cls.parser.feed(cls.page)

    def test_generated_outputs_are_current(self) -> None:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_color_pattern_catalog.py"), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_exact_censuses(self) -> None:
        self.assertEqual(len(self.payload["wallpaper_groups"]), 17)
        self.assertEqual(
            Counter(group["number_of_colours"] for group in self.payload["colour_groups"]),
            Counter({1: 17, 2: 46, 3: 23}),
        )
        self.assertEqual(
            Counter(pattern["number_of_colours"] for pattern in self.payload["pattern_types"]),
            Counter({1: 51, 2: 88, 3: 59}),
        )
        self.assertEqual(
            Counter(
                pattern["number_of_colours"]
                for pattern in self.payload["pattern_types"]
                if pattern["underlying_pattern_is_primitive"]
            ),
            Counter({1: 17, 2: 46, 3: 23}),
        )

    def test_three_colour_regular_nonregular_split(self) -> None:
        groups = [
            group for group in self.payload["colour_groups"]
            if group["number_of_colours"] == 3
        ]
        self.assertEqual(Counter(group["colour_image"] for group in groups), Counter({"C3": 8, "S3": 15}))
        for group in groups:
            self.assertEqual(group["regular"], "//" not in group["chaim_notation"])
            if group["regular"]:
                self.assertEqual(group["colour_stabilizer_H"], group["all_colours_kernel_K"])
        self.assertEqual(
            {
                group["chaim_notation"]: group["colour_stabilizer_H"]
                for group in groups if not group["regular"]
            },
            catalog.NONREGULAR_THREE_STABILIZER,
        )
        wallpaper_orbifolds = {
            wallpaper["orbifold"] for wallpaper in self.payload["wallpaper_groups"]
        }
        self.assertTrue(all(group["colour_stabilizer_H"] in wallpaper_orbifolds for group in groups))
        self.assertTrue(all(group["all_colours_kernel_K"] in wallpaper_orbifolds for group in groups))

    def test_every_group_has_complete_ghk_and_generator_colour_actions(self) -> None:
        wallpaper_by_id = {
            wallpaper["id"]: wallpaper for wallpaper in self.payload["wallpaper_groups"]
        }
        expected_image_orders = {"C1": 1, "C2": 2, "C3": 3, "S3": 6}
        for group in self.payload["colour_groups"]:
            self.assertEqual(
                group["ghk"],
                {
                    "G": wallpaper_by_id[group["wallpaper_id"]]["orbifold"],
                    "H": group["colour_stabilizer_H"],
                    "K": group["all_colours_kernel_K"],
                },
            )
            actions = group["generator_colour_actions"]
            self.assertTrue(actions)
            for action in actions:
                self.assertEqual(
                    sorted(action["colour_permutation"]),
                    list(range(group["number_of_colours"])),
                )
            image = catalog.permutation_group(actions)
            self.assertEqual(len(image), expected_image_orders[group["colour_image"]])
            self.assertEqual(
                {permutation[0] for permutation in image},
                set(range(group["number_of_colours"])),
            )
            self.assertEqual(
                group["presentation"],
                catalog.group_presentation(group["wallpaper_id"]),
            )
            self.assertEqual(
                group["presentation"]["generators"],
                [action["generator"] for action in actions],
            )
            self.assertTrue(
                catalog.presentation_relations_hold(group["wallpaper_id"], actions)
            )

        groups = {group["id"]: group for group in self.payload["colour_groups"]}
        self.assertEqual(groups["cg-p4-2-1"]["ghk"], {"G": "442", "H": "442", "K": "442"})
        self.assertEqual(
            groups["cg-p4-2-1"]["presentation"],
            {
                "generators": ["α", "β", "γ"],
                "relations": "α⁴ = β⁴ = γ² = αβγ = 1",
            },
        )
        self.assertEqual(
            [action["permutation_code"] for action in groups["cg-p4-2-1"]["generator_colour_actions"]],
            ["1", "AB", "AB"],
        )
        self.assertEqual(
            [action["permutation_code"] for action in groups["cg-p4-2-2"]["generator_colour_actions"]],
            ["AB", "AB", "1"],
        )
        self.assertEqual(
            [action["permutation_code"] for action in groups["cg-p3m1-3-1"]["generator_colour_actions"]],
            ["AB", "BC", "CA"],
        )
        self.assertEqual(
            groups["cg-pmg-3-1"]["ghk"],
            {"G": "22*", "H": "22*", "K": "××"},
        )

    def test_two_colour_orbifold_exception_is_explicit(self) -> None:
        groups = [
            group for group in self.payload["colour_groups"]
            if group["number_of_colours"] == 2
        ]
        notation_counts = Counter(group["chaim_notation"] for group in groups)
        self.assertEqual(len(notation_counts), 45)
        self.assertEqual(notation_counts["**/**"], 2)
        variants = {
            group["notation_variant"] for group in groups
            if group["chaim_notation"] == "**/**"
        }
        self.assertEqual(variants, {"1", "2"})

    def test_tabs_use_complete_chaim_short_signatures(self) -> None:
        self.assertEqual(len(TWO_FOLD_SHORT_SIGNATURE_BY_TYPE), 46)
        self.assertEqual(len(THREE_FOLD_SHORT_SIGNATURE_BY_TYPE), 23)
        for group in self.payload["colour_groups"]:
            colours = group["number_of_colours"]
            if colours == 1:
                expected = next(
                    wallpaper["orbifold"]
                    for wallpaper in self.payload["wallpaper_groups"]
                    if wallpaper["id"] == group["wallpaper_id"]
                )
            else:
                notation = group["chaim_notation"]
                if group["notation_variant"]:
                    notation += f" ({group['notation_variant']})"
                mapping = (
                    TWO_FOLD_SHORT_SIGNATURE_BY_TYPE
                    if colours == 2
                    else THREE_FOLD_SHORT_SIGNATURE_BY_TYPE
                )
                expected = mapping[notation]
            self.assertEqual(group["chaim_short_signature"], expected)
            self.assertIn(
                f'<span class="tab-name tab-signature" aria-hidden="true">'
                f'{catalog.short_signature_html(expected)}</span>',
                self.page,
            )

        groups = {group["id"]: group for group in self.payload["colour_groups"]}
        self.assertNotEqual(
            groups["cg-pm-2-3"]["chaim_short_signature"],
            groups["cg-pm-2-5"]["chaim_short_signature"],
        )
        self.assertNotEqual(
            groups["cg-p3m1-3-1"]["chaim_short_signature"],
            groups["cg-p3m1-3-2"]["chaim_short_signature"],
        )
        self.assertEqual(groups["cg-p6-3-1"]["chaim_short_signature"], "³6³3¹2")
        self.assertEqual(groups["cg-p6-3-2"]["chaim_short_signature"], "²6³3²2")
        self.assertIn("<sup>(AB)</sup>", self.page)
        self.assertNotIn('<span class="tab-alias">', self.page)

    def test_gs_indices_use_the_audited_orbifold_crosswalk(self) -> None:
        expected_two = {
            "p1": ("◦/◦",),
            "p2": ("2222/◦", "2222/2222"),
            "pm": ("**/××", "**/*×", "**/** (1)", "**/◦", "**/** (2)"),
            "pg": ("××/◦", "××/××"),
            "cm": ("*×/◦", "*×/××", "*×/**"),
            "pmm": ("*2222/*2222", "*2222/**", "*2222/2*22", "*2222/22*", "*2222/2222"),
            "pmg": ("22*/22*", "22*/××", "22*/22×", "22*/**", "22*/2222"),
            "pgg": ("22×/××", "22×/2222"),
            "cmm": ("2*22/22×", "2*22/*×", "2*22/22*", "2*22/2222", "2*22/*2222"),
            "p4": ("442/442", "442/2222"),
            "p4m": ("*442/4*2", "*442/442", "*442/2*22", "*442/*2222", "*442/*442"),
            "p4g": ("4*2/442", "4*2/2*22", "4*2/22×"),
            "p3": (),
            "p3m1": ("*333/333",),
            "p31m": ("3*3/333",),
            "p6": ("632/333",),
            "p6m": ("*632/3*3", "*632/*333", "*632/632"),
        }
        expected_three = {
            "p1": ("◦³/◦",),
            "p2": ("2222³//◦",),
            "pm": ("**³//◦", "**³/**"),
            "pg": ("××³/××", "××³//◦"),
            "cm": ("*×³/*×", "*×³//◦"),
            "pmm": ("*2222³//**",),
            "pmg": ("22*³//××", "22*³//**"),
            "pgg": ("22×³//××",),
            "cmm": ("2*22³//*×",),
            "p4": (),
            "p4m": (),
            "p4g": (),
            "p3": ("333³/◦", "333³/333"),
            "p3m1": ("*333³//◦", "*333³//333"),
            "p31m": ("3*3³//◦", "3*3³/*333"),
            "p6": ("632³/2222", "632³//333"),
            "p6m": ("*632³//2222", "*632³//*333"),
        }

        def ordered_notation(parent: str, colours: int) -> tuple[str, ...]:
            groups = sorted(
                (
                    group for group in self.payload["colour_groups"]
                    if group["wallpaper_id"] == parent and group["number_of_colours"] == colours
                ),
                key=lambda group: group["index_within_parent"],
            )
            return tuple(
                group["chaim_notation"] + (
                    f" ({group['notation_variant']})" if group["notation_variant"] else ""
                )
                for group in groups
            )

        for parent, expected in expected_two.items():
            with self.subTest(colours=2, parent=parent):
                self.assertEqual(ordered_notation(parent, 2), expected)
        for parent, expected in expected_three.items():
            with self.subTest(colours=3, parent=parent):
                self.assertEqual(ordered_notation(parent, 3), expected)

    def test_every_pattern_has_one_compatible_parent_group(self) -> None:
        group_by_id = {group["id"]: group for group in self.payload["colour_groups"]}
        seen: set[str] = set()
        counts = defaultdict(int)
        for pattern in self.payload["pattern_types"]:
            self.assertNotIn(pattern["id"], seen)
            seen.add(pattern["id"])
            group = group_by_id[pattern["colour_group_id"]]
            self.assertEqual(group["wallpaper_id"], pattern["wallpaper_id"])
            self.assertEqual(group["number_of_colours"], pattern["number_of_colours"])
            counts[group["id"]] += 1
        self.assertEqual(set(counts), set(group_by_id))

    def test_pattern_type_census_by_wallpaper_parent(self) -> None:
        expected = {
            "p1": (1, 1, 1), "p2": (2, 3, 2), "pm": (2, 8, 4),
            "pg": (1, 2, 2), "cm": (2, 4, 4), "pmm": (3, 12, 4),
            "pmg": (3, 10, 6), "pgg": (2, 3, 2), "cmm": (4, 11, 5),
            "p4": (3, 4, 0), "p4m": (5, 12, 0), "p4g": (4, 6, 0),
            "p3": (2, 0, 3), "p3m1": (3, 1, 5), "p31m": (4, 2, 5),
            "p6": (4, 2, 5), "p6m": (6, 7, 11),
        }
        for parent, wanted in expected.items():
            got = tuple(
                sum(
                    pattern["wallpaper_id"] == parent
                    and pattern["number_of_colours"] == colours
                    for pattern in self.payload["pattern_types"]
                )
                for colours in (1, 2, 3)
            )
            with self.subTest(parent=parent):
                self.assertEqual(got, wanted)

    def test_p31m_book_misprint_is_normalized_and_explained(self) -> None:
        pattern = next(
            item for item in self.payload["pattern_types"]
            if item["gs_pattern_type"] == "PP23[3]_2"
        )
        group = next(
            item for item in self.payload["colour_groups"]
            if item["id"] == pattern["colour_group_id"]
        )
        self.assertEqual(group["gs_symbol"], "p31m[3]_2")
        self.assertIn("prints the colour-group subscript 3", pattern["source_note"])

    def test_static_shell_has_17_families_and_86_group_tabs(self) -> None:
        self.assertEqual(len(self.parser.wallpaper_sections), 17)
        self.assertEqual(len(set(self.parser.wallpaper_sections)), 17)
        self.assertEqual(len(self.parser.group_tabs), 86)
        self.assertEqual(self.parser.panel_hosts, 17)
        self.assertEqual(self.parser.pattern_tabs, 0)
        self.assertEqual(
            sum("is-trivial" in (tab.get("class") or "") for tab in self.parser.group_tabs),
            17,
        )
        for tab in self.parser.group_tabs:
            group_id = tab["data-group-id"]
            self.assertEqual(tab.get("aria-controls"), f"panel-{group_id}")
            self.assertIn("Chaim short colour signature", tab.get("aria-label") or "")
            self.assertIn("colour type", tab.get("aria-label") or "")

    def test_javascript_is_syntax_valid_and_contains_nested_tab_controls(self) -> None:
        subprocess.run(
            ["node", "--check", str(ROOT / "color-pattern-catalog.js")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        script = (ROOT / "color-pattern-catalog.js").read_text(encoding="utf-8")
        for required in ("activateGroup", "activatePattern", "openFromHash", "ArrowLeft", "ArrowRight"):
            self.assertIn(required, script)
        self.assertIn('points: "0,-13 13,0 0,13 -13,0"', script)
        self.assertIn('letter.textContent = "R"', script)
        self.assertIn("const MOTIF_SCALE = 1.55", script)
        self.assertIn("const siblingIndex", script)
        self.assertIn("const layoutVariant", script)
        self.assertIn("const motifAngle = (theta * 180) / Math.PI", script)
        self.assertIn("function buildP4TwoColourPattern", script)
        self.assertIn('group.all_colours_kernel_K === "2222" ? 1 : 0', script)
        self.assertIn('group.all_colours_kernel_K === "442" ? 1 : 0', script)
        self.assertIn("translationShift * (col + row) + quarterTurnShift * orbit", script)
        self.assertNotIn("const motifScale", script)
        self.assertNotIn("layoutVariant * 7", script)
        self.assertNotIn("const paths = [", script)
        self.assertIn('link.target = "color-pattern-book-excerpt"', script)
        self.assertIn("state.excerptWindow.location.href = excerpt.href", script)
        self.assertIn("state.excerptWindow.focus()", script)
        for label in (
            "Chaim short form",
            "Chaim G/H/K",
            "G&S group symbol",
            "G&S pattern type",
            "Presentation",
            "Relations",
        ):
            self.assertIn(f'"{label}"', script)
        for required in (
            "ghkElement",
            "presentationElement",
            "actionPaletteElement",
            "permutationNotation",
            "permutationDescription",
            "group.generator_colour_actions",
            "group.presentation.relations",
            'if (notation !== "id")',
        ):
            self.assertIn(required, script)
        for removed in (
            "group-overview",
            "group-kicker",
            "group-title",
            "group-aliases",
            "Type invariant",
            "Underlying pattern type",
            "Representative",
            "Colour action",
            "Parent wallpaper group",
            "Single-colour stabilizer H",
            "All-colours stabilizer K",
            "Generator colour action",
            '"G / H / K"',
            "-colour plane group",
        ):
            self.assertNotIn(removed, script)

    def test_every_catalog_record_has_a_reusable_book_excerpt(self) -> None:
        for group in self.payload["colour_groups"]:
            excerpt = group["book_excerpt"]
            self.assertEqual(excerpt["work"], "The Symmetries of Things")
            self.assertTrue(excerpt["image"].endswith(".webp"))
            self.assertIn("printed_page", excerpt)
        for pattern in self.payload["pattern_types"]:
            excerpt = pattern["book_excerpt"]
            self.assertEqual(excerpt["work"], "Tilings and Patterns")
            self.assertTrue(excerpt["image"].endswith(".webp"))
            self.assertIn("source_symbol", excerpt)

        script = (ROOT / "color-pattern-catalog.js").read_text(encoding="utf-8")
        self.assertIn("group.book_excerpt", script)
        self.assertGreaterEqual(script.count("pattern.book_excerpt"), 2)

    def test_p4_two_colour_representatives_use_distinct_characters(self) -> None:
        groups = {
            group["chaim_short_signature"]: group
            for group in self.payload["colour_groups"]
            if group["wallpaper_id"] == "p4" and group["number_of_colours"] == 2
        }
        self.assertEqual(groups["¹4²4²2"]["all_colours_kernel_K"], "442")
        self.assertEqual(groups["²4²4¹2"]["all_colours_kernel_K"], "2222")
        # chi(t_x)=chi(t_y)=u and chi(A)=a for a quarter-turn A.
        first = tuple((col + row) % 2 for row in range(2) for col in range(2) for _orbit in range(4))
        second = tuple(orbit % 2 for _row in range(2) for _col in range(2) for orbit in range(4))
        self.assertNotEqual(first, second)

    def test_excerpt_specs_cover_69_colour_groups_and_147_coloured_patterns(self) -> None:
        specs = build_excerpt_specs(self.payload)
        self.assertEqual(Counter(spec["kind"] for spec in specs.values()), Counter({"gs": 147, "sot": 69}))
        expected_paths = {ROOT / path for path in specs}
        actual_paths = set((ROOT / "output" / "color-pattern-excerpts").glob("*.webp"))
        self.assertEqual(actual_paths, expected_paths)
        self.assertTrue(all(path.stat().st_size > 1_000 for path in actual_paths))

        groups = self.payload["colour_groups"]
        self.assertEqual(len(SOT_TWO_ROW), 46)
        self.assertEqual(len(SOT_THREE_ROW), 23)
        blank_short = next(group for group in groups if group["chaim_notation"] == "632³//333")
        self.assertIn("leaves this short-signature cell blank", blank_short["book_excerpt"]["context"])
        corrected_pmg = next(group for group in groups if group["chaim_notation"] == "22*³//××")
        self.assertIn("intransitive", corrected_pmg["book_excerpt"]["context"])
        corrected_cmm = next(group for group in groups if group["chaim_notation"] == "2*22³//*×")
        self.assertIn("centred-mirror kernel K=*×", corrected_cmm["book_excerpt"]["context"])
        corrected_p31m = {
            group["chaim_notation"]: group["book_excerpt"]["context"]
            for group in groups if group["wallpaper_id"] == "p31m" and group["number_of_colours"] == 3
        }
        self.assertIn("H=*×", corrected_p31m["3*3³//◦"])
        self.assertIn("H=K=*333", corrected_p31m["3*3³/*333"])

        page_counts = Counter(
            pattern["source"]["printed_page"]
            for pattern in self.payload["pattern_types"]
            if pattern["number_of_colours"] > 1
        )
        self.assertEqual(page_counts, Counter({page: len(slots) for page, slots in GS_PAGE_SLOTS.items()}))
        for page, slots in GS_PAGE_SLOTS.items():
            for slot in slots:
                self.assertEqual(len(slot["highlight_probes"]), 2)
                crop_x, crop_y, crop_width, crop_height = slot["crop"]
                self.assertGreaterEqual(crop_x, 0)
                self.assertGreaterEqual(crop_y, 0)
                self.assertLessEqual(crop_x + crop_width, 545)
                self.assertLessEqual(crop_y + crop_height, 646)

    def test_one_colour_pattern_links_are_honest_chapter_8_cross_references(self) -> None:
        one_colour = [
            pattern for pattern in self.payload["pattern_types"]
            if pattern["number_of_colours"] == 1
        ]
        self.assertEqual(len(one_colour), 51)
        for pattern in one_colour:
            excerpt = pattern["book_excerpt"]
            self.assertIn("same PP stem", excerpt["context"])
            self.assertNotEqual(excerpt["source_symbol"], pattern["gs_pattern_type"])

    def test_site_navigation_links_to_patterns(self) -> None:
        static_pages = (
            ROOT / "index.html",
            ROOT / "future-directions.html",
            ROOT / "dihedral-interactive.html",
            ROOT / "docs" / "orbifold_notation.html",
            ROOT / "clockwork-coloring-correspondence.html",
            ROOT / "space-group-correspondence.html",
        )
        for path in static_pages:
            target = "../color-pattern-catalog.html" if path.parent.name == "docs" else "color-pattern-catalog.html"
            with self.subTest(path=path.name):
                self.assertIn(f'href="{target}"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
