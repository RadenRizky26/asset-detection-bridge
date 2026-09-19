# -*- coding: utf-8 -*-
"""pdf-markup-core: pure-Python core for PDF markup → AutoCAD DWG export."""

from .calibrate import calibration_quality, canvas_px_to_pdf_mm, compute_calibration
from .cloud import REV_CLOUD_BULGE, cloud_for_text_bbox, make_cloud_vertices
from .geometry import (
    AffineMatrix,
    affine_from_3_points,
    angle_between_vectors_deg,
    angle_deg,
    distance,
    transform_point,
    transform_vector,
    transformed_text_properties,
)
from .pdf_extract import (
    PT_TO_MM,
    clean_text,
    detect_pdf_frame,
    display_point_to_cartesian_mm,
    extract_pdf_annotations,
    get_font_size,
    manual_frame_points_mm,
    pdf_frame_reference_points,
    should_ignore,
)
from .pdf_generate import generate_markup_pdf
from .pdf_render import render_pdf_page_to_base64

__all__ = [
    "AffineMatrix",
    "PT_TO_MM",
    "REV_CLOUD_BULGE",
    "affine_from_3_points",
    "angle_between_vectors_deg",
    "angle_deg",
    "calibration_quality",
    "canvas_px_to_pdf_mm",
    "clean_text",
    "cloud_for_text_bbox",
    "compute_calibration",
    "detect_pdf_frame",
    "display_point_to_cartesian_mm",
    "distance",
    "extract_pdf_annotations",
    "generate_markup_pdf",
    "get_font_size",
    "make_cloud_vertices",
    "manual_frame_points_mm",
    "pdf_frame_reference_points",
    "render_pdf_page_to_base64",
    "should_ignore",
    "transform_point",
    "transform_vector",
    "transformed_text_properties",
]

__version__ = "1.0.0"
