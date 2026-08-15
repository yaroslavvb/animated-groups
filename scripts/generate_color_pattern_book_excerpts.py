#!/usr/bin/env python3
"""Generate annotated book excerpts for the colour-pattern catalog."""

from __future__ import annotations

import argparse
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from color_pattern_book_excerpt_specs import OUTPUT_DIR, build_excerpt_specs
from generate_color_pattern_catalog import build_payload


ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = ROOT / "tmp" / "pdfs"
RENDER_DPI = 216
WATERMARK = "© COPYRIGHTED EXCERPT"
SOURCE_SIZE = {"sot": (612.0, 792.0), "gs": (545.0, 646.0)}


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        Path(
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def _render_pages(source_pdf: Path, pages: set[int], directory: Path, prefix: str) -> dict[int, Image.Image]:
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm (Poppler) is required")
    rendered: dict[int, Image.Image] = {}
    for page_number in sorted(pages):
        output = directory / f"{prefix}-{page_number}"
        subprocess.run(
            [
                "pdftoppm", "-f", str(page_number), "-l", str(page_number),
                "-singlefile", "-r", str(RENDER_DPI), "-png",
                str(source_pdf), str(output),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        with Image.open(output.with_suffix(".png")) as image:
            rendered[page_number] = image.convert("RGB")
    return rendered


def _box(
    rect: tuple[float, float, float, float],
    page: Image.Image,
    source_size: tuple[float, float],
) -> tuple[int, int, int, int]:
    x, y, width, height = rect
    sx = page.width / source_size[0]
    sy = page.height / source_size[1]
    return (
        round(x * sx),
        round(y * sy),
        round((x + width) * sx),
        round((y + height) * sy),
    )


def _watermark(size: tuple[int, int]) -> Image.Image:
    width, height = size
    font_size = max(12, min(38, round(width / 12), round(height / 8)))
    font = _font(font_size, bold=True)
    bounds = font.getbbox(WATERMARK)
    label = Image.new(
        "RGBA",
        (bounds[2] - bounds[0] + 28, bounds[3] - bounds[1] + 22),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(label)
    draw.text(
        ((label.width - (bounds[2] - bounds[0])) / 2, (label.height - (bounds[3] - bounds[1])) / 2 - bounds[1]),
        WATERMARK,
        font=font,
        fill=(120, 37, 27, 28),
    )
    label = label.rotate(18, resample=Image.Resampling.BICUBIC, expand=True)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.alpha_composite(label, ((width - label.width) // 2, (height - label.height) // 2))
    return layer


def _single_content(
    page: Image.Image,
    spec: dict[str, Any],
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    source_size = SOURCE_SIZE[spec["kind"]]
    crop_box = _box(spec["crop"], page, source_size)
    content = page.crop(crop_box).convert("RGBA")
    highlight = _box(spec["highlight"], page, source_size)
    local = (
        highlight[0] - crop_box[0],
        highlight[1] - crop_box[1],
        highlight[2] - crop_box[0],
        highlight[3] - crop_box[1],
    )
    content.alpha_composite(_watermark(content.size))
    return content, local


def _table_content(
    pages: dict[int, Image.Image],
    spec: dict[str, Any],
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    source_size = SOURCE_SIZE[spec["kind"]]
    panels: list[tuple[dict[str, Any], Image.Image, tuple[int, int, int, int]]] = []
    for panel in spec["table_panels"]:
        page = pages[panel["pdf_page"]]
        crop_box = _box(panel["crop"], page, source_size)
        panel_image = page.crop(crop_box).convert("RGBA")
        panel_image.alpha_composite(_watermark(panel_image.size))
        panels.append((panel, panel_image, crop_box))

    gap = 18
    width = max(image.width for _, image, _ in panels)
    height = sum(image.height for _, image, _ in panels) + gap * (len(panels) - 1)
    content = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    local: tuple[int, int, int, int] | None = None
    y_offset = 0
    for panel, image, crop_box in panels:
        x_offset = (width - image.width) // 2
        content.alpha_composite(image, (x_offset, y_offset))
        if panel["pdf_page"] == spec["pdf_page"]:
            source_page = pages[panel["pdf_page"]]
            highlight = _box(spec["highlight"], source_page, source_size)
            local = (
                x_offset + highlight[0] - crop_box[0],
                y_offset + highlight[1] - crop_box[1],
                x_offset + highlight[2] - crop_box[0],
                y_offset + highlight[3] - crop_box[1],
            )
        y_offset += image.height + gap
    if local is None:
        raise ValueError(f"highlight page is absent from table panels: {spec}")
    return content, local


def render_excerpt(
    pages: dict[int, Image.Image],
    spec: dict[str, Any],
) -> bytes:
    if spec.get("table_panels"):
        content, highlight = _table_content(pages, spec)
    else:
        content, highlight = _single_content(pages[spec["pdf_page"]], spec)

    overlay = Image.new("RGBA", content.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(
        highlight,
        radius=8,
        fill=(245, 176, 42, 36),
        outline=(181, 56, 36, 238),
        width=5,
    )
    content = Image.alpha_composite(content, overlay)

    padding = 12
    footer_height = 50
    framed = Image.new(
        "RGBA",
        (content.width + 2 * padding, content.height + 2 * padding + footer_height),
        (248, 246, 240, 255),
    )
    framed.alpha_composite(content, (padding, padding))
    framed_draw = ImageDraw.Draw(framed)
    framed_draw.rectangle(
        (padding - 1, padding - 1, padding + content.width, padding + content.height),
        outline=(92, 88, 78, 150),
        width=2,
    )
    divider_y = 2 * padding + content.height + 3
    framed_draw.line(
        (padding, divider_y, framed.width - padding, divider_y),
        fill=(92, 88, 78, 95),
        width=1,
    )
    label = f"{spec['footer']}  ·  PRINTED P. {spec['printed_page']}  ·  ANNOTATED"
    label_size = 17
    label_font = _font(label_size, bold=True)
    while label_size > 10 and label_font.getlength(label) > framed.width - 2 * padding:
        label_size -= 1
        label_font = _font(label_size, bold=True)
    framed_draw.text((padding, divider_y + 12), label, font=label_font, fill=(59, 61, 57, 235))

    buffer = io.BytesIO()
    framed.convert("RGB").save(buffer, format="WEBP", lossless=True, method=6)
    return buffer.getvalue()


def expected_assets(sot_pdf: Path, gs_pdf: Path) -> dict[Path, bytes]:
    specs = build_excerpt_specs(build_payload())
    sot_pages = {
        panel["pdf_page"]
        for spec in specs.values()
        if spec["kind"] == "sot"
        for panel in spec["table_panels"]
    }
    gs_pages = {spec["pdf_page"] for spec in specs.values() if spec["kind"] == "gs"}
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="colour-pattern-excerpts-", dir=TEMP_ROOT) as temporary:
        directory = Path(temporary)
        pages = {
            "sot": _render_pages(sot_pdf, sot_pages, directory, "sot"),
            "gs": _render_pages(gs_pdf, gs_pages, directory, "gs"),
        }
        return {
            ROOT / image_path: render_excerpt(pages[spec["kind"]], spec)
            for image_path, spec in specs.items()
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sot-pdf", type=Path, required=True)
    parser.add_argument("--gs-pdf", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    sot_pdf = args.sot_pdf.expanduser().resolve()
    gs_pdf = args.gs_pdf.expanduser().resolve()
    for path in (sot_pdf, gs_pdf):
        if not path.is_file():
            parser.error(f"source PDF does not exist: {path}")

    assets = expected_assets(sot_pdf, gs_pdf)
    if args.check:
        stale = [path for path, expected in assets.items() if not path.is_file() or path.read_bytes() != expected]
        for path in stale:
            print(path.relative_to(ROOT))
        if stale:
            return 1
        print(f"All {len(assets)} colour-pattern excerpt assets are current.")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    expected_paths = set(assets)
    for stale in OUTPUT_DIR.glob("*.webp"):
        if stale not in expected_paths:
            stale.unlink()
    for path, contents in assets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    print(f"Wrote {len(assets)} colour-pattern excerpt assets to {OUTPUT_DIR.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
