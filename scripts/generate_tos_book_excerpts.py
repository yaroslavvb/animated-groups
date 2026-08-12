#!/usr/bin/env python3
"""Generate the annotated *Symmetries of Things* excerpt assets.

The source PDF is intentionally not part of the site.  This script renders
only the 65 evidence images listed in
``tos_book_excerpt_specs.py``, bakes in the highlight and copyright notice,
and writes lossless WebP files for the separate excerpt viewer. Table evidence
shows the complete table, including every continuation page.
"""

from __future__ import annotations

import argparse
import io
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from tos_book_excerpt_specs import BOOK_EXCERPTS


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "book-excerpts"
TEMP_ROOT = ROOT / "tmp" / "pdfs"
RENDER_DPI = 216
PDF_WIDTH = 612.0
PDF_HEIGHT = 792.0
WATERMARK = "© COPYRIGHTED EXCERPT"
CONTEXT_AREA_MULTIPLIER = 5.25
VERTICAL_CONTEXT_MULTIPLIER = 5.0


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
             "/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def _render_pages(source_pdf: Path, directory: Path) -> dict[int, Image.Image]:
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm (Poppler) is required to render the source PDF")
    pages: dict[int, Image.Image] = {}
    for pdf_page in sorted({spec["pdf_page"] for spec in BOOK_EXCERPTS.values()}):
        prefix = directory / f"page-{pdf_page}"
        subprocess.run(
            [
                "pdftoppm", "-f", str(pdf_page), "-l", str(pdf_page),
                "-singlefile", "-r", str(RENDER_DPI), "-png",
                str(source_pdf), str(prefix),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        path = prefix.with_suffix(".png")
        with Image.open(path) as rendered:
            pages[pdf_page] = rendered.convert("RGB")
    return pages


def _box(rect: tuple[float, float, float, float], sx: float, sy: float) -> tuple[int, int, int, int]:
    x, y, width, height = rect
    return (
        round(x * sx),
        round(y * sy),
        round((x + width) * sx),
        round((y + height) * sy),
    )


def area_context_crop(
    rect: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Expand a focus crop beyond five times its area without leaving the page."""

    x, y, width, height = rect
    if width <= 0 or height <= 0:
        raise ValueError(f"crop must have positive dimensions: {rect}")
    target_area = width * height * CONTEXT_AREA_MULTIPLIER
    if target_area > PDF_WIDTH * PDF_HEIGHT:
        raise ValueError(f"fivefold crop does not fit on the source page: {rect}")
    aspect_ratio = width / height
    expanded_width = math.sqrt(target_area * aspect_ratio)
    expanded_height = target_area / expanded_width

    if expanded_width > PDF_WIDTH:
        expanded_width = PDF_WIDTH
        expanded_height = target_area / expanded_width
    if expanded_height > PDF_HEIGHT:
        expanded_height = PDF_HEIGHT
        expanded_width = target_area / expanded_height

    center_x = x + width / 2
    center_y = y + height / 2
    expanded_x = min(
        max(0.0, center_x - expanded_width / 2),
        PDF_WIDTH - expanded_width,
    )
    expanded_y = min(
        max(0.0, center_y - expanded_height / 2),
        PDF_HEIGHT - expanded_height,
    )
    return expanded_x, expanded_y, expanded_width, expanded_height


def expanded_crop(
    rect: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Make the established context five times taller, bounded by the page."""

    x, y, width, height = area_context_crop(rect)
    expanded_height = min(PDF_HEIGHT, height * VERTICAL_CONTEXT_MULTIPLIER)
    center_y = y + height / 2
    expanded_y = min(
        max(0.0, center_y - expanded_height / 2),
        PDF_HEIGHT - expanded_height,
    )
    return x, expanded_y, width, expanded_height


def _watermark_layer(size: tuple[int, int]) -> Image.Image:
    width, height = size
    font_size = max(12, min(46, round(width / 15), round(height * 0.38)))
    font = _font(font_size, bold=True)
    bbox = font.getbbox(WATERMARK)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    label = Image.new("RGBA", (text_width + 30, text_height + 24), (0, 0, 0, 0))
    label_draw = ImageDraw.Draw(label)
    label_draw.text(
        ((label.width - text_width) / 2, (label.height - text_height) / 2 - bbox[1]),
        WATERMARK,
        font=font,
        fill=(120, 37, 27, 30),
    )
    label = label.rotate(18, resample=Image.Resampling.BICUBIC, expand=True)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (width - label.width) // 2
    y = (height - label.height) // 2
    layer.alpha_composite(label, (x, y))
    return layer


def _render_content(
    pages: dict[int, Image.Image],
    spec: dict[str, Any],
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Render either complete table panels or one contextual prose crop."""

    panels = spec.get("table_panels")
    if not panels:
        page = pages[spec["pdf_page"]]
        sx = page.width / PDF_WIDTH
        sy = page.height / PDF_HEIGHT
        crop_box = _box(expanded_crop(spec["crop"]), sx, sy)
        excerpt = page.crop(crop_box).convert("RGBA")
        highlight = _box(spec["highlight"], sx, sy)
        local = (
            highlight[0] - crop_box[0],
            highlight[1] - crop_box[1],
            highlight[2] - crop_box[0],
            highlight[3] - crop_box[1],
        )
        excerpt.alpha_composite(_watermark_layer(excerpt.size))
        return excerpt, local

    rendered_panels: list[tuple[dict[str, Any], Image.Image, tuple[int, int, int, int]]] = []
    for panel in panels:
        page = pages[panel["pdf_page"]]
        sx = page.width / PDF_WIDTH
        sy = page.height / PDF_HEIGHT
        crop_box = _box(panel["crop"], sx, sy)
        panel_image = page.crop(crop_box).convert("RGBA")
        panel_image.alpha_composite(_watermark_layer(panel_image.size))
        rendered_panels.append((panel, panel_image, crop_box))

    gap = 18
    content_width = max(image.width for _, image, _ in rendered_panels)
    content_height = sum(image.height for _, image, _ in rendered_panels)
    content_height += gap * (len(rendered_panels) - 1)
    excerpt = Image.new("RGBA", (content_width, content_height), (255, 255, 255, 255))

    highlight_local: tuple[int, int, int, int] | None = None
    highlight_area = math.inf
    y_offset = 0
    for panel, panel_image, crop_box in rendered_panels:
        x_offset = (content_width - panel_image.width) // 2
        excerpt.alpha_composite(panel_image, (x_offset, y_offset))
        if panel["pdf_page"] == spec["pdf_page"]:
            page = pages[panel["pdf_page"]]
            sx = page.width / PDF_WIDTH
            sy = page.height / PDF_HEIGHT
            highlight = _box(spec["highlight"], sx, sy)
            local = (
                x_offset + highlight[0] - crop_box[0],
                y_offset + highlight[1] - crop_box[1],
                x_offset + highlight[2] - crop_box[0],
                y_offset + highlight[3] - crop_box[1],
            )
            clipped_width = max(
                0,
                min(local[2], x_offset + panel_image.width) - max(local[0], x_offset),
            )
            clipped_height = max(
                0,
                min(local[3], y_offset + panel_image.height) - max(local[1], y_offset),
            )
            if clipped_width * clipped_height < highlight_area:
                highlight_area = clipped_width * clipped_height
                highlight_local = local
        y_offset += panel_image.height + gap

    if highlight_local is None:
        raise ValueError(f"highlight page is absent from table panels: {spec['key']}")
    return excerpt, highlight_local


def render_excerpt(pages: dict[int, Image.Image], spec: dict[str, Any]) -> bytes:
    excerpt, local = _render_content(pages, spec)

    overlay = Image.new("RGBA", excerpt.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    radius = 9
    outline_width = 5
    draw.rounded_rectangle(
        local,
        radius=radius,
        fill=(245, 176, 42, 34),
        outline=(181, 56, 36, 235),
        width=outline_width,
    )
    excerpt = Image.alpha_composite(excerpt, overlay)

    padding = 12
    footer_height = 54
    framed = Image.new(
        "RGBA",
        (excerpt.width + padding * 2, excerpt.height + padding * 2 + footer_height),
        (248, 246, 240, 255),
    )
    framed.alpha_composite(excerpt, (padding, padding))
    framed_draw = ImageDraw.Draw(framed)
    framed_draw.rectangle(
        (padding - 1, padding - 1, padding + excerpt.width, padding + excerpt.height),
        outline=(92, 88, 78, 150),
        width=2,
    )
    divider_y = padding * 2 + excerpt.height + 4
    framed_draw.line((padding, divider_y, framed.width - padding, divider_y), fill=(92, 88, 78, 95), width=1)
    if spec.get("table_panels"):
        printed_pages = [panel["printed_page"] for panel in spec["table_panels"]]
        page_label = (
            f"PRINTED P. {printed_pages[0]}"
            if len(printed_pages) == 1
            else f"PRINTED PP. {printed_pages[0]}-{printed_pages[-1]}"
        )
        label = (
            "THE SYMMETRIES OF THINGS  ·  "
            f"{spec['table_name'].upper()}  ·  {page_label}  ·  ANNOTATED"
        )
    else:
        label = (
            "THE SYMMETRIES OF THINGS  ·  "
            f"PRINTED P. {spec['printed_page']}  ·  ANNOTATED EXCERPT"
        )
    label_size = 18
    label_font = _font(label_size, bold=True)
    while label_size > 11 and label_font.getlength(label) > framed.width - padding * 2:
        label_size -= 1
        label_font = _font(label_size, bold=True)
    framed_draw.text(
        (padding, divider_y + 13),
        label,
        font=label_font,
        fill=(59, 61, 57, 235),
    )

    buffer = io.BytesIO()
    framed.convert("RGB").save(buffer, format="WEBP", lossless=True, method=6)
    return buffer.getvalue()


def expected_assets(source_pdf: Path) -> dict[Path, bytes]:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tos-excerpts-", dir=TEMP_ROOT) as temporary:
        pages = _render_pages(source_pdf, Path(temporary))
        return {
            ROOT / spec["image"]: render_excerpt(pages, spec)
            for spec in BOOK_EXCERPTS.values()
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source_pdf = args.source_pdf.expanduser().resolve()
    if not source_pdf.is_file():
        parser.error(f"source PDF does not exist: {source_pdf}")

    assets = expected_assets(source_pdf)
    if args.check:
        stale = [path for path, expected in assets.items() if not path.is_file() or path.read_bytes() != expected]
        if stale:
            for path in stale:
                print(path.relative_to(ROOT))
            return 1
        print(f"All {len(assets)} annotated excerpt assets are current.")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, contents in assets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    print(f"Wrote {len(assets)} annotated excerpt assets to {OUTPUT_DIR.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
