# -*- coding: utf-8 -*-
"""Generate a markup PDF with FreeText annotations from confirmed assets.

The bridge later reads these annotations back with ``extract_pdf_annotations``
and inserts them into the active DWG — the same round-trip as markup_v4.0.py,
except the markup PDF originates from the web asset register instead of
hand-drawn fields.
"""

from __future__ import annotations

from typing import List, Sequence

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore[no-redef]

from .pdf_extract import PT_TO_MM
from .schemas import AssetAnnotation


def _norm_to_pdf_pt(bbox_norm: Sequence[float], page_w_pt: float,
                    page_h_pt: float) -> "fitz.Rect":
    """Normalized 0-1000 bbox (origin top-left, like AI detections) -> PDF rect (pt)."""
    bx, by, bw, bh = (float(v) for v in bbox_norm)
    x0 = max(0.0, min(1000.0, bx)) / 1000.0 * page_w_pt
    y0 = max(0.0, min(1000.0, by)) / 1000.0 * page_h_pt
    x1 = max(0.0, min(1000.0, bx + bw)) / 1000.0 * page_w_pt
    y1 = max(0.0, min(1000.0, by + bh)) / 1000.0 * page_h_pt
    # Guarantee a minimum annotation size so tiny symbols stay clickable.
    if x1 - x0 < 24:
        x1 = min(page_w_pt, x0 + 24)
    if y1 - y0 < 12:
        y1 = min(page_h_pt, y0 + 12)
    return fitz.Rect(x0, y0, x1, y1)


def generate_markup_pdf(assets: List[AssetAnnotation], page_width_mm: float = 841.0,
                        page_height_mm: float = 594.0, font_size_pt: float = 6.0,
                        title: str | None = None) -> bytes:
    """Build a one-page markup PDF with one FreeText annot per asset.

    Page size defaults to ISO A1 landscape. Returns the PDF as bytes.
    """
    page_w_pt = page_width_mm / PT_TO_MM
    page_h_pt = page_height_mm / PT_TO_MM

    doc = fitz.open()
    try:
        page = doc.new_page(width=page_w_pt, height=page_h_pt)

        if title:
            page.insert_text(
                fitz.Point(20, 30), title, fontsize=14,
                fontname="helv", color=(0.2, 0.2, 0.2),
            )

        for asset in assets:
            rect = _norm_to_pdf_pt(
                (asset.bbox_x, asset.bbox_y, asset.bbox_w, asset.bbox_h),
                page_w_pt, page_h_pt,
            )
            annot = page.add_freetext_annot(
                rect,
                asset.label,
                fontsize=font_size_pt,
                fontname="helv",
                text_color=(0, 0, 0),
                fill_color=(1, 1, 0.6),
                border_color=(0.8, 0, 0),
                align=0,
            )
            annot.set_border({"width": 0.5})
            annot.update()

        return doc.tobytes()
    finally:
        doc.close()
