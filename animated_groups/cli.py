"""Command-line interface for rendering and checking the example GIFs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from .rendering import (
    GifAudit,
    audit_gif,
    gif_duration_ms,
    render_frames,
    save_looping_gif,
    write_audit_report,
)


DEFAULT_NAMES = {
    "time_glide": "time_glide_c2.gif",
    "time_screw": "time_screw_c4.gif",
    "diagonal_relay": "diagonal_relay_c3.gif",
    "mixed_time_glide": "mixed_time_glide.gif",
    "glide_time_reversal": "glide_time_reversal.gif",
    "rotary_time_reversal": "rotary_time_reversal_4prime.gif",
    "dihedral_choreography": "dihedral_choreography_d3.gif",
}


def generate_one(
    example: str,
    output: str | Path,
    *,
    frame_count: int,
    fps: int,
    size: int,
    screw_order: int = 4,
    relay_order: int = 3,
    supersample: int = 2,
) -> GifAudit:
    frames = render_frames(
        example,
        frame_count=frame_count,
        size=size,
        screw_order=screw_order,
        relay_order=relay_order,
        supersample=supersample,
    )
    path = save_looping_gif(frames, output, fps=fps)
    return audit_gif(
        path,
        expected_frames=frame_count,
        expected_duration_ms=gif_duration_ms(fps),
    )


def _add_render_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--frames", type=int, default=60, help="number of samples; endpoint t=1 is omitted")
    parser.add_argument("--fps", type=int, default=20, help="playback frames per second")
    parser.add_argument("--size", type=int, default=600, help="square GIF size in pixels")
    parser.add_argument("--supersample", type=int, default=2, help="internal anti-aliasing scale")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="animated-groups",
        description="Render exact colored spacetime-group state models as seamless GIFs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    all_parser = subparsers.add_parser("all", help="render the complete example catalog")
    _add_render_options(all_parser)
    all_parser.add_argument("--output-dir", type=Path, default=Path("output"))

    glide_parser = subparsers.add_parser("time-glide", help="render reflection + T/2")
    _add_render_options(glide_parser)
    glide_parser.add_argument("--output", type=Path, default=Path("output/time_glide_c2.gif"))

    screw_parser = subparsers.add_parser("time-screw", help="render rotation + T/n")
    _add_render_options(screw_parser)
    screw_parser.add_argument("--order", type=int, choices=(3, 4, 6), default=4)
    screw_parser.add_argument("--output", type=Path, default=None)

    relay_parser = subparsers.add_parser("diagonal-relay", help="render the non-product cell/time subgroup")
    _add_render_options(relay_parser)
    relay_parser.add_argument("--order", type=int, choices=range(2, 7), default=3)
    relay_parser.add_argument("--output", type=Path, default=None)

    mixed_parser = subparsers.add_parser(
        "mixed-time-glide",
        help="render reflection + half-y shift + T/2",
    )
    _add_render_options(mixed_parser)
    mixed_parser.add_argument("--output", type=Path, default=Path("output/mixed_time_glide.gif"))

    glide_tr_parser = subparsers.add_parser(
        "glide-time-reversal",
        help="render half-cell translation + playback reversal",
    )
    _add_render_options(glide_tr_parser)
    glide_tr_parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/glide_time_reversal.gif"),
    )

    rotary_tr_parser = subparsers.add_parser(
        "rotary-time-reversal",
        help="render the non-split tetragonal 4-prime example",
    )
    _add_render_options(rotary_tr_parser)
    rotary_tr_parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/rotary_time_reversal_4prime.gif"),
    )

    dihedral_parser = subparsers.add_parser(
        "dihedral-choreography",
        help="render the diagonal nonabelian D3 example",
    )
    _add_render_options(dihedral_parser)
    dihedral_parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/dihedral_choreography_d3.gif"),
    )

    verify_parser = subparsers.add_parser("verify", help="audit saved GIF loop metadata and seam")
    verify_parser.add_argument("paths", type=Path, nargs="+")
    verify_parser.add_argument("--frames", type=int, default=60, help="expected decoded frame count")
    verify_parser.add_argument("--report", type=Path, default=None)
    return parser


def _print_audit(audit: GifAudit) -> None:
    status = "PASS" if audit.passes else "FAIL"
    duration = audit.durations_ms[0] if audit.durations_ms else 0
    print(
        f"{status} {audit.path}: {audit.frame_count} frames, loop={audit.loop}, "
        f"duration={duration} ms ({audit.effective_fps:.3g} fps), "
        f"seam ratio={audit.seam_ratio:.3f}"
    )
    for check in audit.checks:
        print(f"  - {check}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    audits: list[GifAudit] = []

    render_commands = {
        "all",
        "time-glide",
        "time-screw",
        "diagonal-relay",
        "mixed-time-glide",
        "glide-time-reversal",
        "rotary-time-reversal",
        "dihedral-choreography",
    }
    if args.command in render_commands:
        try:
            gif_duration_ms(args.fps)
        except ValueError as error:
            parser.error(str(error))
        if args.size < 240:
            parser.error("--size must be at least 240")
        if args.supersample < 1:
            parser.error("--supersample must be at least 1")

        if args.command == "all":
            # lcm(2, 3, 4) = 12.  Validate before writing the first file so an
            # invalid shared setting cannot leave a partial output directory.
            if args.frames < 12 or args.frames % 12:
                parser.error("--frames for 'all' must be at least 12 and divisible by 12")
            if args.size % 6:
                parser.error("--size for 'all' must be divisible by 6 for the periodic scenes")
        else:
            fixed_orders = {
                "time-glide": 2,
                "mixed-time-glide": 2,
                "glide-time-reversal": 2,
                "rotary-time-reversal": 4,
                "dihedral-choreography": 3,
            }
            order = fixed_orders[args.command] if args.command in fixed_orders else args.order
            if args.frames < 2 * order or args.frames % order:
                parser.error(
                    f"--frames must be at least {2 * order} and divisible by sampling order {order}"
                )
            if args.command == "diagonal-relay" and args.size % args.order:
                parser.error(f"--size must be divisible by relay order {args.order}")
            if args.command in {"mixed-time-glide", "glide-time-reversal"} and args.size % 2:
                parser.error("--size must be even for a half-cell periodic translation")

    if args.command == "all":
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for example, name in DEFAULT_NAMES.items():
            audit = generate_one(
                example,
                args.output_dir / name,
                frame_count=args.frames,
                fps=args.fps,
                size=args.size,
                supersample=args.supersample,
            )
            audits.append(audit)
            _print_audit(audit)
        report = write_audit_report(audits, args.output_dir / "loop_report.json")
        print(f"Wrote {report}")
    elif args.command == "time-glide":
        audit = generate_one(
            "time_glide",
            args.output,
            frame_count=args.frames,
            fps=args.fps,
            size=args.size,
            supersample=args.supersample,
        )
        audits.append(audit)
        _print_audit(audit)
    elif args.command == "time-screw":
        output = args.output or Path(f"output/time_screw_c{args.order}.gif")
        audit = generate_one(
            "time_screw",
            output,
            frame_count=args.frames,
            fps=args.fps,
            size=args.size,
            screw_order=args.order,
            supersample=args.supersample,
        )
        audits.append(audit)
        _print_audit(audit)
    elif args.command == "diagonal-relay":
        output = args.output or Path(f"output/diagonal_relay_c{args.order}.gif")
        audit = generate_one(
            "diagonal_relay",
            output,
            frame_count=args.frames,
            fps=args.fps,
            size=args.size,
            relay_order=args.order,
            supersample=args.supersample,
        )
        audits.append(audit)
        _print_audit(audit)
    elif args.command == "mixed-time-glide":
        audit = generate_one(
            "mixed_time_glide",
            args.output,
            frame_count=args.frames,
            fps=args.fps,
            size=args.size,
            supersample=args.supersample,
        )
        audits.append(audit)
        _print_audit(audit)
    elif args.command == "glide-time-reversal":
        audit = generate_one(
            "glide_time_reversal",
            args.output,
            frame_count=args.frames,
            fps=args.fps,
            size=args.size,
            supersample=args.supersample,
        )
        audits.append(audit)
        _print_audit(audit)
    elif args.command == "rotary-time-reversal":
        audit = generate_one(
            "rotary_time_reversal",
            args.output,
            frame_count=args.frames,
            fps=args.fps,
            size=args.size,
            supersample=args.supersample,
        )
        audits.append(audit)
        _print_audit(audit)
    elif args.command == "dihedral-choreography":
        audit = generate_one(
            "dihedral_choreography",
            args.output,
            frame_count=args.frames,
            fps=args.fps,
            size=args.size,
            supersample=args.supersample,
        )
        audits.append(audit)
        _print_audit(audit)
    elif args.command == "verify":
        if args.frames < 2:
            parser.error("--frames must be at least 2")
        audits = [audit_gif(path, expected_frames=args.frames) for path in args.paths]
        for audit in audits:
            _print_audit(audit)
        if args.report:
            report = write_audit_report(audits, args.report)
            print(f"Wrote {report}")

    return 0 if all(audit.passes for audit in audits) else 1


if __name__ == "__main__":
    sys.exit(main())
