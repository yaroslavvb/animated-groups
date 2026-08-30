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
SOURCE_SIZE = {"sot": (612.0, 792.0), "gs": (547.0, 646.0)}
INK_THRESHOLD = 118
INK_PADDING_POINTS = 4.5
HORIZONTAL_RULE_DENSITY = 0.70
INK_LINE_GAP_POINTS = 1.5


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
) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    source_size = SOURCE_SIZE[spec["kind"]]
    crop_box = _box(spec["crop"], page, source_size)
    if spec.get("highlight_probes"):
        highlights = [
            _detected_ink_box(page, probe, source_size)
            for probe in spec["highlight_probes"]
        ]
    else:
        highlights = [_box(spec["highlight"], page, source_size)]
    crop_box = _fit_crop_to_highlights(crop_box, highlights, page)
    content = page.crop(crop_box).convert("RGBA")
    local = [
        (
            highlight[0] - crop_box[0],
            highlight[1] - crop_box[1],
            highlight[2] - crop_box[0],
            highlight[3] - crop_box[1],
        )
        for highlight in highlights
    ]
    content.alpha_composite(_watermark(content.size))
    return content, local


def _detected_ink_box(
    page: Image.Image,
    probe: tuple[float, float, float, float],
    source_size: tuple[float, float],
) -> tuple[int, int, int, int]:
    """Tighten an approximate label region to its printed dark ink."""

    probe_box = _box(probe, page, source_size)

    def ink_inside(box: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
        sample = page.crop(box).convert("L")
        return sample.point(lambda value: 255 if value < 118 else 0).getbbox()

    ink = ink_inside(probe_box)
    if ink is None:
        # Several Chapter 8 plates shift the PP caption about 45 pt farther
        # right than the otherwise regular grid.  Expand only an empty probe;
        # this preserves the tight split on crowded rows such as pp. 429–430.
        x, y, width, height = probe
        extra_right = 50.0 if width < 80.0 else 8.0
        fallback = (
            max(0.0, x - 4.0),
            max(0.0, y - 8.0),
            min(source_size[0] - max(0.0, x - 4.0), width + extra_right),
            min(source_size[1] - max(0.0, y - 8.0), height + 16.0),
        )
        probe_box = _box(fallback, page, source_size)
        ink = ink_inside(probe_box)
    if ink is None:
        raise ValueError(f"no printed label ink found in probe {probe}")
    sx = page.width / source_size[0]
    sy = page.height / source_size[1]
    pad_x = round(INK_PADDING_POINTS * sx)
    pad_y = round(INK_PADDING_POINTS * sy)
    return (
        max(0, probe_box[0] + ink[0] - pad_x),
        max(0, probe_box[1] + ink[1] - pad_y),
        min(page.width, probe_box[0] + ink[2] + pad_x),
        min(page.height, probe_box[1] + ink[3] + pad_y),
    )


def _detected_table_ink_box(
    page: Image.Image,
    probe: tuple[float, float, float, float],
    source_size: tuple[float, float],
) -> tuple[int, int, int, int]:
    """Tighten one table-row probe to ink, rejecting ambiguous detections."""

    probe_box = _box(probe, page, source_size)
    left, top, right, bottom = probe_box
    if (
        left < 0
        or top < 0
        or right > page.width
        or bottom > page.height
        or left >= right
        or top >= bottom
    ):
        raise ValueError(f"table highlight probe leaves the source page: {probe}")

    mask = page.crop(probe_box).convert("L").point(
        lambda value: 255 if value < INK_THRESHOLD else 0
    )
    width, height = mask.size
    pixels = mask.load()
    rule_cutoff = max(1, round(width * HORIZONTAL_RULE_DENSITY))
    rule_rows = [
        row
        for row in range(height)
        if sum(bool(pixels[column, row]) for column in range(width)) >= rule_cutoff
    ]
    if rule_rows:
        draw = ImageDraw.Draw(mask)
        for row in rule_rows:
            draw.line((0, row, width - 1, row), fill=0)

    pixels = mask.load()
    row_counts = [
        sum(bool(pixels[column, row]) for column in range(width))
        for row in range(height)
    ]
    occupied_rows = [row for row, count in enumerate(row_counts) if count]
    if not occupied_rows:
        raise ValueError(f"no notation ink found in table highlight probe {probe}")

    # A short signature is one printed line.  Bridging only tiny raster gaps
    # keeps disconnected superscripts with their bases while rejecting a
    # probe that also reaches the preceding or following table row.
    sy = page.height / source_size[1]
    max_gap = max(1, round(INK_LINE_GAP_POINTS * sy))
    line_clusters: list[list[int]] = [[occupied_rows[0]]]
    for row in occupied_rows[1:]:
        if row - line_clusters[-1][-1] > max_gap + 1:
            line_clusters.append([row])
        else:
            line_clusters[-1].append(row)
    if len(line_clusters) != 1:
        bounds = [(cluster[0], cluster[-1]) for cluster in line_clusters]
        raise ValueError(
            f"ambiguous table highlight probe {probe}: ink lines {bounds}"
        )

    ink = mask.getbbox()
    if ink is None:  # Defensive: occupied_rows already proves this cannot occur.
        raise ValueError(f"no notation ink found in table highlight probe {probe}")
    if ink[0] == 0 or ink[1] == 0 or ink[2] == width or ink[3] == height:
        raise ValueError(
            f"table highlight probe clips notation ink at its edge: {probe}; "
            f"detected {ink} within {(width, height)}"
        )

    sx = page.width / source_size[0]
    pad_x = round(INK_PADDING_POINTS * sx)
    pad_y = round(INK_PADDING_POINTS * sy)
    highlight = (
        left + ink[0] - pad_x,
        top + ink[1] - pad_y,
        left + ink[2] + pad_x,
        top + ink[3] + pad_y,
    )
    if (
        highlight[0] < 0
        or highlight[1] < 0
        or highlight[2] > page.width
        or highlight[3] > page.height
    ):
        raise ValueError(
            f"padded table highlight leaves the source page: {probe} -> {highlight}"
        )
    return highlight


def _fit_crop_to_highlights(
    crop: tuple[int, int, int, int],
    highlights: list[tuple[int, int, int, int]],
    page: Image.Image,
) -> tuple[int, int, int, int]:
    """Keep every outline fully inside the excerpt with visible clearance."""

    margin = round(12 * page.width / SOURCE_SIZE["gs"][0])
    left, top, right, bottom = crop
    left = max(0, min(left, min(box[0] for box in highlights) - margin))
    top = max(0, min(top, min(box[1] for box in highlights) - margin))
    right = min(page.width, max(right, max(box[2] for box in highlights) + margin))
    bottom = min(page.height, max(bottom, max(box[3] for box in highlights) + margin))
    return left, top, right, bottom


def _table_content(
    pages: dict[int, Image.Image],
    spec: dict[str, Any],
) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
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
            if spec["kind"] == "sot":
                probe = spec.get("highlight_probe")
                blank_short_signature = spec.get("blank_short_signature", False)
                if bool(probe) == bool(blank_short_signature):
                    raise ValueError(
                        "SOT table excerpts need exactly one of highlight_probe "
                        "or blank_short_signature"
                    )
                if blank_short_signature:
                    if "highlight" not in spec:
                        raise ValueError(
                            "a blank SOT short-signature cell needs a fixed highlight"
                        )
                    highlight = _box(spec["highlight"], source_page, source_size)
                else:
                    if "highlight" in spec:
                        raise ValueError(
                            "detected SOT table excerpts must not carry a fixed highlight"
                        )
                    highlight = _detected_table_ink_box(
                        source_page,
                        probe,
                        source_size,
                    )
            else:
                highlight = _box(spec["highlight"], source_page, source_size)
            if (
                highlight[0] < crop_box[0]
                or highlight[1] < crop_box[1]
                or highlight[2] > crop_box[2]
                or highlight[3] > crop_box[3]
            ):
                raise ValueError(
                    f"table highlight lies outside its panel crop: {highlight} "
                    f"not within {crop_box}"
                )
            local = (
                x_offset + highlight[0] - crop_box[0],
                y_offset + highlight[1] - crop_box[1],
                x_offset + highlight[2] - crop_box[0],
                y_offset + highlight[3] - crop_box[1],
            )
        y_offset += image.height + gap
    if local is None:
        raise ValueError(f"highlight page is absent from table panels: {spec}")
    return content, [local]


def render_excerpt(
    pages: dict[int, Image.Image],
    spec: dict[str, Any],
) -> bytes:
    if spec.get("table_panels"):
        content, highlights = _table_content(pages, spec)
    else:
        content, highlights = _single_content(pages[spec["pdf_page"]], spec)

    overlay = Image.new("RGBA", content.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for highlight in highlights:
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


def expected_assets(
    sot_pdf: Path | None,
    gs_pdf: Path | None,
    *,
    kind: str = "all",
) -> dict[Path, bytes]:
    if kind not in {"all", "sot", "gs"}:
        raise ValueError(f"unsupported excerpt kind: {kind}")
    selected_kinds = {"sot", "gs"} if kind == "all" else {kind}
    specs = {
        path: spec
        for path, spec in build_excerpt_specs(build_payload()).items()
        if spec["kind"] in selected_kinds
    }
    source_pdfs = {"sot": sot_pdf, "gs": gs_pdf}
    missing = sorted(
        source_kind
        for source_kind in selected_kinds
        if source_pdfs[source_kind] is None
    )
    if missing:
        raise ValueError(f"missing source PDF for excerpt kind(s): {', '.join(missing)}")

    page_numbers: dict[str, set[int]] = {}
    if "sot" in selected_kinds:
        page_numbers["sot"] = {
            panel["pdf_page"]
            for spec in specs.values()
            if spec["kind"] == "sot"
            for panel in spec["table_panels"]
        }
    if "gs" in selected_kinds:
        page_numbers["gs"] = {
            spec["pdf_page"]
            for spec in specs.values()
            if spec["kind"] == "gs"
        }

    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="colour-pattern-excerpts-", dir=TEMP_ROOT) as temporary:
        directory = Path(temporary)
        pages: dict[str, dict[int, Image.Image]] = {}
        for source_kind in sorted(selected_kinds):
            source_pdf = source_pdfs[source_kind]
            if source_pdf is None:  # Covered by the missing-source check above.
                raise ValueError(f"missing source PDF for excerpt kind: {source_kind}")
            pages[source_kind] = _render_pages(
                source_pdf,
                page_numbers[source_kind],
                directory,
                source_kind,
            )
        return {
            ROOT / image_path: render_excerpt(pages[spec["kind"]], spec)
            for image_path, spec in specs.items()
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("all", "sot", "gs"), default="all")
    parser.add_argument("--sot-pdf", type=Path)
    parser.add_argument("--gs-pdf", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    selected_kinds = {"sot", "gs"} if args.kind == "all" else {args.kind}
    supplied_pdfs = {"sot": args.sot_pdf, "gs": args.gs_pdf}
    for source_kind in sorted(selected_kinds):
        if supplied_pdfs[source_kind] is None:
            parser.error(f"--{source_kind}-pdf is required for --kind {args.kind}")
    resolved_pdfs = {
        source_kind: path.expanduser().resolve() if path is not None else None
        for source_kind, path in supplied_pdfs.items()
    }
    for path in resolved_pdfs.values():
        if path is None:
            continue
        if not path.is_file():
            parser.error(f"source PDF does not exist: {path}")

    assets = expected_assets(
        resolved_pdfs["sot"],
        resolved_pdfs["gs"],
        kind=args.kind,
    )
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
    cleanup_glob = {
        "all": "*.webp",
        "sot": "tos-*.webp",
        "gs": "gs-*.webp",
    }[args.kind]
    removed = 0
    for stale in OUTPUT_DIR.glob(cleanup_glob):
        if stale not in expected_paths:
            stale.unlink()
            removed += 1
    changed = 0
    for path, contents in assets.items():
        if path.is_file() and path.read_bytes() == contents:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
        changed += 1
    unchanged = len(assets) - changed
    print(
        f"Selected {len(assets)} {args.kind} colour-pattern excerpt assets; "
        f"wrote {changed}, kept {unchanged} byte-identical, removed {removed} stale "
        f"asset(s) in {OUTPUT_DIR.relative_to(ROOT)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
