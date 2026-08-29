from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WALLPAPERS = {
    "p1", "p2", "pm", "pg", "cm", "pmm", "pmg", "pgg", "cmm",
    "p4", "p4m", "p4g", "p3", "p3m1", "p31m", "p6", "p6m",
}


class BrownianPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []
        self.ids: list[str] = []
        self.brownian_links = 0
        self.current_brownian_links = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"] or "")
        for name in ("href", "src"):
            if attributes.get(name):
                self.references.append(attributes[name] or "")
        if tag == "a" and attributes.get("href", "").endswith("brownian.html"):
            self.brownian_links += 1
            if attributes.get("aria-current") == "page":
                self.current_brownian_links += 1


def affine_key(operation: dict[str, object]) -> tuple[float, ...]:
    matrix = operation["M"]
    translation = operation["v"]
    assert isinstance(matrix, list)
    assert isinstance(translation, list)
    normalized = [float(value) % 1 for value in translation]
    return tuple(
        round(float(value), 8)
        for row in matrix
        for value in row
    ) + tuple(round(value, 8) for value in normalized)


def compose(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    a = left["M"]
    b = right["M"]
    av = left["v"]
    bv = right["v"]
    assert isinstance(a, list) and isinstance(b, list)
    assert isinstance(av, list) and isinstance(bv, list)
    matrix = [
        [sum(a[row][k] * b[k][column] for k in range(2)) for column in range(2)]
        for row in range(2)
    ]
    translation = [
        av[row] + sum(a[row][k] * bv[k] for k in range(2))
        for row in range(2)
    ]
    return {"M": matrix, "v": translation}


class BrownianPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = (ROOT / "brownian.html").read_text(encoding="utf-8")
        cls.parser = BrownianPageParser()
        cls.parser.feed(cls.page)
        payload = json.loads(
            (ROOT / "data" / "clockwork-coloring-correspondence.json")
            .read_text(encoding="utf-8")
        )
        cls.products = [
            group for group in payload["groups"]
            if group["product"] and group["clock_order"] == 1
        ]

    def test_page_has_complete_accessible_control_surface(self) -> None:
        self.assertIn("<h1>Symmetric Brownian motion</h1>", self.page)
        self.assertIn('id="wallpaper-group" disabled', self.page)
        self.assertIn('id="brownian-new"', self.page)
        self.assertIn('id="brownian-play"', self.page)
        self.assertIn('id="show-axes"', self.page)
        self.assertIn('id="show-trails"', self.page)
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))
        self.assertEqual(self.parser.current_brownian_links, 1)

    def test_every_local_page_reference_exists(self) -> None:
        for reference in self.parser.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = ROOT / unquote(parsed.path.lstrip("/"))
            with self.subTest(reference=reference):
                self.assertTrue(target.exists(), target)

    def test_data_contains_exactly_the_seventeen_product_wallpapers(self) -> None:
        self.assertEqual(
            {group["parent"]["hm"] for group in self.products},
            EXPECTED_WALLPAPERS,
        )
        for group in self.products:
            with self.subTest(group=group["id"]):
                self.assertTrue(group["render"]["basis"])
                self.assertTrue(group["render"]["ops"])
                self.assertTrue(all(op["s"] == 1 and op["tau"] == 0 for op in group["render"]["ops"]))

    def test_each_finite_operation_set_is_closed_modulo_the_lattice(self) -> None:
        for group in self.products:
            operations = group["render"]["ops"]
            keys = {affine_key(operation) for operation in operations}
            for left in operations:
                for right in operations:
                    with self.subTest(group=group["id"]):
                        self.assertIn(affine_key(compose(left, right)), keys)

    def test_brownian_assets_are_local_to_this_repository(self) -> None:
        controller = (ROOT / "brownian.js").read_text(encoding="utf-8")
        self.assertIn("clockwork-coloring-correspondence.json", controller)
        self.assertNotIn("animated-groups-fable", controller)
        self.assertNotIn("designer/", controller)
        self.assertNotIn("wallpaper-data", controller)


if __name__ == "__main__":
    unittest.main()
