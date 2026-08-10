"""Command-line orchestration for the systematic catalog and GIF gallery."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Sequence

from .enumerate import build_catalog
from .export import catalog_entry_to_dict, export_catalog
from .patterns import PATTERNS
from .render import compatible_frame_count, render_catalog_gallery
from .selection import select_pattern_entries


def write_representatives(
    catalog,
    output_dir: str | Path,
    *,
    target_frames: int,
    audits=(),
) -> Path:
    """Write the stable catalog-row-to-pattern bridge used by the gallery."""

    root = Path(output_dir)
    selected = select_pattern_entries(catalog)
    audits_by_name = {Path(audit.path).name: audit for audit in audits}
    rows = []
    for key, spec in PATTERNS.items():
        audit = audits_by_name.get(spec.filename)
        row = {
            "pattern": key,
            "title": spec.title,
            "gif": f"gifs/{spec.filename}",
            "phase_divisor": spec.phase_divisor,
            "frame_count": (
                audit.frame_count
                if audit is not None
                else compatible_frame_count(target_frames, spec.phase_divisor)
            ),
            "catalog_selector": spec.catalog_selector,
            "catalog_entry": catalog_entry_to_dict(selected[key]),
        }
        if audit is not None:
            row["loop_audit"] = asdict(audit)
        rows.append(row)

    payload = {
        "schema_version": catalog.schema_version,
        "catalog": "catalog.json",
        "representatives": rows,
    }
    output = root / "representatives.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def generate_systematic_catalog(
    output_dir: str | Path,
    *,
    min_modulus: int = 2,
    max_modulus: int = 12,
    target_frames: int = 60,
    fps: int = 20,
    size: int = 600,
    supersample: int = 2,
    render_gifs: bool = True,
):
    """Build all data products, then optionally render and audit the gallery."""

    if min_modulus < 2 or max_modulus < min_modulus:
        raise ValueError("phase modulus range must satisfy 2 <= minimum <= maximum")
    catalog = build_catalog(target_moduli=range(min_modulus, max_modulus + 1))
    paths = export_catalog(catalog, output_dir)
    audits = ()
    if render_gifs:
        audits = render_catalog_gallery(
            output_dir,
            target_frames=target_frames,
            fps=fps,
            size=size,
            supersample=supersample,
        )
        if not all(audit.passes for audit in audits):
            failed = [audit for audit in audits if not audit.passes]
            details = "; ".join(
                f"{Path(audit.path).name}: {', '.join(audit.checks)}" for audit in failed
            )
            raise RuntimeError(f"catalog GIF audit failed: {details}")
    paths["representatives"] = write_representatives(
        catalog,
        output_dir,
        target_frames=target_frames,
        audits=audits,
    )
    return catalog, paths, audits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate-catalog",
        description="Enumerate bounded phase actions and render the procedural GIF gallery.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/systematic_catalog"))
    parser.add_argument("--min-modulus", type=int, default=2)
    parser.add_argument("--max-modulus", type=int, default=12)
    parser.add_argument("--target-frames", type=int, default=60)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--size", type=int, default=600)
    parser.add_argument("--supersample", type=int, default=2)
    parser.add_argument("--catalog-only", action="store_true", help="skip GIF rendering")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        catalog, paths, audits = generate_systematic_catalog(
            args.output_dir,
            min_modulus=args.min_modulus,
            max_modulus=args.max_modulus,
            target_frames=args.target_frames,
            fps=args.fps,
            size=args.size,
            supersample=args.supersample,
            render_gifs=not args.catalog_only,
        )
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))

    print(
        f"Catalog: {len(catalog.entries)} normalized non-product actions "
        f"({len(catalog.finite_entries)} finite, "
        f"{len(catalog.translation_entries)} translations, "
        f"{len(catalog.reversible_relay_entries)} reversible relays)"
    )
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")
    for audit in audits:
        print(
            f"PASS {audit.path}: {audit.frame_count} frames, loop={audit.loop}, "
            f"seam ratio={audit.seam_ratio:.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "build_parser",
    "generate_systematic_catalog",
    "main",
    "write_representatives",
]
