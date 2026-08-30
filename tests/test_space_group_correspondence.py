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
        self.base_group_ids: list[str] = []
        self.base_group_links: list[tuple[str | None, str]] = []
        self.static_tab_roles: list[tuple[str, str]] = []
        self.article_images: dict[str, list[str]] = defaultdict(list)
        self.article_links: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.presentation_tables: list[str] = []
        self.generator_rows: dict[str, int] = defaultdict(int)
        self.space_summaries: list[str] = []
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
            if attributes.get("role"):
                self.static_tab_roles.append((tag, attributes["role"] or ""))
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
                (attributes.get("data-directory-group", ""), attributes.get("href", ""))
            )
        if tag == "article" and "data-space-tabpanel" in attributes:
            self.current_article = attributes.get("id", "")
            self.panels.append(self.current_article)
            if attributes.get("role"):
                self.static_tab_roles.append((tag, attributes["role"] or ""))
        if tag == "dl" and "base-group" in classes and attributes.get("id"):
            self.base_group_ids.append(attributes["id"] or "")
        if self.current_article is not None:
            if tag == "img":
                self.article_images[self.current_article].append(attributes.get("src", ""))
            if tag == "a":
                self.article_links[self.current_article].append(
                    (attributes.get("class", ""), attributes.get("href", ""))
                )
            if tag == "section" and "space-group-summary" in classes:
                self.space_summaries.append(self.current_article)
            if tag == "table" and attributes.get("data-space-presentation"):
                self.presentation_tables.append(attributes["data-space-presentation"] or "")
            if tag == "tr" and "presentation-generator-row" in classes:
                self.generator_rows[self.current_article] += 1
        if tag == "a" and "base-group-link" in classes:
            self.base_group_links.append(
                (self.current_article, attributes.get("href", ""))
            )

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
        self.assertEqual(self.payload["meta"]["schema_version"], 4)
        self.assertEqual(len(groups), 68)
        self.assertEqual({group["id"] for group in groups}, set(correspondence.SPACE_GROUP_BY_ID))
        numbers = [group["space_group"]["it_number"] for group in groups]
        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertEqual(set(numbers), correspondence.POLAR_IT_NUMBERS)

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
            self.assertEqual(lifted["cell_action_presentation"], original["cell_action_presentation"])
            self.assertEqual(lifted["book_color_signature"], original["book_color_signature"])

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

    def test_all_17_sections_display_only_the_51_nontrivial_pairs(self) -> None:
        expected_ids = [group["id"] for group in self.displayed_groups]
        trivial_ids = [group["id"] for group in self.trivial_groups]
        self.assertEqual(len(expected_ids), correspondence.DISPLAYED_GROUP_COUNT)
        self.assertEqual(len(trivial_ids), correspondence.OMITTED_TRIVIAL_COUNT)
        self.assertEqual(
            self.parser.family_ids,
            [f"wallpaper-{base}" for base in correspondence.BASE_ORDER],
        )
        self.assertEqual(self.parser.empty_family_ids, ["wallpaper-p1", "wallpaper-pm", "wallpaper-pg"])
        self.assertEqual(self.parser.tabs_containers, correspondence.DISPLAYED_FAMILY_COUNT)
        self.assertEqual(self.parser.tablists, correspondence.DISPLAYED_FAMILY_COUNT)
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
        self.assertEqual(self.parser.space_summaries, expected_ids)
        self.assertEqual(self.parser.presentation_tables, expected_ids)
        self.assertEqual(
            self.parser.directory_groups,
            [(group_id, f"#{group_id}") for group_id in expected_ids],
        )
        self.assertEqual(self.parser.base_group_ids, trivial_ids)
        self.assertNotIn("data-trivial-product", self.page)
        self.assertNotIn("C<sub>1</sub> product", self.page)
        self.assertNotIn("More-than-one-colour orders", self.page)
        self.assertNotIn('class="family-census"', self.page)

    def test_every_panel_contains_only_the_colouring_plate_and_compact_space_summary(self) -> None:
        for group in self.displayed_groups:
            group_id = group["id"]
            self.assertEqual(self.parser.article_images[group_id], [group["image"]], group_id)
            self.assertEqual(
                self.parser.article_links[group_id],
                [
                    ("colouring-catalog-link", group["catalog_url"]),
                    ("ucl-link", group["space_group"]["ucl_reference_url"]),
                    (
                        "base-group-link",
                        next(
                            base_group["space_group"]["ucl_reference_url"]
                            for base_group in self.trivial_groups
                            if base_group["parent"]["hm"] == group["parent"]["hm"]
                        ),
                    ),
                ],
                group_id,
            )
            presentation = group["cell_action_presentation"]
            self.assertEqual(
                self.parser.generator_rows[group_id], len(presentation["generators"]), group_id
            )
            article = re.search(
                rf'<article[^>]+id="{group_id}"[^>]*>.*?</article>', self.page, re.DOTALL
            )
            self.assertIsNotNone(article, group_id)
            markup = article.group(0)
            self.assertIn(
                f'class="space-group-name">{correspondence._hm_html(group["space_group"]["hm_short"])}',
                markup,
            )
            self.assertNotIn('class="colouring-signature', markup)
            self.assertIn("Colouring ↗", markup)

        for obsolete in (
            "data-space-viewer",
            "data-space-canvas",
            "data-space-controls",
            "space-reference-preview",
            "group-data",
            "lift-copy",
            "entry-badges",
            "entry-identity",
            "visual-sequence",
        ):
            self.assertNotIn(obsolete, self.page)
        self.assertNotIn("output/space-groups/", "\n".join(
            image for images in self.parser.article_images.values() for image in images
        ))

    def test_base_groups_are_compact_right_pane_entries(self) -> None:
        trivial_by_base = {
            group["parent"]["hm"]: group for group in self.trivial_groups
        }
        expected_links = []
        for base in correspondence.BASE_ORDER:
            rows = [
                group for group in self.displayed_groups
                if group["parent"]["hm"] == base
            ]
            base_url = trivial_by_base[base]["space_group"]["ucl_reference_url"]
            if rows:
                expected_links.extend((group["id"], base_url) for group in rows)
            else:
                expected_links.append((None, base_url))
        self.assertEqual(self.parser.base_group_links, expected_links)
        self.assertEqual(
            self.page.count('class="base-group"'),
            len(self.displayed_groups) + len(correspondence.BASE_ORDER) - len(self.contributing_bases),
        )

        for group_id in ("g233", "g234", "g235"):
            article = re.search(
                rf'<article[^>]+id="{group_id}"[^>]*>.*?</article>',
                self.page,
                re.DOTALL,
            )
            self.assertIsNotNone(article, group_id)
            markup = article.group(0)
            self.assertIn("<dt>Base group</dt>", markup)
            self.assertIn(correspondence.clockwork.orbifold_html("3*3"), markup)
            self.assertIn(">P31m</a>", markup)

    def test_navigation_uses_goodman_strauss_orbifold_notation(self) -> None:
        self.assertNotIn("Orbifold family ", self.page)
        self.assertNotIn('class="family-hm"', self.page)
        self.assertNotIn('class="directory-space-group"', self.page)
        self.assertNotIn('class="tab-space-name"', self.page)

        for base in correspondence.BASE_ORDER:
            orbifold_html = correspondence.clockwork.orbifold_html(
                correspondence.ORBIFOLD_BY_BASE[base]
            )
            self.assertIn(
                f'id="wallpaper-{base}-title"><span class="family-orbifold">'
                f'{orbifold_html}</span>',
                self.page,
                base,
            )
            if base in self.contributing_bases:
                self.assertIn(
                    f'class="directory-family-link" href="#wallpaper-{base}">'
                    f'{orbifold_html}<span class="directory-family-count">',
                    self.page,
                    base,
                )

        expected_palette_swatches = 0
        for group in self.displayed_groups:
            group_id = group["id"]
            signature_html = correspondence.clockwork.superscript_html(
                group["book_color_signature"]
            )
            expected_signature = correspondence.clockwork.book_color_signature(
                group_id,
                group["parent"]["orbifold"],
                group["tos_notation"],
                group["clock_order"],
            )
            self.assertEqual(group["book_color_signature"], expected_signature, group_id)
            tab = re.search(
                rf'<a id="tab-{group_id}".*?</a>', self.page, re.DOTALL
            )
            directory = re.search(
                rf'<a class="directory-group"[^>]+data-directory-group="{group_id}".*?</a>',
                self.page,
                re.DOTALL,
            )
            self.assertIsNotNone(tab, group_id)
            self.assertIsNotNone(directory, group_id)
            self.assertIn(signature_html, tab.group(0), group_id)
            self.assertIn(signature_html, directory.group(0), group_id)
            self.assertIn(f">{group_id} · C<sub>{group['clock_order']}</sub>", tab.group(0))
            self.assertIn(f">{group_id}</span>", directory.group(0))
            expected_palette_swatches += group["clock_order"]

        self.assertEqual(
            self.page.count("--directory-colour:"), expected_palette_swatches
        )
        for left, right in (("g96", "g97"), ("g225", "g226"), ("g244", "g245"), ("g247", "g248")):
            by_id = {group["id"]: group for group in self.displayed_groups}
            self.assertEqual(
                by_id[left]["book_color_signature"], by_id[right]["book_color_signature"]
            )

        css = (ROOT / "space-group-correspondence.css").read_text(encoding="utf-8")
        self.assertIn(".orbifold-star", css)
        self.assertIn(".book-color-signature sup", css)
        self.assertIn(".directory-palette", css)
        self.assertIn(".directory-family-count", css)
        self.assertNotIn(".directory-family h3 span", css)

    def test_every_displayed_group_stores_a_complete_relative_cell_presentation(self) -> None:
        for group in self.displayed_groups:
            self.assertEqual(
                group["cell_action_presentation"],
                correspondence.clockwork.cell_action_presentation(
                    group["id"], group["render"], group["parent"]["hm"]
                ),
                group["id"],
            )
            presentation = group["space_group_presentation"]
            self.assertEqual(presentation, correspondence._space_group_presentation(group), group["id"])
            self.assertEqual(presentation["relative_to"], "displayed unit cell")
            names = [generator["name"] for generator in presentation["generators"]]
            self.assertEqual(names[:3], ["a", "b", "c"], group["id"])
            self.assertTrue(
                all(set(generator) == {"name", "operation"} for generator in presentation["generators"]),
                group["id"],
            )
            self.assertEqual(
                names[3:],
                [chr(ord("A") + index) for index in range(len(names) - 3)],
                group["id"],
            )
            self.assertEqual(set(presentation["relations"]), {"lattice", "action", "cell"})
            self.assertEqual(
                presentation["relations"]["lattice"],
                ["ab = ba", "ac = ca", "bc = cb"],
            )
            self.assertEqual(
                len(presentation["relations"]["action"]), len(names) - 3, group["id"]
            )
            self.assertTrue(presentation["relations"]["cell"], group["id"])

        by_id = {group["id"]: group for group in self.displayed_groups}
        golden = {
            "g6": ["A² = c"],
            "g7": ["A² = bc", "B² = 1", "AB = b · BA"],
            "g75": ["A² = c", "B⁴ = bc³", "(AB)⁴ = ac⁵", "AB² = b⁻¹ · B²A"],
            "g96": ["A⁴ = c"],
            "g234": ["A² = 1", "B³ = c²", "B(ABA) = a · (ABA)B"],
            "g244": ["A⁶ = c⁴"],
        }
        for group_id, relations in golden.items():
            self.assertEqual(by_id[group_id]["space_group_presentation"]["relations"]["cell"], relations)

    def test_visible_presentations_use_the_compact_cell_quotient(self) -> None:
        for group in self.displayed_groups:
            group_id = group["id"]
            quotient = group["cell_action_presentation"]
            names = ", ".join(generator["name"] for generator in quotient["generators"])
            expected = (
                f"<span>G/Λ = ⟨{names} | {quotient['relations']}⟩</span>"
            )
            article = re.search(
                rf'<article[^>]+id="{group_id}"[^>]*>.*?</article>',
                self.page,
                re.DOTALL,
            )
            self.assertIsNotNone(article, group_id)
            markup = article.group(0)
            self.assertIn(expected, markup, group_id)

            full = group["space_group_presentation"]
            lifted_names = [
                generator["name"]
                for generator in full["generators"]
                if generator["name"] not in {"a", "b", "c"}
            ]
            self.assertEqual(
                lifted_names,
                [generator["name"] for generator in quotient["generators"]],
                group_id,
            )

        self.assertEqual(
            self.page.count('>Presentation</h4>'), correspondence.DISPLAYED_GROUP_COUNT
        )
        self.assertEqual(self.page.count(">Relations</strong>"), correspondence.DISPLAYED_GROUP_COUNT)
        self.assertEqual(self.page.count("<span>G/Λ = ⟨"), correspondence.DISPLAYED_GROUP_COUNT)
        self.assertNotIn("G/Λ₃", self.page)
        self.assertNotIn("<span>G = ⟨", self.page)
        self.assertNotIn("displayed lift-cell coordinates", self.page)
        self.assertNotIn('generator-key">a</span>', self.page)
        self.assertNotIn('generator-key">b</span>', self.page)
        self.assertNotIn('generator-key">c</span>', self.page)
        self.assertNotIn("Unit translation along a", self.page)
        self.assertNotIn("Unit translation along b", self.page)
        self.assertNotIn("Unit translation along the lift axis", self.page)
        self.assertNotIn("A(a,b,c)", self.page)
        self.assertNotIn("(a,b,c)", self.page)
        self.assertNotIn("ab = ba", self.page)
        self.assertIn(
            "G/Λ = ⟨A, B | A² = B² = 1; AB = BA⟩",
            self.page,
        )

    def test_external_links_are_exact_and_unique(self) -> None:
        ucl_urls = []
        catalog_urls = []
        extra_urls_by_catalog: dict[str, list[str]] = defaultdict(list)
        for group in self.payload["groups"]:
            space_group = group["space_group"]
            expected_ucl = (
                f"{correspondence.UCL_SPACE_GROUP_BASE}/"
                f"{correspondence.UCL_PAGE_BY_NUMBER[space_group['it_number']]}"
            )
            expected_catalog = (
                "https://yaroslavvb.github.io/animated-groups-fable/"
                f"catalog.html?time=forward#{group['id']}"
            )
            self.assertEqual(space_group["ucl_reference_url"], expected_ucl)
            self.assertEqual(group["catalog_url"], expected_catalog)
            links = space_group["extra_links"]
            self.assertEqual(
                tuple(link["catalog_id"] for link in links),
                correspondence.EXTRA_CATALOG_IDS,
                group["id"],
            )
            self.assertEqual(
                len({link["url"] for link in links}),
                len(correspondence.EXTRA_CATALOG_IDS),
                group["id"],
            )
            self.assertTrue(
                all(
                    set(link) == {"catalog_id", "catalog", "scope", "target", "url"}
                    and link["catalog"]
                    and link["target"]
                    and link["url"].startswith(("http://", "https://"))
                    for link in links
                ),
                group["id"],
            )
            links_by_id = {link["catalog_id"]: link for link in links}
            number = space_group["it_number"]
            point_group = space_group["point_group"]
            post_slug = "33-3" if number == 33 else str(number)
            self.assertEqual(
                links_by_id["crystal-symmetry-example"]["url"],
                "https://crystalsymmetry.wordpress.com/"
                f"{correspondence.CRYSTAL_SYMMETRY_POST_DATE_BY_NUMBER[number]}/"
                f"{post_slug}/",
            )
            self.assertEqual(
                links_by_id["crystal-symmetry-diagram"]["url"],
                "https://crystalsymmetry.wordpress.com/space-group-diagrams/"
                f"{correspondence.CRYSTAL_SYMMETRY_DIAGRAM_BY_NUMBER[number]}/",
            )
            self.assertEqual(
                links_by_id["iucr-space-group"]["url"],
                "https://onlinelibrary.wiley.com/iucr/itc/Ac/ch2o3v0001/"
                f"sgtable2o3o{number:03d}/",
            )
            self.assertEqual(links_by_id["ucl-space-group"]["url"], expected_ucl)
            self.assertEqual(
                links_by_id["bilbao-point-group"]["url"],
                correspondence.POINT_GROUP_CATALOG_LINKS[point_group]["bilbao"],
            )
            self.assertEqual(
                links_by_id["aflow-prototypes"]["url"],
                f"https://aflow.org/p/{space_group['crystal_system']}_spacegroup.html#sg{number}",
            )
            for catalog_id, source_key in (
                ("gsp-point-group", "gsp"),
                ("webmineral-crystal-class", "webmineral"),
                ("smorf-crystal-form", "smorf"),
            ):
                self.assertEqual(
                    links_by_id[catalog_id]["url"],
                    correspondence.POINT_GROUP_CATALOG_LINKS[point_group][source_key],
                )
            self.assertEqual(
                links_by_id["gemmology-cdl"]["url"],
                "https://gemmology.dev/docs/cdl/#crystal-systems",
            )
            parent_number = correspondence.clockwork.PLANE_GROUP_NUMBER_BY_HM[
                group["parent"]["hm"]
            ]
            self.assertEqual(
                links_by_id["iucr-plane-group"]["url"],
                correspondence.clockwork.IUCR_PLANE_GROUP_URL.format(
                    number=parent_number
                ),
            )
            self.assertEqual(
                links_by_id["jmol-sgsv"]["url"],
                "https://spacegroups.symotter.org/",
            )
            self.assertEqual(
                links_by_id["crystallify"]["url"],
                "https://www.crystallify.com/",
            )
            self.assertEqual(
                links_by_id["jmol-sgsv"]["scope"],
                "manual_space_group_selection",
            )
            self.assertIn(f"No. {number} ", links_by_id["jmol-sgsv"]["target"])
            for link in links:
                extra_urls_by_catalog[link["catalog_id"]].append(link["url"])
            ucl_urls.append(expected_ucl)
            catalog_urls.append(expected_catalog)
        self.assertEqual(len(set(ucl_urls)), 68)
        self.assertEqual(len(set(catalog_urls)), 68)
        for catalog_id in (
            "crystal-symmetry-example",
            "crystal-symmetry-diagram",
            "iucr-space-group",
            "ucl-space-group",
            "aflow-prototypes",
        ):
            self.assertEqual(len(set(extra_urls_by_catalog[catalog_id])), 68)
        for catalog_id in (
            "bilbao-point-group",
            "gsp-point-group",
            "webmineral-crystal-class",
            "smorf-crystal-form",
        ):
            self.assertEqual(len(set(extra_urls_by_catalog[catalog_id])), 10)
        self.assertEqual(self.page.count('class="colouring-catalog-link"'), 51)
        self.assertEqual(self.page.count('class="ucl-link"'), 51)

    def test_filter_metadata_ids_and_deep_links_are_auditable(self) -> None:
        element_ids = re.findall(r'(?<=\s)id="([^"]+)"', self.page)
        self.assertEqual(len(element_ids), len(set(element_ids)))
        for group in self.trivial_groups:
            group_id = group["id"]
            self.assertNotIn(f'data-directory-group="{group_id}"', self.page)
            self.assertNotIn(f'data-panel-id="{group_id}"', self.page)
        controller = (ROOT / "space-group-correspondence.js").read_text(encoding="utf-8")
        self.assertIn('document.getElementById(id)?.scrollIntoView({ block: "start" })', controller)
        self.assertNotIn("fetch(", controller)
        self.assertNotIn("canvas", controller.lower())
        self.assertNotIn("requestAnimationFrame(tick)", controller)

    def test_static_space_group_plates_remain_reproducible_data_assets(self) -> None:
        for group in self.payload["groups"]:
            image_path = ROOT / group["space_group"]["image"]
            self.assertTrue(image_path.is_file(), group["id"])
            with Image.open(image_path) as image:
                self.assertEqual(image.format, "WEBP", group["id"])
                self.assertEqual(image.size, (correspondence.IMAGE_WIDTH, correspondence.IMAGE_HEIGHT))
                self.assertEqual(image.mode, "RGB", group["id"])
                self.assertIsNotNone(image.getbbox(), group["id"])
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
