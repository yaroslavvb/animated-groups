from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest


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
        self.motion_images = 0
        self.orbifold_text: list[str] = []
        self.orbifold_labels: list[str | None] = []
        self.links: list[str] = []
        self._symmetry_depth = 0
        self._orbifold_parts: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        classes = _classes(attributes)

        if tag == "article" and "symmetry" in classes:
            self.symmetry_articles += 1
            self._symmetry_depth += 1
        elif tag == "figure" and self._symmetry_depth:
            self.symmetry_figures += 1
        elif tag == "img" and "motion-image" in classes:
            self.motion_images += 1

        if tag == "code" and "orbifold" in classes:
            self._orbifold_parts = []
            self.orbifold_labels.append(attributes.get("aria-label"))

        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "code" and self._orbifold_parts is not None:
            self.orbifold_text.append("".join(self._orbifold_parts))
            self._orbifold_parts = None
        if tag == "article" and self._symmetry_depth:
            self._symmetry_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._orbifold_parts is not None:
            self._orbifold_parts.append(data)


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
        self.assertEqual(self.parser.motion_images, 33)

    def test_spacetime_orbifold_labels_are_complete_and_ordered(self) -> None:
        actual = tuple(map(_normalized_notation, self.parser.orbifold_text))
        expected = tuple(map(_normalized_notation, self.EXPECTED_ORBIFOLDS))
        self.assertEqual(actual, expected)
        self.assertEqual(len(self.parser.orbifold_labels), 11)
        self.assertTrue(
            all(label and label.strip() for label in self.parser.orbifold_labels)
        )

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
