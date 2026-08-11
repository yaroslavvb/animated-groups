#!/usr/bin/env python3
"""Generate the colour-plane-group / forward-film-group census.

The checked-in manifest is a compact, reproducible extract of the 68 forward
entries in a pinned 275-group catalog snapshot.  Normal runs use only that
manifest; the source catalog is not needed.  To audit or deliberately refresh
the extract, pass the catalog explicitly.  The source is read only.

Run from any directory::

    python3 scripts/generate_color_forward_census.py
    python3 scripts/generate_color_forward_census.py --check
    python3 scripts/generate_color_forward_census.py \
        --source-catalog /path/to/pinned-catalog.json
"""

from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MANIFEST = DATA_DIR / "color-forward-manifest.json"
OUT_JSON = DATA_DIR / "color-forward-census.json"
OUT_CSV = DATA_DIR / "color-forward-census.csv"
OUT_ORBIFOLD_CSV = DATA_DIR / "color-forward-by-orbifold.csv"

MAX_COLOURS = 6
BASE_ORDER = (
    "p1", "p2", "pm", "pg", "cm", "pmm", "pmg", "pgg", "cmm",
    "p4", "p4m", "p4g", "p3", "p3m1", "p31m", "p6", "p6m",
)

# International short (Hermann--Mauguin) notation to Conway orbifold notation.
# The report and its per-group CSV lead with the orbifold symbol; the source
# catalog's HM code remains alongside it for traceability.
ORBIFOLD_BY_BASE = {
    "p1": "o",
    "p2": "2222",
    "pm": "**",
    "pg": "××",
    "cm": "*×",
    "pmm": "*2222",
    "pmg": "22*",
    "pgg": "22×",
    "cmm": "2*22",
    "p4": "442",
    "p4m": "*442",
    "p4g": "4*2",
    "p3": "333",
    "p3m1": "*333",
    "p31m": "3*3",
    "p6": "632",
    "p6m": "*632",
}

# Wieting's aggregate number a(N) of colour plane groups of index N.
WIETING_ALL = {1: 17, 2: 46, 3: 23, 4: 96, 5: 14, 6: 90}

# Affine-normalizer orbits of normal index-N kernels with cyclic quotient C_N.
# The rows are ordered by N=1,...,6.  These are the independently reconstructed
# Senechal--Wieting counts; keeping the 17-row audit prevents aggregate drift.
CYCLIC_BY_BASE = {
    "p1":   (1, 1, 1, 1, 1, 1),
    "p2":   (1, 2, 0, 0, 0, 0),
    "pm":   (1, 5, 1, 3, 1, 5),
    "pg":   (1, 2, 1, 2, 1, 2),
    "cm":   (1, 3, 1, 2, 1, 3),
    "pmm":  (1, 5, 0, 0, 0, 0),
    "pmg":  (1, 5, 0, 0, 0, 0),
    "pgg":  (1, 2, 0, 1, 0, 0),
    "cmm":  (1, 5, 0, 0, 0, 0),
    "p4":   (1, 2, 0, 2, 0, 0),
    "p4m":  (1, 5, 0, 0, 0, 0),
    "p4g":  (1, 3, 0, 2, 0, 0),
    "p3":   (1, 0, 2, 0, 0, 0),
    "p3m1": (1, 1, 0, 0, 0, 0),
    "p31m": (1, 1, 1, 0, 0, 1),
    "p6":   (1, 1, 1, 0, 0, 1),
    "p6m":  (1, 3, 0, 0, 0, 0),
}

EXPECTED_CYCLIC_TOTALS = {1: 17, 2: 46, 3: 8, 4: 13, 5: 4, 6: 13}
EXPECTED_FORWARD_TOTALS = {1: 17, 2: 36, 3: 6, 4: 6, 5: 0, 6: 3}
EXPECTED_SOURCE_CATALOG_SHA256 = (
    "040eebe747815557014c1dbf1d4265d204aaae35c110595f2a15b94ee7f68ca0"
)
SOURCE_DESCRIPTION = "Pinned 275-group catalog snapshot"
SOURCE_CATALOG_PATH = "docs/data/catalog.json"


def exact_tau(value: Any) -> Fraction:
    """Recover a catalog time offset as its exact small rational."""

    raw = float(value) % 1.0
    candidate = Fraction(raw).limit_denominator(12)
    if abs(float(candidate) - raw) > 1e-8:
        raise ValueError(f"time offset is not a small catalog rational: {value!r}")
    return candidate


def canonical_clock_order(group: dict[str, Any]) -> int:
    """Return the LCM of temporal denominators in one forward entry."""

    order = 1
    for operation in group["render"]["ops"]:
        if operation["s"] != 1:
            raise ValueError(f"forward group {group['id']} contains time reversal")
        order = math.lcm(order, exact_tau(operation["tau"]).denominator)
    return order


def manifest_from_catalog(path: Path) -> dict[str, Any]:
    """Read *path* without modifying it and extract the forward catalog rows."""

    raw_catalog = path.read_bytes()
    catalog_sha256 = hashlib.sha256(raw_catalog).hexdigest()
    catalog = json.loads(raw_catalog)
    forward = [group for group in catalog["groups"] if group["forward"]]

    if catalog_sha256 != EXPECTED_SOURCE_CATALOG_SHA256:
        raise ValueError(
            "unexpected source catalog digest; audit the catalog change and "
            "update EXPECTED_SOURCE_CATALOG_SHA256 deliberately: "
            f"{catalog_sha256}"
        )
    if catalog["meta"]["total"] != 275 or len(catalog["groups"]) != 275:
        raise ValueError("source catalog must contain the documented 275 groups")
    if len(forward) != 68:
        raise ValueError("source catalog must contain exactly 68 forward groups")

    groups = [
        {
            "id": group["id"],
            "symbol": group["symbol"],
            "base": group["base"],
            "canonical_clock_order": canonical_clock_order(group),
        }
        for group in forward
    ]
    return {
        "meta": {
            "schema_version": 1,
            "source_description": SOURCE_DESCRIPTION,
            "source_catalog_path": SOURCE_CATALOG_PATH,
            "source_catalog_sha256": catalog_sha256,
            "source_catalog_total_groups": len(catalog["groups"]),
            "forward_groups": len(groups),
            "selection": "catalog group.forward == true",
            "canonical_clock_order": (
                "LCM of the reduced denominators of all displayed temporal "
                "offsets tau in the canonical entry"
            ),
        },
        "groups": groups,
    }


def json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def validate_manifest(manifest: dict[str, Any]) -> None:
    meta = manifest.get("meta", {})
    groups = manifest.get("groups", [])
    ids = [group.get("id") for group in groups]

    if meta.get("source_catalog_sha256") != EXPECTED_SOURCE_CATALOG_SHA256:
        raise ValueError("manifest does not identify the audited source catalog")
    if meta.get("source_catalog_total_groups") != 275:
        raise ValueError("manifest source total must be 275")
    if meta.get("forward_groups") != 68 or len(groups) != 68:
        raise ValueError("manifest must contain exactly 68 forward entries")
    if len(ids) != len(set(ids)):
        raise ValueError("manifest forward ids must be unique")

    required = {"id", "symbol", "base", "canonical_clock_order"}
    for group in groups:
        if set(group) != required:
            raise ValueError(f"unexpected manifest fields in {group!r}")
        if group["base"] not in BASE_ORDER:
            raise ValueError(
                f"unknown wallpaper base in {group['id']}: {group['base']}"
            )
        if group["canonical_clock_order"] not in range(1, MAX_COLOURS + 1):
            raise ValueError(f"clock order outside report range in {group['id']}")


def build_payload(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build all census rows from the compact manifest and pinned references."""

    manifest = load_manifest() if manifest is None else manifest
    validate_manifest(manifest)

    if tuple(ORBIFOLD_BY_BASE) != BASE_ORDER:
        raise AssertionError("orbifold map must exactly follow the 17-group order")
    if len(set(ORBIFOLD_BY_BASE.values())) != len(BASE_ORDER):
        raise AssertionError("Conway orbifold symbols must be unique")
    if tuple(CYCLIC_BY_BASE) != BASE_ORDER:
        raise AssertionError("cyclic audit must exactly follow the 17-group order")

    cyclic_totals = {
        n: sum(CYCLIC_BY_BASE[base][n - 1] for base in BASE_ORDER)
        for n in range(1, MAX_COLOURS + 1)
    }
    if cyclic_totals != EXPECTED_CYCLIC_TOTALS:
        raise AssertionError((cyclic_totals, EXPECTED_CYCLIC_TOTALS))
    if WIETING_ALL[2] != cyclic_totals[2]:
        raise AssertionError("every index-two subgroup must be regular cyclic")

    forward_by_base = {
        base: {n: [] for n in range(1, MAX_COLOURS + 1)}
        for base in BASE_ORDER
    }
    for group in manifest["groups"]:
        base = group["base"]
        order = group["canonical_clock_order"]
        forward_by_base[base][order].append({
            "id": group["id"],
            "symbol": group["symbol"],
            "base": base,
            "orbifold": ORBIFOLD_BY_BASE[base],
            "canonical_clock_order": order,
        })

    forward_totals = {
        n: sum(len(forward_by_base[base][n]) for base in BASE_ORDER)
        for n in range(1, MAX_COLOURS + 1)
    }
    if forward_totals != EXPECTED_FORWARD_TOTALS:
        raise AssertionError((forward_totals, EXPECTED_FORWARD_TOTALS))
    if sum(forward_totals.values()) != 68:
        raise AssertionError("forward-group census must contain exactly 68 entries")

    summary = [
        {
            "colours": n,
            "wieting_all_transitive": WIETING_ALL[n],
            "regular_cyclic_kernels": cyclic_totals[n],
            "forward_catalog_canonical_clock_order": forward_totals[n],
        }
        for n in range(1, MAX_COLOURS + 1)
    ]

    by_wallpaper = []
    for base in BASE_ORDER:
        cyclic = {
            str(n): CYCLIC_BY_BASE[base][n - 1]
            for n in range(1, MAX_COLOURS + 1)
        }
        films = {
            str(n): len(forward_by_base[base][n])
            for n in range(1, MAX_COLOURS + 1)
        }
        by_wallpaper.append({
            "orbifold": ORBIFOLD_BY_BASE[base],
            "wallpaper_group": base,
            "regular_cyclic": cyclic,
            "forward_catalog": films,
            "forward_total": sum(films.values()),
        })

    canonical_manifest = json_text(manifest).encode("utf-8")
    manifest_meta = manifest["meta"]
    return {
        "meta": {
            "schema_version": 2,
            "range": {"minimum_colours": 1, "maximum_colours": MAX_COLOURS},
            "manifest_source": MANIFEST.name,
            "manifest_sha256": hashlib.sha256(canonical_manifest).hexdigest(),
            "source_catalog": {
                "description": manifest_meta["source_description"],
                "path": manifest_meta["source_catalog_path"],
                "sha256": manifest_meta["source_catalog_sha256"],
                "total_groups": manifest_meta["source_catalog_total_groups"],
                "forward_groups": manifest_meta["forward_groups"],
            },
            "label_conventions": {
                "primary": "Conway orbifold notation",
                "orbifold_field": "orbifold",
                "traceability": (
                    "wallpaper_group retains the source catalog's International "
                    "short (Hermann–Mauguin) code"
                ),
            },
            "definitions": {
                "wieting_all_transitive": (
                    "Plane-affine classes of all index-N colour stabilizers."
                ),
                "regular_cyclic_kernels": (
                    "Plane-affine classes of normal index-N kernels with quotient C_N."
                ),
                "forward_catalog_canonical_clock_order": (
                    "Forward representatives in the 275-group source catalog whose "
                    "displayed temporal offsets generate a cyclic group of exact "
                    "order N."
                ),
            },
            "warning": (
                "The three columns use different equivalence relations. The forward "
                "column is a canonical-representative statistic, not the number of "
                "all N-colourings of forward film groups."
            ),
            "sources": [
                {
                    "label": "Wieting Table 11 totals (OEIS A307293)",
                    "url": "https://oeis.org/A307293",
                },
                {
                    "label": "Pinned Senechal-Wieting subgroup reconstruction",
                    "url": (
                        "https://github.com/yaroslavvb/wieting-subgroups/tree/"
                        "dc192b34f206e6fd8e0533c6a25ab89a6055b9ff"
                    ),
                },
                {
                    "label": "Jarratt-Schwarzenberger coloured plane groups",
                    "url": "https://doi.org/10.1107/S0567739480001866",
                },
            ],
        },
        "summary": summary,
        "by_wallpaper": by_wallpaper,
        "forward_groups_by_order": {
            str(n): [
                group
                for base in BASE_ORDER
                for group in forward_by_base[base][n]
            ]
            for n in range(1, MAX_COLOURS + 1)
        },
    }


def summary_csv_text(payload: dict[str, Any]) -> str:
    buffer = io.StringIO(newline="")
    fields = (
        "colours",
        "wieting_all_transitive",
        "regular_cyclic_kernels",
        "forward_catalog_canonical_clock_order",
    )
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(payload["summary"])
    return buffer.getvalue()


def orbifold_csv_text(payload: dict[str, Any]) -> str:
    buffer = io.StringIO(newline="")
    fields = ["orbifold", "wallpaper_group"]
    fields += [f"cyclic_n{n}" for n in range(1, MAX_COLOURS + 1)]
    fields += [f"film_n{n}" for n in range(1, MAX_COLOURS + 1)]
    fields += ["forward_total"]
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in payload["by_wallpaper"]:
        output = {
            "orbifold": row["orbifold"],
            "wallpaper_group": row["wallpaper_group"],
            "forward_total": row["forward_total"],
        }
        for n in range(1, MAX_COLOURS + 1):
            output[f"cyclic_n{n}"] = row["regular_cyclic"][str(n)]
            output[f"film_n{n}"] = row["forward_catalog"][str(n)]
        writer.writerow(output)
    return buffer.getvalue()


def outputs(
    manifest: dict[str, Any], *, include_manifest: bool = False
) -> dict[Path, str]:
    payload = build_payload(manifest)
    generated = {
        OUT_JSON: json_text(payload),
        OUT_CSV: summary_csv_text(payload),
        OUT_ORBIFOLD_CSV: orbifold_csv_text(payload),
    }
    if include_manifest:
        generated = {MANIFEST: json_text(manifest), **generated}
    return generated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if tracked outputs differ from a fresh census",
    )
    parser.add_argument(
        "--source-catalog",
        type=Path,
        metavar="PATH",
        help=(
            "read an explicit pinned catalog and regenerate the compact manifest; "
            "the source file is never modified"
        ),
    )
    args = parser.parse_args(argv)

    if args.source_catalog is None:
        manifest = load_manifest()
        generated = outputs(manifest)
    else:
        manifest = manifest_from_catalog(args.source_catalog)
        generated = outputs(manifest, include_manifest=True)

    if args.check:
        stale = [
            path
            for path, content in generated.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            for path in stale:
                print(f"stale: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("colour/forward-film census: tracked outputs are current")
        return 0

    for path, content in generated.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
