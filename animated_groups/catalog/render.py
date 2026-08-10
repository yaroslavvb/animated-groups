"""Frame and GIF orchestration for the procedural catalog patterns."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image

from animated_groups.rendering import (
    GifAudit,
    audit_gif,
    gif_duration_ms,
    save_looping_gif,
    write_audit_report,
)

from .patterns import PATTERNS, render_pattern_image


def compatible_frame_count(target_frames: int, phase_divisor: int) -> int:
    """Round upward to a legal sample count, with two samples per phase step."""

    if target_frames < 1:
        raise ValueError("target frame count must be positive")
    if phase_divisor < 1:
        raise ValueError("phase divisor must be positive")
    minimum = 2 * phase_divisor
    target = max(target_frames, minimum)
    return math.ceil(target / phase_divisor) * phase_divisor


def render_pattern_frames(
    key: str,
    frame_count: int,
    size: int = 600,
    supersample: int = 2,
) -> list[Image.Image]:
    """Render periodic samples ``k/N`` without duplicating the endpoint."""

    try:
        spec = PATTERNS[key]
    except KeyError as error:
        choices = ", ".join(PATTERNS)
        raise ValueError(f"unknown catalog pattern {key!r}; choose from {choices}") from error
    if frame_count < 2 * spec.phase_divisor:
        raise ValueError(
            f"frame count must be at least twice the phase divisor "
            f"({2 * spec.phase_divisor})"
        )
    if frame_count % spec.phase_divisor:
        raise ValueError(
            f"frame count {frame_count} must be divisible by phase divisor "
            f"{spec.phase_divisor}"
        )
    return [
        render_pattern_image(
            key,
            frame / frame_count,
            size=size,
            supersample=supersample,
        )
        for frame in range(frame_count)
    ]


def render_catalog_gallery(
    output_dir: str | Path,
    target_frames: int = 60,
    fps: int = 20,
    size: int = 600,
    supersample: int = 2,
) -> tuple[GifAudit, ...]:
    """Render all four patterns and write a decoded-GIF loop audit report."""

    root = Path(output_dir)
    gif_dir = root / "gifs"
    expected_duration = gif_duration_ms(fps)
    audits: list[GifAudit] = []
    for key, spec in PATTERNS.items():
        frame_count = compatible_frame_count(target_frames, spec.phase_divisor)
        frames = render_pattern_frames(
            key,
            frame_count=frame_count,
            size=size,
            supersample=supersample,
        )
        gif_path = save_looping_gif(frames, gif_dir / spec.filename, fps=fps)
        audits.append(
            audit_gif(
                gif_path,
                expected_frames=frame_count,
                expected_duration_ms=expected_duration,
            )
        )
    write_audit_report(audits, root / "loop_report.json")
    return tuple(audits)


__all__ = [
    "compatible_frame_count",
    "render_pattern_frames",
    "render_catalog_gallery",
]
