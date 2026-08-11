from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_color_forward_census as census  # noqa: E402


class ColorForwardCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(census.MANIFEST.read_text(encoding="utf-8"))
        cls.payload = census.build_payload(cls.manifest)

    def test_manifest_is_the_audited_68_group_extract(self) -> None:
        metadata = self.manifest["meta"]
        groups = self.manifest["groups"]
        self.assertEqual(
            metadata["source_catalog_sha256"],
            census.EXPECTED_SOURCE_CATALOG_SHA256,
        )
        self.assertEqual(
            metadata["source_description"],
            "Pinned 275-group catalog snapshot",
        )
        self.assertNotIn("source_repository", metadata)
        self.assertEqual(metadata["source_catalog_total_groups"], 275)
        self.assertEqual(metadata["forward_groups"], 68)
        self.assertEqual(len(groups), 68)
        self.assertEqual(len({group["id"] for group in groups}), 68)
        self.assertEqual(
            set(groups[0]),
            {"id", "symbol", "base", "canonical_clock_order"},
        )

    def test_summary_vectors_are_pinned(self) -> None:
        rows = self.payload["summary"]
        self.assertEqual(
            [row["wieting_all_transitive"] for row in rows],
            [17, 46, 23, 96, 14, 90],
        )
        self.assertEqual(
            [row["regular_cyclic_kernels"] for row in rows],
            [17, 46, 8, 13, 4, 13],
        )
        self.assertEqual(
            [row["forward_catalog_canonical_clock_order"] for row in rows],
            [17, 36, 6, 6, 0, 3],
        )

    def test_orbifold_is_primary_and_hm_is_retained(self) -> None:
        rows = self.payload["by_wallpaper"]
        self.assertEqual(
            [row["orbifold"] for row in rows],
            [census.ORBIFOLD_BY_BASE[base] for base in census.BASE_ORDER],
        )
        self.assertEqual(
            [row["wallpaper_group"] for row in rows],
            list(census.BASE_ORDER),
        )
        self.assertEqual(
            self.payload["meta"]["label_conventions"]["primary"],
            "Conway orbifold notation",
        )

        csv_rows = list(
            csv.DictReader(io.StringIO(census.orbifold_csv_text(self.payload)))
        )
        self.assertEqual(
            list(csv_rows[0]),
            [
                "orbifold",
                "wallpaper_group",
                "cyclic_n1",
                "cyclic_n2",
                "cyclic_n3",
                "cyclic_n4",
                "cyclic_n5",
                "cyclic_n6",
                "film_n1",
                "film_n2",
                "film_n3",
                "film_n4",
                "film_n5",
                "film_n6",
                "forward_total",
            ],
        )

    def test_every_forward_group_occurs_once_and_reconciles(self) -> None:
        items = [
            item
            for group_items in self.payload["forward_groups_by_order"].values()
            for item in group_items
        ]
        ids = [item["id"] for item in items]
        self.assertEqual(len(ids), 68)
        self.assertEqual(len(set(ids)), 68)
        self.assertEqual(
            sum(row["forward_total"] for row in self.payload["by_wallpaper"]),
            68,
        )

        for n in range(1, census.MAX_COLOURS + 1):
            self.assertEqual(
                sum(
                    row["forward_catalog"][str(n)]
                    for row in self.payload["by_wallpaper"]
                ),
                self.payload["summary"][n - 1][
                    "forward_catalog_canonical_clock_order"
                ],
            )

    def test_tracked_generated_files_are_current(self) -> None:
        for path, expected in census.outputs(self.manifest).items():
            self.assertEqual(path.read_text(encoding="utf-8"), expected, path)


if __name__ == "__main__":
    unittest.main()
