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
            "pmg": ("22*³//◦", "22*³//**"),
            "pgg": ("22×³//××",),
            "cmm": ("2*22³//**",),
            "p4": (),
            "p4m": (),
            "p4g": (),
            "p3": ("333³/◦", "333³/333"),
            "p3m1": ("*333³//◦", "*333³//333"),
            "p31m": ("3*3³//*333", "3*3³/◦"),
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
