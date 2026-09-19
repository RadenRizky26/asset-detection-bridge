# -*- coding: utf-8 -*-
"""PDF services for the bridge: info / generate / render / compute.

These endpoints let the Next.js app stay Python-free: all PyMuPDF work
happens here.
"""

from __future__ import annotations

import base64

from pdf_markup_core.calibrate import calibration_quality, compute_calibration
from pdf_markup_core.geometry import AffineMatrix
from pdf_markup_core.pdf_extract import PT_TO_MM
from pdf_markup_core.pdf_generate import generate_markup_pdf
from pdf_markup_core.pdf_render import render_pdf_page_to_base64
from pdf_markup_core.schemas import AssetAnnotation


def pdf_info(pdf_bytes: bytes) -> dict:
    import pymupdf as fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages = []
        for i in range(len(doc)):
            page = doc[i]
            pages.append({
                "index": i,
                "width_pt": float(page.rect.width),
                "height_pt": float(page.rect.height),
                "width_mm": float(page.rect.width) * PT_TO_MM,
                "height_mm": float(page.rect.height) * PT_TO_MM,
                "rotation": int(page.rotation),
            })
        return {"page_count": len(doc), "pages": pages}
    finally:
        doc.close()


def pdf_generate(assets: list, page_width_mm: float, page_height_mm: float,
                 font_size_pt: float, title=None) -> bytes:
    models = [AssetAnnotation(**a) for a in assets]
    return generate_markup_pdf(models, page_width_mm, page_height_mm, font_size_pt, title)


def pdf_render(pdf_bytes: bytes, page_index: int, scale: float) -> dict:
    return render_pdf_page_to_base64(pdf_bytes, page_index, scale)


def calibrate_compute(pdf_points: list, dwg_points: list) -> dict:
    calibration = compute_calibration(pdf_points, dwg_points)
    matrix = AffineMatrix.from_dict(calibration.matrix.model_dump())
    quality = calibration_quality(pdf_points, dwg_points, matrix)
    return {"calibration": calibration.model_dump(), "quality": quality}
