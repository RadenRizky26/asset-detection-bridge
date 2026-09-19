# -*- coding: utf-8 -*-
"""Pydantic schemas shared between the Next.js API and the bridge service."""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Point2D(BaseModel):
    x: float
    y: float


class FramePoints(BaseModel):
    """Three ordered points: bottom-left, bottom-right, top-left."""

    p1: Point2D
    p2: Point2D
    p3: Point2D

    def as_tuples(self) -> List[tuple]:
        return [(self.p1.x, self.p1.y), (self.p2.x, self.p2.y), (self.p3.x, self.p3.y)]


class AffineMatrixModel(BaseModel):
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float


class AssetAnnotation(BaseModel):
    """One confirmed asset to place as FreeText in the markup PDF."""

    asset_tag: Optional[str] = None
    asset_type: str
    # Normalized 0-1000 bounding box (same space as AI detections)
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    pid_page: int = 1

    @property
    def label(self) -> str:
        tag = (self.asset_tag or "").strip()
        return f"{tag} | {self.asset_type}" if tag else self.asset_type


class PdfGenerateRequest(BaseModel):
    assets: List[AssetAnnotation]
    page_width_mm: float = Field(default=841.0, description="ISO A1 landscape width")
    page_height_mm: float = Field(default=594.0, description="ISO A1 landscape height")
    font_size_pt: float = 6.0
    title: Optional[str] = None


class PdfExtractInfo(BaseModel):
    page_rotation_deg: int
    page_width_mm: float
    page_height_mm: float
    frame_detection_method: Literal["AUTO", "MANUAL"]
    frame_points_pdf_mm: List[List[float]]
    frame_width_mm: float
    frame_height_mm: float


class AnnotationRecord(BaseModel):
    text: str
    pdf_x_mm: float
    pdf_y_mm: float
    font_size_pt: float
    font_height_pdf_mm: float
    pdf_rotation_deg: float


class DwgTextEntity(BaseModel):
    """One TEXT/MTEXT entity found in the active DWG (for the dropdown picker)."""

    handle: str
    object_name: Literal["AcDbText", "AcDbMText"]
    text: str
    height: float
    style: Optional[str] = None
    insertion_x: float
    insertion_y: float


class ReferenceTextData(BaseModel):
    handle: str
    height: float
    style: Optional[str] = None
    sample_text: Optional[str] = None


class CalibrationData(BaseModel):
    pdf_frame_points_mm: FramePoints
    dwg_frame_points: FramePoints
    matrix: AffineMatrixModel


JobStatusValue = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]


class CalibrateExecuteRequest(BaseModel):
    pdf_base64: str = Field(description="Generated markup PDF, base64-encoded")
    pdf_page_index: int = 0
    pdf_frame_points_mm: FramePoints
    reference_text: ReferenceTextData
    create_rev_clouds: bool = True
    import_layer: str = "PDF_TAG_IMPORT"
    import_layer_color: int = 5
    rev_cloud_layer: str = "PDF_REV_CLOUD"
    rev_cloud_color: int = 1
    tag_nudge_x: float = 0.0
    tag_nudge_y: float = 0.0
    target_space: Literal["ModelSpace", "PaperSpace"] = "ModelSpace"


class CalibrateExecuteResponse(BaseModel):
    job_id: str
    status: JobStatusValue


class JobStatus(BaseModel):
    job_id: str
    status: JobStatusValue
    inserted_count: int = 0
    failed_count: int = 0
    doc_name: Optional[str] = None
    error_detail: Optional[str] = None
