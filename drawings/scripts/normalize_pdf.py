"""Normalize AutoCAD PDF output and verify strict readability."""

from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader, PdfWriter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "drawings" / "exports" / "single_line_a1_raw.pdf"
DEFAULT_OUTPUT = PROJECT_ROOT / "drawings" / "exports" / "single_line_a1.pdf"


def normalize_pdf(input_path: Path, output_path: Path) -> int:
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"AutoCAD PDF not found: {input_path}")

    reader = PdfReader(input_path, strict=False)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": "220kV renewable energy substation single-line diagram",
            "/Subject": "Course design drawing SLD-01",
            "/Creator": "AutoCAD Core Console and project normalization pipeline",
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_file:
        writer.write(output_file)

    strict_reader = PdfReader(output_path, strict=True)
    if len(strict_reader.pages) != 1:
        raise ValueError(
            f"Expected one A1 drawing page, found {len(strict_reader.pages)} pages"
        )
    media_box = strict_reader.pages[0].mediabox
    width_points = float(media_box.width)
    height_points = float(media_box.height)
    if width_points <= height_points:
        raise ValueError(
            f"Expected landscape output, got {width_points:.1f} x {height_points:.1f} pt"
        )
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    pages = normalize_pdf(args.input, args.output)
    print(f"Normalized {pages} page: {args.output.resolve()}")


if __name__ == "__main__":
    main()
