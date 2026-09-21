# -*- coding: utf-8 -*-
"""Background job executor: PDF extract -> affine -> DWG insert -> save.

Mirrors markup_v4.0.py main() steps 3/5/7/8/9, except:
- PDF frame points come from the web calibration canvas (no Tkinter).
- DWG frame points are picked interactively in AutoCAD via COM
  (Utility.GetPoint x3) OR supplied directly by the caller when a
  calibration preset is reused.
- Reference text comes from the dropdown-selected entity handle.
"""

from __future__ import annotations

import base64
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pdf_markup_core.calibrate import compute_calibration
from pdf_markup_core.geometry import (
    AffineMatrix,
    transform_point,
    transformed_text_properties,
)
from pdf_markup_core.pdf_extract import extract_pdf_annotations

import autocad_client as cad
from config import settings
from models import BridgeExecuteBody, JobStatus


@dataclass
class JobRecord:
    job_id: str
    status: str = "PENDING"
    inserted_count: int = 0
    failed_count: int = 0
    doc_name: Optional[str] = None
    error_detail: Optional[str] = None
    cancel_requested: bool = False
    thread: Optional[threading.Thread] = field(default=None, repr=False)


_JOBS: Dict[str, JobRecord] = {}
_JOBS_LOCK = threading.Lock()
# COM is apartment-threaded: serialize all AutoCAD access.
_COM_LOCK = threading.Lock()


def create_job() -> JobRecord:
    record = JobRecord(job_id=uuid.uuid4().hex[:12])
    with _JOBS_LOCK:
        _JOBS[record.job_id] = record
    return record


def get_job(job_id: str) -> Optional[JobRecord]:
    with _JOBS_LOCK:
        return _JOBS.get(job_id)


def request_cancel(job_id: str) -> bool:
    record = get_job(job_id)
    if record is None:
        return False
    record.cancel_requested = True
    return True


def job_to_status(record: JobRecord) -> JobStatus:
    return JobStatus(
        job_id=record.job_id,
        status=record.status,  # type: ignore[arg-type]
        inserted_count=record.inserted_count,
        failed_count=record.failed_count,
        doc_name=record.doc_name,
        error_detail=record.error_detail,
    )


def start_execute_job(body: BridgeExecuteBody,
                      dwg_frame_points: Optional[List[List[float]]] = None) -> JobRecord:
    """Launch the insert job in a background thread. Returns immediately."""
    record = create_job()
    record.status = "RUNNING"

    def _runner() -> None:
        try:
            _run_execute(record, body, dwg_frame_points)
        except Exception as exc:  # pragma: no cover - defensive
            record.status = "FAILED"
            record.error_detail = str(exc)

    thread = threading.Thread(target=_runner, daemon=True, name=f"dwg-job-{record.job_id}")
    record.thread = thread
    thread.start()
    return record


def _mm_points_to_display_pt(pdf_bytes: bytes, page_index: int,
                              points_mm: List[List[float]]) -> List[List[float]]:
    """Invert cartesian mm back to display points for the manual-frame fallback."""
    import pymupdf as fitz
    from pdf_markup_core.pdf_extract import PT_TO_MM

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc[page_index]
        h_pt = float(page.rect.height)
        return [[x_mm / PT_TO_MM, h_pt - y_mm / PT_TO_MM] for x_mm, y_mm in points_mm]
    finally:
        doc.close()


def _run_execute(record: JobRecord, body: BridgeExecuteBody,
                 dwg_frame_points: Optional[List[List[float]]]) -> None:
    with _COM_LOCK:
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
        try:
            _execute(record, body, dwg_frame_points)
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass


def _execute(record: JobRecord, body: BridgeExecuteBody,
             dwg_frame_points: Optional[List[List[float]]]) -> None:
    # 1. Connect
    acad, doc = cad.connect_active_doc()
    record.doc_name = cad.com_call_retry(lambda: doc.Name)

    # 2. Extract annotations from the markup PDF.
    # Generated markup PDFs have no vector drawing frame, so auto-detection
    # will fail — fall back to the web-calibrated points (mm -> display pt).
    pdf_bytes = base64.b64decode(body.pdf_base64)
    manual_pt = _mm_points_to_display_pt(
        pdf_bytes, body.pdf_page_index,
        [[body.pdf_frame_points_mm.p1.x, body.pdf_frame_points_mm.p1.y],
         [body.pdf_frame_points_mm.p2.x, body.pdf_frame_points_mm.p2.y],
         [body.pdf_frame_points_mm.p3.x, body.pdf_frame_points_mm.p3.y]])
    records, pdf_info = extract_pdf_annotations(
        pdf_bytes,
        page_index=body.pdf_page_index,
        ignore_phrases=settings.ignore_text_contains,
        text_height_factor=settings.text_height_factor,
        manual_display_points_pt=manual_pt,
    )
    if record.cancel_requested:
        record.status = "CANCELLED"
        return

    # 3. Affine matrix: web PDF points (mm) -> DWG points
    pdf_pts = [[body.pdf_frame_points_mm.p1.x, body.pdf_frame_points_mm.p1.y],
               [body.pdf_frame_points_mm.p2.x, body.pdf_frame_points_mm.p2.y],
               [body.pdf_frame_points_mm.p3.x, body.pdf_frame_points_mm.p3.y]]
    if dwg_frame_points is not None:
        dwg_pts = [list(map(float, p)) for p in dwg_frame_points]
    else:
        # Interactive fallback (same as markup_v4.0.py): user clicks 3x in AutoCAD.
        p1, p2, p3 = cad.pick_three_frame_points(doc)
        dwg_pts = [list(p1), list(p2), list(p3)]
    calibration = compute_calibration(pdf_pts, dwg_pts)
    matrix = AffineMatrix.from_dict(calibration.matrix.model_dump())

    # 4. Reference text entity (dropdown-selected handle)
    ref_entity = cad.find_entity_by_handle(doc, body.reference_text.handle)
    ref_height = float(body.reference_text.height)
    ref_style = body.reference_text.style

    # 5. Layers + target space
    cad.ensure_layer(doc, body.import_layer, body.import_layer_color)
    if body.create_rev_clouds:
        cad.ensure_layer(doc, body.rev_cloud_layer, body.rev_cloud_color)
    space = cad.get_target_space(doc, body.target_space)

    nudge = (body.tag_nudge_x or settings.tag_nudge_x,
             body.tag_nudge_y or settings.tag_nudge_y)

    # 6. Insert
    inserted, failed = 0, 0
    for record_item in records:
        if record.cancel_requested:
            record.status = "CANCELLED"
            return
        try:
            cad_x, cad_y = transform_point(
                matrix, (record_item["pdf_x_mm"], record_item["pdf_y_mm"]), nudge)
            rotation_deg, cad_height = transformed_text_properties(
                matrix, record_item["pdf_rotation_deg"], ref_height)

            entities = _insert_multiline(
                space, record_item["text"], cad_x, cad_y, cad_height,
                rotation_deg, body.import_layer, ref_style)

            if body.create_rev_clouds:
                for text_entity in entities:
                    min_x, min_y, max_x, max_y = cad.get_entity_bounding_box(text_entity)
                    cad.create_revision_cloud(
                        space, min_x, min_y, max_x, max_y,
                        body.rev_cloud_layer, ref_height)

            inserted += 1
            record.inserted_count = inserted
        except Exception:
            failed += 1
            record.failed_count = failed
        time.sleep(settings.import_object_delay)

    # 7. Save + zoom
    cad.safe_document_save(doc)
    try:
        cad.com_call_retry(acad.ZoomExtents)
    except Exception:
        pass

    record.status = "COMPLETED"


def _insert_multiline(space, text: str, cad_x: float, cad_y: float, cad_height: float,
                      rotation_deg: float, layer_name: str, text_style):
    """Insert possibly multi-line text, stacking upward like markup_v4.0.py."""
    lines = text.split("\n")
    entities = []
    if len(lines) == 1:
        entities.append(cad.add_single_line_text(
            space, lines[0], cad_x, cad_y, cad_height, rotation_deg, layer_name, text_style))
        return entities

    spacing = cad_height * 1.20
    theta = math.radians(rotation_deg)
    up_x, up_y = -math.sin(theta), math.cos(theta)
    total = len(lines)
    for index, line in enumerate(lines):
        offset = (total - 1 - index) * spacing
        entities.append(cad.add_single_line_text(
            space, line, cad_x + up_x * offset, cad_y + up_y * offset,
            cad_height, rotation_deg, layer_name, text_style))
    return entities
