from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]

GENERATED_TORUS_PAGES = {
    "torus-tutorial.html": "scripts/generate_torus_tutorial.py",
    "torus-patterns.html": "scripts/generate_torus_patterns.py",
    "torus-patterns-c4.html": "scripts/generate_torus_patterns_c4.py",
    "torus-cayley.html": "scripts/generate_torus_cayley.py",
    "torus-nonregular.html": "scripts/generate_torus_nonregular.py",
}
TORUS_PAGES = ("torus-colorings.html", *GENERATED_TORUS_PAGES)


class LocalReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[tuple[str, str, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        for attribute in ("href", "src"):
            value = attributes.get(attribute)
            if value:
                self.references.append((tag, attribute, value))


class CaseTableParser(HTMLParser):
    """Collect table text while retaining the enclosing case section."""

    def __init__(self) -> None:
        super().__init__()
        self.section_stack: list[str | None] = []
        self.tables: list[dict[str, object]] = []
        self.table: dict[str, object] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.caption: list[str] | None = None

    @staticmethod
    def _text(parts: list[str]) -> str:
        return " ".join("".join(parts).split())

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if tag == "section":
            self.section_stack.append(attributes.get("id"))
        elif tag == "table":
            self.table = {
                "section": self.section_stack[-1] if self.section_stack else None,
                "caption": "",
                "rows": [],
            }
        elif self.table is not None and tag == "caption":
            self.caption = []
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.table is not None and tag in {"td", "th"}:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)
        elif self.caption is not None:
            self.caption.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None:
            assert self.row is not None
            self.row.append(self._text(self.cell))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            assert self.table is not None
            rows = self.table["rows"]
            assert isinstance(rows, list)
            rows.append(self.row)
            self.row = None
        elif tag == "caption" and self.caption is not None:
            assert self.table is not None
            self.table["caption"] = self._text(self.caption)
            self.caption = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None
        elif tag == "section":
            self.section_stack.pop()


class TorusMiniSiteTests(unittest.TestCase):
    def test_every_page_exposes_the_complete_torus_navigation(self) -> None:
        for page_name in TORUS_PAGES:
            page = (ROOT / page_name).read_text(encoding="utf-8")
            with self.subTest(page=page_name, current=True):
                self.assertIn(
                    f'href="{page_name}" aria-current="page"',
                    page,
                )
            for destination in TORUS_PAGES:
                with self.subTest(page=page_name, destination=destination):
                    self.assertIn(f'href="{destination}"', page)

    def test_all_five_generated_pages_are_current(self) -> None:
        for page, generator in GENERATED_TORUS_PAGES.items():
            with self.subTest(page=page):
                result = subprocess.run(
                    [sys.executable, str(ROOT / generator), "--check"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"{page} is stale:\n{result.stdout}{result.stderr}",
                )

    def test_all_local_href_and_src_targets_exist(self) -> None:
        for page_name in TORUS_PAGES:
            page = ROOT / page_name
            parser = LocalReferenceParser()
            parser.feed(page.read_text(encoding="utf-8"))
            for tag, attribute, value in parser.references:
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                relative = Path(unquote(parsed.path.lstrip("/")))
                target = (ROOT / relative).resolve()
                with self.subTest(
                    page=page_name,
                    tag=tag,
                    attribute=attribute,
                    value=value,
                ):
                    self.assertTrue(target.exists(), f"missing local target: {target}")

    def test_translation_stabilizer_uses_the_abstract_coset_action(self) -> None:
        parser = CaseTableParser()
        parser.feed((ROOT / "torus-nonregular.html").read_text(encoding="utf-8"))
        tables = {
            table["caption"]: table["rows"]
            for table in parser.tables
            if table["section"] == "case-x"
        }
        self.assertEqual(set(tables), {"the four cosets", "colour stabilizers"})

        expected_cosets = {
            "A": (frozenset({"e", "X"}), "A"),
            "B": (frozenset({"s", "Ys"}), "B"),
            "C": (frozenset({"Y", "XY"}), "C"),
            "D": (frozenset({"Xs", "XYs"}), "D"),
        }
        coset_rows = tables["the four cosets"]
        assert isinstance(coset_rows, list)
        self.assertEqual([row[0] for row in coset_rows], list("ABCD"))
        for colour, members, destination in coset_rows:
            parsed_members = frozenset(
                item.strip() for item in members.strip("{}").split(",")
            )
            expected_members, expected_destination = expected_cosets[colour]
            self.assertEqual(parsed_members, expected_members, colour)
            self.assertEqual(destination, f"sends A → {expected_destination}", colour)

        expected_stabilizers = {
            "A": frozenset({"e", "X"}),
            "B": frozenset({"e", "Y"}),
            "C": frozenset({"e", "X"}),
            "D": frozenset({"e", "Y"}),
        }
        stabilizer_rows = tables["colour stabilizers"]
        assert isinstance(stabilizer_rows, list)
        actual_stabilizers = {
            colour: frozenset(
                item.strip() for item in members.strip("{}").split(",")
            )
            for colour, members in stabilizer_rows
        }
        self.assertEqual(actual_stabilizers, expected_stabilizers)

    def test_half_turn_description_is_not_double_escaped(self) -> None:
        page = (ROOT / "torus-patterns-c4.html").read_text(encoding="utf-8")
        self.assertNotIn("180&amp;deg;", page)
        rendered_text = unescape(page)
        self.assertNotIn("180&deg;", rendered_text)
        self.assertIn("180° turn about a point", rendered_text)


@unittest.skipUnless(shutil.which("node"), "Node.js is required for the browser catalog audit")
class TorusColoringCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        command = "const t=require('./torus-colorings.js');process.stdout.write(JSON.stringify(t.records()));"
        result = subprocess.run(
            ["node", "-e", command],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.records = json.loads(result.stdout)

    def test_catalog_has_the_burnside_count(self) -> None:
        self.assertEqual(len(self.records), 32)
        self.assertEqual(sum(record["orbitSize"] for record in self.records), 512)

    def test_orbit_and_stabilizer_distributions(self) -> None:
        self.assertEqual(
            Counter(record["orbitSize"] for record in self.records),
            Counter({18: 27, 6: 4, 2: 1}),
        )
        for record in self.records:
            self.assertEqual(record["orbitSize"] * record["stabilizerSize"], 18)

    def test_canonical_representatives_use_the_minority_color(self) -> None:
        self.assertEqual(
            Counter(record["weight"] for record in self.records),
            Counter({0: 1, 1: 1, 2: 4, 3: 12, 4: 14}),
        )
        self.assertTrue(all(record["weight"] <= 4 for record in self.records))
        self.assertEqual(len({record["pattern"] for record in self.records}), 32)

    def test_static_page_loads_the_verified_catalog(self) -> None:
        page = (ROOT / "torus-colorings.html").read_text()
        stylesheet = (ROOT / "torus-colorings.css").read_text()
        index = (ROOT / "index.html").read_text()

        self.assertIn("Binary colorings of the 3 × 3 torus", page)
        self.assertIn('data-torus-catalog', page)
        self.assertIn('src="torus-colorings.js?v=1"', page)
        self.assertIn('href="torus-colorings.css?v=2"', page)
        self.assertIn("rotations and reflections are not identified", page)
        self.assertIn(".central-domain", stylesheet)
        self.assertIn('href="torus-tutorial.html">Discrete torus</a>', index)


if __name__ == "__main__":
    unittest.main()
