#!/usr/bin/env python3
"""Render two additional motif families for every showcased symmetry."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from animated_groups.catalog.motif_variants import render_catalog_variant_gallery
from animated_groups.motif_variants import render_legacy_variant_gallery
from animated_groups.rendering import write_audit_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render discs and bars variants for all eleven symmetry types."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/motif_variants"))
    parser.add_argument("--target-frames", type=int, default=60)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--size", type=int, default=420)
    parser.add_argument("--supersample", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    legacy = render_legacy_variant_gallery(
        args.output_dir,
        target_frames=args.target_frames,
        fps=args.fps,
        size=args.size,
        supersample=args.supersample,
    )
    catalog = render_catalog_variant_gallery(
        args.output_dir,
        target_frames=args.target_frames,
        fps=args.fps,
        size=args.size,
        supersample=args.supersample,
    )
    audits = (*legacy, *catalog)
    report = write_audit_report(audits, args.output_dir / "loop_report.json")
    for audit in audits:
        status = "PASS" if audit.passes else "FAIL"
        print(
            f"{status} {audit.path}: {audit.frame_count} frames, "
            f"loop={audit.loop}, seam ratio={audit.seam_ratio:.3f}"
        )
        for check in audit.checks:
            print(f"  - {check}")
    print(f"Wrote {report}")
    return 0 if all(audit.passes for audit in audits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
