# -*- coding: utf-8 -*-
"""Calibration helpers: mm conversion + matrix computation + validation."""

from __future__ import annotations

from typing import Sequence

from .geometry import AffineMatrix, affine_from_3_points, distance
from .pdf_extract import PT_TO_MM
from .schemas import AffineMatrixModel, CalibrationData, FramePoints


def canvas_px_to_pdf_mm(px: float, py: float, img_w_px: float, img_h_px: float,
                        page_w_pt: float, page_h_pt: float) -> tuple:
    """Calibration-canvas click (image px) -> cartesian mm.

    The canvas renders the PDF page; clicks are in image pixels (origin
    top-left). Returns (x_mm, y_mm) with origin bottom-left.
    """
    if img_w_px <= 0 or img_h_px <= 0:
        raise ValueError("Image dimensions must be positive.")
    x_pt = (px / img_w_px) * page_w_pt
    y_pt = (py / img_h_px) * page_h_pt
    x_mm = x_pt * PT_TO_MM
    y_mm = ((page_h_pt - y_pt)) * PT_TO_MM
    return (x_mm, y_mm)


def compute_calibration(pdf_points_mm: Sequence[Sequence[float]],
                        dwg_points: Sequence[Sequence[float]]) -> CalibrationData:
    """Build CalibrationData (incl. affine matrix) from 3+3 ordered points."""
    if len(pdf_points_mm) != 3 or len(dwg_points) != 3:
        raise ValueError("Exactly 3 PDF points and 3 DWG points are required.")
    matrix = affine_from_3_points(pdf_points_mm, dwg_points)
    pdf_fp = FramePoints.model_validate({
        "p1": {"x": pdf_points_mm[0][0], "y": pdf_points_mm[0][1]},
        "p2": {"x": pdf_points_mm[1][0], "y": pdf_points_mm[1][1]},
        "p3": {"x": pdf_points_mm[2][0], "y": pdf_points_mm[2][1]},
    })
    dwg_fp = FramePoints.model_validate({
        "p1": {"x": dwg_points[0][0], "y": dwg_points[0][1]},
        "p2": {"x": dwg_points[1][0], "y": dwg_points[1][1]},
        "p3": {"x": dwg_points[2][0], "y": dwg_points[2][1]},
    })
    return CalibrationData(
        pdf_frame_points_mm=pdf_fp,
        dwg_frame_points=dwg_fp,
        matrix=AffineMatrixModel(**matrix.to_dict()),
    )


def calibration_quality(pdf_points_mm: Sequence[Sequence[float]],
                        dwg_points: Sequence[Sequence[float]],
                        matrix: AffineMatrix) -> dict:
    """Residual check: transform PDF frame pts, compare with DWG frame pts.

    Returns per-point residuals and frame width/height in both spaces so the
    UI can warn when the calibration looks off (e.g. wrong click order).
    """
    from .geometry import transform_point

    residuals = []
    for pdf_pt, dwg_pt in zip(pdf_points_mm, dwg_points):
        mapped = transform_point(matrix, pdf_pt)
        residuals.append(distance(mapped, dwg_pt))
    return {
        "residuals": residuals,
        "max_residual": max(residuals) if residuals else 0.0,
        "pdf_frame_width": distance(pdf_points_mm[0], pdf_points_mm[1]),
        "pdf_frame_height": distance(pdf_points_mm[0], pdf_points_mm[2]),
        "dwg_frame_width": distance(dwg_points[0], dwg_points[1]),
        "dwg_frame_height": distance(dwg_points[0], dwg_points[2]),
    }
