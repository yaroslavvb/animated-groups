from __future__ import annotations

from collections import Counter, defaultdict
from html.parser import HTMLParser
import json
from math import hypot, isfinite
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_color_pattern_catalog as catalog  # noqa: E402
import generate_color_pattern_book_excerpts as excerpt_generator  # noqa: E402
from chaim_short_signatures import (  # noqa: E402
    THREE_FOLD_SHORT_SIGNATURE_BY_TYPE,
    TWO_FOLD_SHORT_SIGNATURE_BY_TYPE,
)
from color_pattern_book_excerpt_specs import (  # noqa: E402
    GS_PAGE_SLOTS,
    build_excerpt_specs,
)
from tos_book_excerpt_specs import BOOK_EXCERPTS  # noqa: E402
from wallpaper_affine_generators import (  # noqa: E402
    affine_relations_hold,
    colour_blind_discrepancy,
    colour_blind_fingerprint,
    enumerate_coloured_actions,
    scene_fingerprint,
)


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.wallpaper_sections: list[str] = []
        self.group_tabs: list[dict[str, str | None]] = []
        self.panel_hosts = 0
        self.pattern_tabs = 0
        self.nav_links: list[str] = []
        self.directory_cards: list[dict[str, str | None]] = []
        self.directory_images: list[dict[str, str | None]] = []

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
        if tag == "a" and attributes.get("data-directory-wallpaper-id"):
            self.directory_cards.append(attributes)
        if tag == "img" and (attributes.get("src") or "").startswith(
            "output/mathworld-wallpaper-groups/"
        ):
            self.directory_images.append(attributes)


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

    def test_temporary_pattern_lock_keeps_one_primitive_tab_per_group(self) -> None:
        patterns_by_group: dict[str, list[dict[str, object]]] = defaultdict(list)
        for pattern in self.payload["pattern_types"]:
            patterns_by_group[pattern["colour_group_id"]].append(pattern)

        self.assertEqual(len(patterns_by_group), 86)
        self.assertEqual(
            sum(len(patterns) - 1 for patterns in patterns_by_group.values()),
            112,
        )
        self.assertTrue(all(
            patterns[0]["underlying_pattern_is_primitive"]
            for patterns in patterns_by_group.values()
        ))

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

    def test_affine_generator_visualizations_match_presentations(self) -> None:
        counts: Counter[str] = Counter()
        for wallpaper in self.payload["wallpaper_groups"]:
            descriptions = dict(catalog.GENERATOR_GEOMETRY[wallpaper["id"]])
            for generator in wallpaper["render_geometry"]["generators"]:
                visualization = generator["visualization"]
                kind = visualization["kind"]
                description = descriptions[generator["generator"]]
                expected = (
                    "translation" if description == "translation"
                    else "glide" if "glide reflection" in description
                    else "mirror" if "mirror reflection" in description
                    else "rotation"
                )
                self.assertEqual(kind, expected, (wallpaper["id"], generator["generator"]))
                counts[kind] += 1
                if kind == "rotation":
                    self.assertIn(visualization["angle_degrees"], {60, 90, 120, 180})
                    self.assertTrue(all(isfinite(value) for value in visualization["centre"]))
                elif kind in {"mirror", "glide"}:
                    self.assertTrue(all(isfinite(value) for value in visualization["axis_point"]))
                    self.assertAlmostEqual(
                        hypot(*visualization["axis_direction"]), 1, places=8,
                    )
        self.assertEqual(
            counts,
            Counter({"mirror": 21, "rotation": 20, "glide": 4, "translation": 3}),
        )

    def test_affine_renderer_realizes_all_198_entries_without_collisions(self) -> None:
        wallpaper_by_id = {
            wallpaper["id"]: wallpaper for wallpaper in self.payload["wallpaper_groups"]
        }
        group_by_id = {
            group["id"]: group for group in self.payload["colour_groups"]
        }
        for parent, wallpaper in wallpaper_by_id.items():
            self.assertTrue(affine_relations_hold(parent))
            self.assertEqual(
                [item["generator"] for item in wallpaper["render_geometry"]["generators"]],
                group_by_id[f"cg-{parent}-1-1"]["presentation"]["generators"],
            )

        actions_by_group = {}
        fingerprints: defaultdict[tuple, list[str]] = defaultdict(list)
        colours_seen: dict[str, set[int]] = defaultdict(set)
        blind_by_pattern: dict[str, tuple] = {}
        for pattern in self.payload["pattern_types"]:
            group = group_by_id[pattern["colour_group_id"]]
            if group["id"] not in actions_by_group:
                actions_by_group[group["id"]] = enumerate_coloured_actions(
                    group["wallpaper_id"], group["generator_colour_actions"]
                )
            fingerprint = scene_fingerprint(
                pattern, group, actions_by_group[group["id"]]
            )
            self.assertTrue(fingerprint, pattern["id"])
            fingerprints[fingerprint].append(pattern["id"])
            colours_seen[group["id"]].update(pose[-1] // 10 for pose in fingerprint)
            blind_by_pattern[pattern["id"]] = colour_blind_fingerprint(
                pattern, group, actions_by_group[group["id"]]
            )

        collisions = [ids for ids in fingerprints.values() if len(ids) > 1]
        self.assertEqual(len(fingerprints), 198)
        self.assertEqual(collisions, [])
        for group in self.payload["colour_groups"]:
            self.assertEqual(
                colours_seen[group["id"]],
                set(range(group["number_of_colours"])),
                group["id"],
            )

        pattern_by_id = {
            pattern["id"]: pattern for pattern in self.payload["pattern_types"]
        }
        orbit_points = {
            tuple(seed["point"])
            for pattern in self.payload["pattern_types"]
            if pattern["render_layout"]["kind"] == "orbit"
            for seed in pattern["render_layout"]["seeds"]
        }
        # Generic representatives retain one centre grid per wallpaper
        # family.  *632 and *442 use the incenter of their mirror triangles
        # to keep the deliberately large R-diamonds apart; every other family
        # keeps the common seed.  The optimizer changes orientation, not
        # position.
        self.assertEqual(
            orbit_points,
            {(0.173, 0.137), (0.394338, 0.105662), (0.353553, 0.146447)},
        )
        zero_discrepancy = 0
        for pattern in self.payload["pattern_types"]:
            layout = pattern["render_layout"]
            reference_id = layout["reference_pattern_id"]
            self.assertIn(reference_id, pattern_by_id)
            measured = colour_blind_discrepancy(
                blind_by_pattern[reference_id], blind_by_pattern[pattern["id"]]
            )
            self.assertAlmostEqual(
                layout["colour_blind_discrepancy"], measured, places=6,
                msg=pattern["id"],
            )
            if measured == 0:
                zero_discrepancy += 1
        # Candidate zero is shared within each wallpaper family.  It gives
        # every group's first representative the family reference geometry;
        # only later same-group pattern types need the closest alternative.
        self.assertEqual(zero_discrepancy, 86)

    def test_p6m_motifs_have_clearance_and_keep_one_grid(self) -> None:
        group_by_id = {
            group["id"]: group for group in self.payload["colour_groups"]
        }
        patterns = [
            pattern for pattern in self.payload["pattern_types"]
            if pattern["wallpaper_id"] == "p6m"
            and pattern["render_layout"]["kind"] == "orbit"
        ]
        self.assertTrue(patterns)
        self.assertEqual(
            {
                tuple(seed["point"])
                for pattern in patterns
                for seed in pattern["render_layout"]["seeds"]
            },
            {(0.394338, 0.105662)},
        )

        # The rendered diamond has circumradius 13 * 1.55.  Distinct visible
        # centres must be farther apart than two circumradii, independent of
        # motif orientation.
        required_clearance = 2 * 13 * 1.55
        for pattern in patterns:
            group = group_by_id[pattern["colour_group_id"]]
            scene = colour_blind_fingerprint(
                pattern,
                group,
                enumerate_coloured_actions(
                    group["wallpaper_id"], group["generator_colour_actions"]
                ),
            )
            centres = sorted({
                (pose[0] / 1_000, pose[1] / 1_000) for pose in scene
            })
            minimum = min(
                ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
                for index, (ax, ay) in enumerate(centres)
                for bx, by in centres[index + 1:]
            )
            self.assertGreater(minimum, required_clearance, pattern["id"])

    def test_p2_pp7_pp8_follow_the_source_merge_layout(self) -> None:
        patterns = {
            pattern["gs_pattern_type"]: pattern
            for pattern in self.payload["pattern_types"]
            if pattern["wallpaper_id"] == "p2"
        }
        pp7_exchange = patterns["PP7[2]_1"]
        pp7 = patterns["PP7[2]_2"]
        pp8 = patterns["PP8[2]_2"]
        mono_pp7 = patterns["PP7"]
        mono_pp8 = patterns["PP8"]
        for pattern in (mono_pp7, mono_pp8, pp7_exchange, pp7, pp8):
            layout = pattern["render_layout"]
            self.assertEqual(layout["kind"], "fixed_vertical_bands")
            self.assertEqual(layout["band_axis"], "vertical")
            self.assertEqual(layout["origin"], [60, 55])
            self.assertEqual(layout["spacing"], [70, 90])
        self.assertEqual(pp7["render_layout"]["motifs_per_band"], 2)
        self.assertEqual(pp7_exchange["render_layout"]["motifs_per_band"], 2)
        self.assertEqual(pp8["render_layout"]["motifs_per_band"], 1)
        self.assertEqual(mono_pp7["render_layout"]["motifs_per_band"], 2)
        self.assertEqual(mono_pp8["render_layout"]["motifs_per_band"], 1)
        self.assertEqual(
            pp8["render_layout"]["reference_pattern_id"], pp7["id"]
        )
        self.assertEqual(
            pp7_exchange["render_layout"]["reference_pattern_id"],
            pp7_exchange["id"],
        )
        self.assertEqual(pp7_exchange["render_layout"]["colour_rule"], "within_pair")
        self.assertEqual(pp7["render_layout"]["colour_rule"], "by_band")
        self.assertGreater(pp8["render_layout"]["colour_blind_discrepancy"], 0)
        self.assertIn("half-turn symmetric", pp8["render_layout"]["schematic_constraint"])

        group_by_id = {
            group["id"]: group for group in self.payload["colour_groups"]
        }
        self.assertEqual(
            [
                action["permutation_code"]
                for action in group_by_id["cg-p2-2-2"]["generator_colour_actions"]
            ],
            ["1", "1", "AB", "AB"],
        )
        self.assertEqual(
            [
                action["permutation_code"]
                for action in group_by_id["cg-p2-3-1"]["generator_colour_actions"]
            ],
            ["BC", "BC", "AB", "AB"],
        )
        pp7_scene = scene_fingerprint(pp7, group_by_id[pp7["colour_group_id"]])
        pp7_exchange_scene = scene_fingerprint(
            pp7_exchange,
            group_by_id[pp7_exchange["colour_group_id"]],
        )
        pp8_scene = scene_fingerprint(pp8, group_by_id[pp8["colour_group_id"]])
        self.assertEqual(
            colour_blind_fingerprint(
                pp7_exchange,
                group_by_id[pp7_exchange["colour_group_id"]],
            ),
            colour_blind_fingerprint(
                pp7,
                group_by_id[pp7["colour_group_id"]],
            ),
        )
        self.assertEqual(len(pp7_exchange_scene), len(pp7_scene))
        self.assertEqual(len(pp7_scene), 2 * len(pp8_scene))
        # Sorted left-to-right in one row: the first PP7 colouring alternates
        # inside every pair, the second has AA|BB paired bands, and PP8 has
        # A|B single bands on the same band centres.
        pp7_exchange_row = sorted(
            pose for pose in pp7_exchange_scene if pose[1] < 100_000
        )
        pp7_row = sorted(pose for pose in pp7_scene if pose[1] < 100_000)
        pp8_row = sorted(pose for pose in pp8_scene if pose[1] < 100_000)
        self.assertEqual(
            [pose[-1] // 10 for pose in pp7_exchange_row[:4]],
            [0, 1, 0, 1],
        )
        self.assertEqual([pose[-1] // 10 for pose in pp7_row[:4]], [0, 0, 1, 1])
        self.assertEqual([pose[-1] // 10 for pose in pp8_row[:4]], [0, 1, 0, 1])

        p2_geometry = next(
            wallpaper["render_geometry"]
            for wallpaper in self.payload["wallpaper_groups"]
            if wallpaper["id"] == "p2"
        )
        beta = next(
            generator for generator in p2_geometry["generators"]
            if generator["generator"] == "β"
        )
        self.assertEqual(beta["translation"], [0.0, 1.0])

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
        self.assertEqual(
            catalog.short_signature_html("◦¹,³"),
            "◦<sup>1,3</sup>",
        )
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

        self.assertEqual(
            [card["data-directory-wallpaper-id"] for card in self.parser.directory_cards],
            list(catalog.MATHWORLD_DIRECTORY_ORDER),
        )
        self.assertEqual(len(self.parser.directory_images), 17)
        self.assertNotIn("nontrivial groups ·", self.page)
        self.assertIn("MathWorld", self.page)
        self.assertIn("<title>Catalog of colorings</title>", self.page)
        self.assertIn('<h1 id="page-title">Catalog of colorings</h1>', self.page)
        for subtitle in (
            "1. Wallpaper group",
            "2. Chaim Goodman-Strauss colored group",
            "3. Grünbaum–Shephard pattern",
            "Up to 3 colors",
        ):
            self.assertIn(subtitle, self.page)
        self.assertNotIn('class="census"', self.page)
        self.assertNotIn('class="filter-bar"', self.page)
        self.assertNotIn("data-colour-filter", self.page)
        self.assertNotIn("Catalogued object:", self.page)
        self.assertIn("window.COLOR_PATTERN_CATALOG_SETTINGS", self.page)
        self.assertIn("enableGsPatternSelection: false", self.page)
        self.assertIn("color-pattern-catalog.js?v=generator-overlays-v2", self.page)
        self.assertIn("color-pattern-catalog.css?v=generator-overlays-v2", self.page)

    def test_mathworld_directory_has_17_local_crops(self) -> None:
        assets = sorted((ROOT / "output" / "mathworld-wallpaper-groups").glob("*.webp"))
        self.assertEqual(
            {asset.stem for asset in assets},
            {wallpaper["hm"] for wallpaper in self.payload["wallpaper_groups"]},
        )
        for asset in assets:
            self.assertGreater(asset.stat().st_size, 2_000)
            with Image.open(asset) as image:
                self.assertEqual(image.size, (320, 240))

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
        self.assertIn("function enumerateGroupActions", script)
        self.assertNotIn("function applyFilter", script)
        self.assertNotIn("data-colour-filter", script)
        self.assertNotIn("state.filter", script)
        self.assertIn("function composeAffine", script)
        self.assertIn("function composePermutations", script)
        self.assertIn("function patternTemplateSeeds", script)
        self.assertIn("function motifPose", script)
        self.assertIn("function addGeneratorOverlay", script)
        self.assertIn("function addAxisGenerator", script)
        self.assertIn("function addRotationGenerator", script)
        self.assertIn("function chooseLabelPosition", script)
        self.assertIn('class: "pattern-motif"', script)
        self.assertIn('if (kind === "translation") return', script)
        self.assertIn('class: "generator-rotation-centre"', script)
        self.assertIn('class: "generator-label-backing"', script)
        self.assertNotIn("generator-degree", script)
        self.assertIn("Translation generators are omitted", script)
        self.assertEqual(script.count("addGeneratorOverlay(svg, group, wallpaper);"), 2)
        self.assertIn("wallpaper.render_geometry.generators", script)
        self.assertIn("operation.permutation[seed.colour]", script)
        self.assertIn("pattern.render_layout", script)
        self.assertIn("function addFixedVerticalBands", script)
        self.assertNotIn("function layoutDiscrepancyElement", script)
        self.assertNotIn('appendTableRow(table, "Colour-blind Δ"', script)
        self.assertIn('document.createTextNode("permutations of")', script)
        self.assertIn("Permutations of canonical colour labels", script)
        self.assertIn("enableGsPatternSelection", script)
        self.assertIn('tab.setAttribute("aria-disabled", "true")', script)
        self.assertIn("temporarily unavailable while G&S pattern notation is under review", script)
        self.assertIn('tab.getAttribute("aria-disabled") !== "true"', script)
        self.assertIn("history.replaceState", script)
        self.assertNotIn("Math.max(1, pattern.number_of_colours - 1)", script)
        self.assertNotIn("function buildP4TwoColourPattern", script)
        self.assertNotIn("const motifScale", script)
        self.assertNotIn("layoutVariant * 7", script)
        self.assertNotIn("const paths = [", script)
        self.assertIn('link.target = "color-pattern-book-excerpt"', script)
        self.assertIn("book-excerpt.html?v=one-colour-source-v1", script)
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
        sot_specs = {
            path: spec for path, spec in specs.items() if spec["kind"] == "sot"
        }
        detected = {
            path: spec for path, spec in sot_specs.items() if "highlight_probe" in spec
        }
        blank = {
            path: spec
            for path, spec in sot_specs.items()
            if spec.get("blank_short_signature") is True
        }
        self.assertEqual(len(detected), 68)
        self.assertEqual(
            blank.keys(),
            {"output/color-pattern-excerpts/tos-cg-p6-3-2.webp"},
        )
        self.assertEqual(excerpt_generator.INK_PADDING_POINTS, 4.5)
        for path, spec in detected.items():
            self.assertNotIn("highlight", spec, path)
            self.assertNotIn("blank_short_signature", spec, path)
            probe_x, probe_y, probe_width, probe_height = spec["highlight_probe"]
            self.assertGreater(probe_width, 0, path)
            self.assertGreater(probe_height, 0, path)
            self.assertGreaterEqual(probe_x, 0, path)
            self.assertGreaterEqual(probe_y, 0, path)
            self.assertLessEqual(probe_x + probe_width, 612, path)
            self.assertLessEqual(probe_y + probe_height, 792, path)
        blank_spec = next(iter(blank.values()))
        self.assertNotIn("highlight_probe", blank_spec)
        self.assertIn("highlight", blank_spec)
        regression_probes = {
            # Reported example: *²3²3²3 must hug the notation, not its cell.
            "output/color-pattern-excerpts/tos-cg-p3m1-2-1.webp": (
                330.34,
                337.16,
                32.28,
                12.23,
            ),
            # g129: select *¹4²4¹2, not its *442/*2222 type cell.
            "output/color-pattern-excerpts/tos-cg-p4m-2-4.webp": (
                330.34,
                248.24,
                32.28,
                12.35,
            ),
            # The final p. 141 block formerly reached the preceding row or
            # the Table 11.1 continuation caption.
            "output/color-pattern-excerpts/tos-cg-pg-2-2.webp": (
                217.66,
                303.80,
                20.61,
                12.35,
            ),
            "output/color-pattern-excerpts/tos-cg-pg-2-1.webp": (
                230.26,
                314.84,
                22.05,
                12.23,
            ),
            "output/color-pattern-excerpts/tos-cg-p1-2-1.webp": (
                215.14,
                326.12,
                13.29,
                12.35,
            ),
        }
        for path, probe in regression_probes.items():
            self.assertEqual(sot_specs[path]["highlight_probe"], probe, path)
        self.assertEqual(blank_spec["highlight"], (337.0, 199.5, 76.0, 13.0))

        self.assertEqual(
            BOOK_EXCERPTS["p164::632³/2222-exact"]["highlight"],
            (307, 354, 72, 18),
        )
        self.assertIn(
            "short form is ³6³3¹2",
            BOOK_EXCERPTS["p164::632³/2222-exact"]["context"],
        )
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

    def test_every_sot_outline_is_baked_and_tight_around_its_selected_target(self) -> None:
        specs = {
            path: spec
            for path, spec in build_excerpt_specs(self.payload).items()
            if spec["kind"] == "sot"
        }
        self.assertEqual(len(specs), 69)
        blank_path = "output/color-pattern-excerpts/tos-cg-p6-3-2.webp"
        source_pdf = ROOT / "Conway J., Goodman-Strauss C. (2008) The Symmetries of Things.pdf"
        self.assertTrue(source_pdf.is_file())

        def outline_mask(rgb: Image.Image) -> Image.Image:
            red, green, blue = rgb.split()
            red_enough = red.point(lambda value: 255 if value > 130 else 0)
            red_over_green = ImageChops.subtract(red, green).point(
                lambda value: 255 if value > 65 else 0
            )
            red_over_blue = ImageChops.subtract(red, blue).point(
                lambda value: 255 if value > 80 else 0
            )
            return ImageChops.darker(
                red_enough,
                ImageChops.darker(red_over_green, red_over_blue),
            )

        def filtered_probe_ink_box(
            page: Image.Image,
            probe: tuple[float, float, float, float],
        ) -> tuple[int, int, int, int]:
            probe_box = excerpt_generator._box(
                probe,
                page,
                excerpt_generator.SOURCE_SIZE["sot"],
            )
            mask = page.crop(probe_box).convert("L").point(
                lambda value: 255
                if value < excerpt_generator.INK_THRESHOLD
                else 0
            )
            width, height = mask.size
            pixels = mask.load()
            rule_cutoff = max(
                1,
                round(width * excerpt_generator.HORIZONTAL_RULE_DENSITY),
            )
            rule_rows = [
                row
                for row in range(height)
                if sum(bool(pixels[column, row]) for column in range(width))
                >= rule_cutoff
            ]
            if rule_rows:
                draw = ImageDraw.Draw(mask)
                for row in rule_rows:
                    draw.line((0, row, width - 1, row), fill=0)
            ink = mask.getbbox()
            self.assertIsNotNone(ink)
            assert ink is not None
            return (
                probe_box[0] + ink[0],
                probe_box[1] + ink[1],
                probe_box[0] + ink[2],
                probe_box[1] + ink[3],
            )

        def framed_highlight_box(
            pages: dict[int, Image.Image],
            spec: dict[str, object],
            highlight: tuple[int, int, int, int],
        ) -> tuple[int, int, int, int]:
            panels = spec["table_panels"]
            assert isinstance(panels, tuple)
            panel_boxes = [
                excerpt_generator._box(
                    panel["crop"],
                    pages[panel["pdf_page"]],
                    excerpt_generator.SOURCE_SIZE["sot"],
                )
                for panel in panels
            ]
            content_width = max(right - left for left, _top, right, _bottom in panel_boxes)
            y_offset = 0
            for panel, crop_box in zip(panels, panel_boxes):
                panel_width = crop_box[2] - crop_box[0]
                panel_height = crop_box[3] - crop_box[1]
                if panel["pdf_page"] == spec["pdf_page"]:
                    x_offset = (content_width - panel_width) // 2
                    return (
                        12 + x_offset + highlight[0] - crop_box[0],
                        12 + y_offset + highlight[1] - crop_box[1],
                        12 + x_offset + highlight[2] - crop_box[0],
                        12 + y_offset + highlight[3] - crop_box[1],
                    )
                y_offset += panel_height + 18
            self.fail(f"highlight page missing from table panels: {spec}")

        with tempfile.TemporaryDirectory(prefix="sot-outline-test-") as raw:
            pages = excerpt_generator._render_pages(
                source_pdf,
                {159, 160, 175},
                Path(raw),
                "sot",
            )
            for path, spec in specs.items():
                with self.subTest(path=path):
                    page = pages[spec["pdf_page"]]
                    if path == blank_path:
                        self.assertTrue(spec.get("blank_short_signature"), path)
                        highlight = excerpt_generator._box(
                            spec["highlight"],
                            page,
                            excerpt_generator.SOURCE_SIZE["sot"],
                        )
                    else:
                        probe = spec["highlight_probe"]
                        ink = filtered_probe_ink_box(page, probe)
                        highlight = excerpt_generator._detected_table_ink_box(
                            page,
                            probe,
                            excerpt_generator.SOURCE_SIZE["sot"],
                        )
                        pad_x = round(
                            excerpt_generator.INK_PADDING_POINTS
                            * page.width
                            / excerpt_generator.SOURCE_SIZE["sot"][0]
                        )
                        pad_y = round(
                            excerpt_generator.INK_PADDING_POINTS
                            * page.height
                            / excerpt_generator.SOURCE_SIZE["sot"][1]
                        )
                        self.assertEqual(
                            highlight,
                            (
                                ink[0] - pad_x,
                                ink[1] - pad_y,
                                ink[2] + pad_x,
                                ink[3] + pad_y,
                            ),
                            path,
                        )

                    expected = framed_highlight_box(pages, spec, highlight)
                    with Image.open(ROOT / path) as image:
                        outline = outline_mask(image.convert("RGB"))
                    # Pillow's rounded rectangle includes its right and bottom
                    # coordinates, while getbbox returns exclusive bounds.
                    self.assertEqual(
                        outline.getbbox(),
                        (expected[0], expected[1], expected[2] + 1, expected[3] + 1),
                        path,
                    )

    def test_sot_table_detector_has_fixed_padding_and_rejects_ambiguous_probes(self) -> None:
        page = Image.new("RGB", (300, 300), "white")
        draw = ImageDraw.Draw(page)
        draw.rectangle((60, 45, 109, 64), fill="black")
        source_size = (100.0, 100.0)
        probe = (10.0, 10.0, 50.0, 20.0)

        self.assertEqual(excerpt_generator.INK_PADDING_POINTS, 4.5)
        self.assertEqual(
            excerpt_generator._detected_table_ink_box(page, probe, source_size),
            (46, 31, 124, 79),
        )

        ambiguous = page.copy()
        ImageDraw.Draw(ambiguous).rectangle((60, 78, 109, 84), fill="black")
        with self.assertRaisesRegex(ValueError, "ambiguous table highlight probe"):
            excerpt_generator._detected_table_ink_box(
                ambiguous,
                probe,
                source_size,
            )

        clipped = Image.new("RGB", (300, 300), "white")
        ImageDraw.Draw(clipped).rectangle((30, 45, 60, 64), fill="black")
        with self.assertRaisesRegex(ValueError, "clips notation ink at its edge"):
            excerpt_generator._detected_table_ink_box(
                clipped,
                probe,
                source_size,
            )

    def test_sot_only_excerpt_selection_does_not_require_or_render_gs(self) -> None:
        rendered_sources: list[tuple[Path, set[int], str]] = []

        def fake_render_pages(
            source_pdf: Path,
            pages: set[int],
            _directory: Path,
            prefix: str,
        ) -> dict[int, Image.Image]:
            rendered_sources.append((source_pdf, pages, prefix))
            return {}

        sot_pdf = Path("source-sot.pdf")
        with (
            patch.object(excerpt_generator, "build_payload", return_value=self.payload),
            patch.object(excerpt_generator, "_render_pages", side_effect=fake_render_pages),
            patch.object(excerpt_generator, "render_excerpt", return_value=b"excerpt"),
        ):
            assets = excerpt_generator.expected_assets(
                sot_pdf,
                None,
                kind="sot",
            )

        self.assertEqual(len(assets), 69)
        self.assertTrue(all(path.name.startswith("tos-") for path in assets))
        self.assertEqual(
            rendered_sources,
            [(sot_pdf, {159, 160, 175}, "sot")],
        )

    def test_sot_only_write_preserves_gs_and_byte_identical_assets(self) -> None:
        (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="sot-only-test-", dir=ROOT / "tmp") as raw:
            temporary = Path(raw)
            output = temporary / "output"
            output.mkdir()
            source_pdf = temporary / "sot.pdf"
            source_pdf.write_bytes(b"pdf fixture")
            unchanged = output / "tos-current.webp"
            new = output / "tos-new.webp"
            stale = output / "tos-stale.webp"
            preserved = output / "gs-preserved.webp"
            unchanged.write_bytes(b"same")
            stale.write_bytes(b"stale")
            preserved.write_bytes(b"gs")
            unchanged_mtime = unchanged.stat().st_mtime_ns

            expected = {unchanged: b"same", new: b"new"}
            argv = [
                "generate_color_pattern_book_excerpts.py",
                "--kind",
                "sot",
                "--sot-pdf",
                str(source_pdf),
            ]
            with (
                patch.object(excerpt_generator, "OUTPUT_DIR", output),
                patch.object(excerpt_generator, "expected_assets", return_value=expected) as generate,
                patch.object(sys, "argv", argv),
            ):
                self.assertEqual(excerpt_generator.main(), 0)

            generate.assert_called_once_with(source_pdf.resolve(), None, kind="sot")
            self.assertEqual(unchanged.read_bytes(), b"same")
            self.assertEqual(unchanged.stat().st_mtime_ns, unchanged_mtime)
            self.assertEqual(new.read_bytes(), b"new")
            self.assertFalse(stale.exists())
            self.assertEqual(preserved.read_bytes(), b"gs")

    def test_one_colour_pattern_links_are_honest_chapter_8_cross_references(self) -> None:
        one_colour = [
            pattern for pattern in self.payload["pattern_types"]
            if pattern["number_of_colours"] == 1
        ]
        self.assertEqual(len(one_colour), 51)
        for pattern in one_colour:
            excerpt = pattern["book_excerpt"]
            self.assertFalse(excerpt["direct_source"])
            self.assertEqual(excerpt["relationship"], "underlying-pattern-type")
            self.assertEqual(excerpt["catalog_symbol"], pattern["gs_pattern_type"])
            self.assertIn("indirect cross-reference", excerpt["context"])
            self.assertNotEqual(excerpt["source_symbol"], pattern["gs_pattern_type"])

        coloured = [
            pattern for pattern in self.payload["pattern_types"]
            if pattern["number_of_colours"] > 1
        ]
        self.assertEqual(len(coloured), 147)
        self.assertTrue(all(pattern["book_excerpt"]["direct_source"] for pattern in coloured))

        p2 = {
            pattern["gs_pattern_type"]: pattern
            for pattern in one_colour if pattern["wallpaper_id"] == "p2"
        }
        self.assertEqual(set(p2), {"PP7", "PP8"})
        self.assertTrue(p2["PP7"]["underlying_pattern_is_primitive"])
        self.assertFalse(p2["PP8"]["underlying_pattern_is_primitive"])
        self.assertEqual(p2["PP7"]["book_excerpt"]["source_symbol"], "PP7[2]_1")
        self.assertEqual(p2["PP8"]["book_excerpt"]["source_symbol"], "PP8[2]_2")

        script = (ROOT / "color-pattern-catalog.js").read_text(encoding="utf-8")
        self.assertIn("function gsGroupSymbolElement", script)
        self.assertIn("function gsPatternTypeElement", script)
        self.assertIn("if (group.number_of_colours === 1)", script)
        self.assertIn("if (pattern.book_excerpt.direct_source)", script)

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
