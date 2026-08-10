"""Deterministic JSON, CSV, and Markdown exports for catalog data."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterable, Sequence

from .algebra import CircleIsometry
from .enumerate import Catalog, CatalogEntry, GeneratorImage


def _fraction_dict(action: CircleIsometry) -> dict[str, object]:
    return {
        "shift": {
            "numerator": action.shift.numerator,
            "denominator": action.shift.denominator,
        },
        "reverses": action.reverses,
    }


def generator_image_to_dict(image: GeneratorImage) -> dict[str, object]:
    return {
        "generator": image.generator,
        **_fraction_dict(image.action),
    }


def catalog_entry_to_dict(entry: CatalogEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "canonical_key": entry.canonical_key,
        "family": entry.family,
        "domain": entry.domain,
        "order": entry.order,
        "domain_size": entry.domain_size,
        "generator_images": [
            generator_image_to_dict(image) for image in entry.generator_images
        ],
        "target_phase_order": entry.target_phase_order,
        "reduced_phase_order": entry.reduced_phase_order,
        "phase_rotation_order": entry.phase_rotation_order,
        "image_order": entry.image_order,
        "kernel_elements": list(entry.kernel_elements),
        "kernel_order": entry.kernel_order,
        "graph_nonproduct": entry.graph_nonproduct,
        "extension_type": entry.extension_type,
        "time_reversing": entry.time_reversing,
        "frame_divisor": entry.frame_divisor,
        "tags": list(entry.tags),
        "realized_in_moduli": list(entry.realized_in_moduli),
        "translation_d4_orbit_key": entry.translation_d4_orbit_key,
        "quotient_projection_split": entry.quotient_projection_split,
        "product_lattice_cover_split": entry.product_lattice_cover_split,
    }


def catalog_to_dict(catalog: Catalog) -> dict[str, object]:
    return {
        "schema_version": catalog.schema_version,
        "scope": {
            "target_moduli": list(catalog.target_moduli),
            "finite_orders": list(catalog.finite_orders),
            "equivalence": "simultaneous target conjugacy only",
            "inflated_moduli": "merged by exact reduced generator images",
            "relay_extension_convention": (
                "extension_type refers to the product-lattice wallpaper cover; "
                "quotient_projection_split and product_lattice_cover_split "
                "record both levels explicitly"
            ),
        },
        "counts": {
            "total": len(catalog.entries),
            "finite": len(catalog.finite_entries),
            "translation": len(catalog.translation_entries),
            "reversible_relay": len(catalog.reversible_relay_entries),
        },
        "entries": [catalog_entry_to_dict(entry) for entry in catalog.entries],
    }


def write_catalog_json(catalog: Catalog, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(catalog_to_dict(catalog), indent=2, sort_keys=True) + "\n"
    output.write_text(payload, encoding="utf-8")
    return output


def _compact_images(images: Sequence[GeneratorImage]) -> str:
    return ";".join(image.token() for image in images)


def _optional_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


CSV_FIELDS = (
    "id",
    "canonical_key",
    "family",
    "domain",
    "order",
    "domain_size",
    "generator_images",
    "target_phase_order",
    "reduced_phase_order",
    "phase_rotation_order",
    "image_order",
    "kernel_elements",
    "kernel_order",
    "graph_nonproduct",
    "extension_type",
    "time_reversing",
    "frame_divisor",
    "tags",
    "realized_in_moduli",
    "translation_d4_orbit_key",
    "quotient_projection_split",
    "product_lattice_cover_split",
)


def _csv_row(entry: CatalogEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "canonical_key": entry.canonical_key,
        "family": entry.family,
        "domain": entry.domain,
        "order": "" if entry.order is None else entry.order,
        "domain_size": "" if entry.domain_size is None else entry.domain_size,
        "generator_images": _compact_images(entry.generator_images),
        "target_phase_order": entry.target_phase_order,
        "reduced_phase_order": entry.reduced_phase_order,
        "phase_rotation_order": entry.phase_rotation_order,
        "image_order": entry.image_order,
        "kernel_elements": ";".join(entry.kernel_elements),
        "kernel_order": "" if entry.kernel_order is None else entry.kernel_order,
        "graph_nonproduct": "true" if entry.graph_nonproduct else "false",
        "extension_type": entry.extension_type,
        "time_reversing": "true" if entry.time_reversing else "false",
        "frame_divisor": entry.frame_divisor,
        "tags": ";".join(entry.tags),
        "realized_in_moduli": ";".join(str(value) for value in entry.realized_in_moduli),
        "translation_d4_orbit_key": entry.translation_d4_orbit_key or "",
        "quotient_projection_split": _optional_bool(entry.quotient_projection_split),
        "product_lattice_cover_split": _optional_bool(entry.product_lattice_cover_split),
    }


def write_catalog_csv(catalog: Catalog, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_csv_row(entry) for entry in catalog.entries)
    output.write_text(buffer.getvalue(), encoding="utf-8")
    return output


def _markdown_fraction(action: CircleIsometry) -> str:
    fraction = action.shift
    shift = str(fraction.numerator) if fraction.denominator == 1 else f"{fraction.numerator}/{fraction.denominator}"
    return f"−t+{shift}" if action.reverses else f"t+{shift}"


def _markdown_images(images: Sequence[GeneratorImage]) -> str:
    return ", ".join(
        f"`{image.generator}→{_markdown_fraction(image.action)}`" for image in images
    )


def write_catalog_markdown(catalog: Catalog, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Systematic spacetime-group catalog",
        "",
        (
            f"{len(catalog.entries)} nontrivial phase actions: "
            f"{len(catalog.finite_entries)} finite spatial actions and "
            f"{len(catalog.translation_entries)} square-lattice translation characters, "
            f"plus {len(catalog.reversible_relay_entries)} reversible pm relays."
        ),
        "",
        "Assignments are quotiented only by simultaneous conjugacy in the target "
        "phase group. Inflated target moduli are merged only when the exact reduced "
        "generator images agree.",
        "",
        "| ID | Domain | Generator images | Image | Kernel | Extension | Realized moduli |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for entry in catalog.entries:
        kernel = "—" if entry.kernel_order is None else str(entry.kernel_order)
        moduli = ", ".join(str(value) for value in entry.realized_in_moduli)
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{entry.id}`",
                    f"`{entry.domain}`",
                    _markdown_images(entry.generator_images),
                    str(entry.image_order),
                    kernel,
                    entry.extension_type.replace("_", " "),
                    moduli,
                )
            )
            + " |"
        )
    lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def export_catalog(
    catalog: Catalog,
    output_dir: str | Path,
    *,
    formats: Iterable[str] = ("json", "csv", "markdown"),
    basename: str = "catalog",
) -> dict[str, Path]:
    """Write selected deterministic formats and return their paths."""

    directory = Path(output_dir)
    requested = tuple(dict.fromkeys(formats))
    unknown = set(requested).difference({"json", "csv", "markdown"})
    if unknown:
        raise ValueError(f"unknown catalog export formats: {', '.join(sorted(unknown))}")
    writers = {
        "json": (write_catalog_json, ".json"),
        "csv": (write_catalog_csv, ".csv"),
        "markdown": (write_catalog_markdown, ".md"),
    }
    result: dict[str, Path] = {}
    for name in requested:
        writer, suffix = writers[name]
        result[name] = writer(catalog, directory / f"{basename}{suffix}")
    return result


__all__ = [
    "CSV_FIELDS",
    "catalog_entry_to_dict",
    "catalog_to_dict",
    "export_catalog",
    "generator_image_to_dict",
    "write_catalog_csv",
    "write_catalog_json",
    "write_catalog_markdown",
]
