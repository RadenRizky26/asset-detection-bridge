# -*- coding: utf-8 -*-
"""Bridge API models. Re-exports shared schemas from pdf-markup-core."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel

from pdf_markup_core.schemas import (
    AffineMatrixModel,
    AnnotationRecord,
    CalibrateExecuteRequest,
    CalibrateExecuteResponse,
    CalibrationData,
    DwgTextEntity,
    FramePoints,
    JobStatus,
    JobStatusValue,
    Point2D,
    ReferenceTextData,
)

__all__ = [
    "AffineMatrixModel",
    "AnnotationRecord",
    "BridgeExecuteBody",
    "CalibrateExecuteRequest",
    "CalibrateExecuteResponse",
    "CalibrationData",
    "ConnectResponse",
    "DwgTextEntity",
    "FramePoints",
    "HealthResponse",
    "JobStatus",
    "JobStatusValue",
    "Point2D",
    "ReferenceTextData",
    "TextEntitiesResponse",
]


class HealthResponse(BaseModel):
    status: str
    autocad_connected: bool
    active_doc: Optional[str] = None
    detail: Optional[str] = None


class ConnectResponse(BaseModel):
    success: bool
    doc_name: Optional[str] = None
    layers: List[str] = []
    detail: Optional[str] = None


class TextEntitiesResponse(BaseModel):
    entities: List[DwgTextEntity]
    doc_name: Optional[str] = None


class BridgeExecuteBody(BaseModel):
    """Body for POST /calibrate/execute — same shape as core CalibrateExecuteRequest."""

    pdf_base64: str
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
    target_space: str = "ModelSpace"
