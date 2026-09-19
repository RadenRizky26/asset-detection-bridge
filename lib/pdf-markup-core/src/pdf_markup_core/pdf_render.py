# -*- coding: utf-8 -*-
"""Render PDF pages to base64 PNG for the web calibration canvas."""

from __future__ import annotations

import base64

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore[no-redef]


def render_pdf_page_to_base64(pdf_bytes: bytes, page_index: int = 0,
                              scale: float = 1.5) -> dict:
    """Render one PDF page to a base64 PNG plus its dimensions.

    Returns {png_base64, width_px, height_px, page_width_pt, page_height_pt, rotation}.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if page_index < 0 or page_index >= len(doc):
            raise ValueError("page_index is outside the PDF page range.")
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return {
            "png_base64": base64.b64encode(pix.tobytes("png")).decode("ascii"),
            "width_px": pix.width,
            "height_px": pix.height,
            "render_scale": scale,
            "page_width_pt": float(page.rect.width),
            "page_height_pt": float(page.rect.height),
            "rotation": int(page.rotation),
            "page_count": len(doc),
        }
    finally:
        doc.close()
