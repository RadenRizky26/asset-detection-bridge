# -*- coding: utf-8 -*-
"""PDF annotation extraction + drawing-frame detection.

Ported from markup_v4.0.py (section 3). The Tkinter manual fallback is
replaced by a programmatic API: the web frontend collects the 3 manual
points and calls :func:`manual_frame_points_mm`.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - fallback for older installs
    import fitz  # type: ignore[no-redef]

from .geometry import distance

PT_TO_MM = 25.4 / 72.0

PointMM = Tuple[float, float]


def clean_text(value: object) -> str:
    """Normalize annotation text: strip blank lines, unify newlines."""
    if value is None:
        return ""
    value = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in value.split("\n") if line.strip()]
    return "\n".join(lines)


def should_ignore(text: str, ignore_phrases: Sequence[str] = ("tidak ada di lapangan",)) -> bool:
    """True when the annotation text matches any ignore phrase (case-insensitive)."""
    low = text.lower()
    return any(phrase.lower() in low for phrase in ignore_phrases)


def get_font_size(doc: "fitz.Document", annot: "fitz.Annot") -> float:
    """Read the FreeText default-appearance (/DA) font size in points."""
    try:
        raw = doc.xref_object(annot.xref)
        match = re.search(r"/DA\s*\([^)]*?([0-9]+(?:\.[0-9]+)?)\s+Tf", raw, re.S)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return 6.0


def display_point_to_cartesian_mm(page: "fitz.Page", x_pt: float, y_pt: float) -> PointMM:
    """Display coords (pt, origin top-left) -> cartesian mm (origin bottom-left)."""
    x_mm = x_pt * PT_TO_MM
    y_mm = (page.rect.height - y_pt) * PT_TO_MM
    return (x_mm, y_mm)


def detect_pdf_frame(page: "fitz.Page") -> Optional["fitz.Rect"]:
    """Auto-detect the drawing frame: largest vector rect covering 60-98.5% of the page.

    Returns the display-space rect, or None when no candidate qualifies
    (caller should fall back to manual 3-point selection in the web UI).
    """
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height
    candidates: List[tuple] = []

    try:
        drawings = page.get_drawings()
    except Exception:
        return None

    for drawing in drawings:
        raw_rect = drawing.get("rect")
        if raw_rect is None:
            continue
        try:
            display_rect = fitz.Rect(raw_rect * page.rotation_matrix)
        except Exception:
            continue

        width, height = display_rect.width, display_rect.height
        if width <= 0 or height <= 0:
            continue

        area = width * height
        area_ratio = area / page_area
        width_ratio = width / page_rect.width
        height_ratio = height / page_rect.height

        if width_ratio < 0.70 or height_ratio < 0.70 or area_ratio < 0.60 or area_ratio >= 0.985:
            continue

        tolerance = 3.0
        if (display_rect.x0 < -tolerance or display_rect.y0 < -tolerance
                or display_rect.x1 > page_rect.width + tolerance
                or display_rect.y1 > page_rect.height + tolerance):
            continue

        candidates.append((area, display_rect))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def pdf_frame_reference_points(page: "fitz.Page", frame_rect: "fitz.Rect") -> Tuple[PointMM, PointMM, PointMM]:
    """Bottom-left, bottom-right, top-left frame corners in cartesian mm."""
    p1 = display_point_to_cartesian_mm(page, frame_rect.x0, frame_rect.y1)
    p2 = display_point_to_cartesian_mm(page, frame_rect.x1, frame_rect.y1)
    p3 = display_point_to_cartesian_mm(page, frame_rect.x0, frame_rect.y0)
    return p1, p2, p3


def manual_frame_points_mm(page: "fitz.Page",
                           display_points_pt: Sequence[Sequence[float]]) -> Tuple[PointMM, PointMM, PointMM]:
    """Convert 3 manually clicked display points (pt) to cartesian mm.

    Web replacement for the Tkinter picker: the frontend sends the 3 clicks
    (bottom-left, bottom-right, top-left) in display points.
    """
    if len(display_points_pt) != 3:
        raise ValueError("Exactly 3 manual frame points are required.")
    pts = [display_point_to_cartesian_mm(page, float(x), float(y)) for x, y in display_points_pt]
    return pts[0], pts[1], pts[2]


def extract_pdf_annotations(
    pdf_bytes: bytes,
    page_index: int = 0,
    ignore_phrases: Sequence[str] = ("tidak ada di lapangan",),
    text_height_factor: float = 1.0,
    manual_display_points_pt: Optional[Sequence[Sequence[float]]] = None,
) -> tuple:
    """Extract FreeText annotations + frame reference points from a PDF.

    Returns (records, info) where records is a list of dicts:
        {text, pdf_x_mm, pdf_y_mm, font_size_pt, font_height_pdf_mm, pdf_rotation_deg}
    and info describes the page/frame (sizes in mm, detection method).

    When auto frame detection fails, pass manual_display_points_pt
    (3 clicks from the web calibration canvas) instead.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if page_index < 0 or page_index >= len(doc):
            raise ValueError("page_index is outside the PDF page range.")

        page = doc[page_index]
        frame_rect = detect_pdf_frame(page)

        if frame_rect is not None:
            frame_points = pdf_frame_reference_points(page, frame_rect)
            frame_detection_method = "AUTO"
        elif manual_display_points_pt is not None:
            frame_points = manual_frame_points_mm(page, manual_display_points_pt)
            frame_detection_method = "MANUAL"
        else:
            raise RuntimeError(
                "PDF frame was not detected automatically. "
                "Provide manual_display_points_pt (3 clicks: BL, BR, TL)."
            )

        records: List[dict] = []
        annot = page.first_annot
        while annot:
            next_annot = annot.next
            try:
                if annot.type[1] != "FreeText":
                    continue
                text = clean_text(annot.info.get("content", ""))
                if not text or should_ignore(text, ignore_phrases):
                    continue

                font_size_pt = get_font_size(doc, annot)
                display_rect = annot.rect * page.rotation_matrix
                insertion_pdf_mm = display_point_to_cartesian_mm(
                    page, display_rect.x0, display_rect.y1)

                annot_rotation = getattr(annot, "rotation", 0) or 0
                base_rotation_deg = (annot_rotation - page.rotation) % 360

                records.append({
                    "text": text,
                    "pdf_x_mm": insertion_pdf_mm[0],
                    "pdf_y_mm": insertion_pdf_mm[1],
                    "font_size_pt": font_size_pt,
                    "font_height_pdf_mm": font_size_pt * PT_TO_MM * text_height_factor,
                    "pdf_rotation_deg": base_rotation_deg,
                })
            finally:
                annot = next_annot

        info = {
            "page_rotation_deg": page.rotation,
            "page_width_mm": page.rect.width * PT_TO_MM,
            "page_height_mm": page.rect.height * PT_TO_MM,
            "frame_detection_method": frame_detection_method,
            "frame_points_pdf_mm": [list(p) for p in frame_points],
            "frame_width_mm": distance(frame_points[0], frame_points[1]),
            "frame_height_mm": distance(frame_points[0], frame_points[2]),
        }
        return records, info
    finally:
        doc.close()
