# -*- coding: utf-8 -*-
"""AutoCAD Bridge Service — FastAPI entrypoint.

Run (Windows, AutoCAD open):
    uvicorn bridge_main:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `src` layout imports when launched as `bridge_main:app`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional

from config import settings
from markup_executor import (
    get_job,
    job_to_status,
    request_cancel,
    start_execute_job,
)
import autocad_client as cad
import pdf_service
from models import (
    BridgeExecuteBody,
    CalibrateExecuteResponse,
    ConnectResponse,
    DwgTextEntity,
    HealthResponse,
    JobStatus,
    TextEntitiesResponse,
)

app = FastAPI(title="AutoCAD Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    state = cad.connection_state()
    return HealthResponse(
        status="ok" if state["connected"] else "degraded",
        autocad_connected=state["connected"],
        active_doc=state["doc_name"],
        detail=state["detail"],
    )


@app.post("/autocad/connect", response_model=ConnectResponse)
def autocad_connect() -> ConnectResponse:
    try:
        _acad, doc = cad.connect_active_doc()
        doc_name = cad.com_call_retry(lambda: doc.Name)
        layers = cad.list_layers(doc)
        return ConnectResponse(success=True, doc_name=doc_name, layers=layers)
    except Exception as exc:
        return ConnectResponse(success=False, detail=str(exc))


@app.get("/autocad/text-entities", response_model=TextEntitiesResponse)
def autocad_text_entities(
    layer: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> TextEntitiesResponse:
    try:
        _acad, doc = cad.connect_active_doc()
        entities = cad.list_text_entities(doc, layer=layer, limit=limit)
        doc_name = cad.com_call_retry(lambda: doc.Name)
        return TextEntitiesResponse(
            entities=[DwgTextEntity(**e) for e in entities], doc_name=doc_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/calibrate/execute", response_model=CalibrateExecuteResponse)
def calibrate_execute(body: BridgeExecuteBody) -> CalibrateExecuteResponse:
    record = start_execute_job(body)
    return CalibrateExecuteResponse(job_id=record.job_id, status="RUNNING")  # type: ignore[arg-type]


@app.post("/calibrate/execute-with-preset", response_model=CalibrateExecuteResponse)
def calibrate_execute_with_preset(body: BridgeExecuteBody,
                                  dwg_p1: str = Query(description="DWG BL point as 'x,y'"),
                                  dwg_p2: str = Query(description="DWG BR point as 'x,y'"),
                                  dwg_p3: str = Query(description="DWG TL point as 'x,y'"),
                                  ) -> CalibrateExecuteResponse:
    """Execute using a stored calibration preset (no interactive DWG clicks)."""
    try:
        dwg_pts = [[float(v) for v in part.split(",")] for part in (dwg_p1, dwg_p2, dwg_p3)]
    except Exception:
        raise HTTPException(status_code=422, detail="dwg_p1/p2/p3 must be 'x,y' pairs.")
    record = start_execute_job(body, dwg_frame_points=dwg_pts)
    return CalibrateExecuteResponse(job_id=record.job_id, status="RUNNING")  # type: ignore[arg-type]


@app.get("/jobs/{job_id}", response_model=JobStatus)
def job_status(job_id: str) -> JobStatus:
    record = get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job_to_status(record)


@app.post("/jobs/{job_id}/cancel")
def job_cancel(job_id: str):
    if not request_cancel(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"cancelled": True}


# ─── PDF services (keep the Next.js app Python-free) ──────────────────────────

class PdfInfoBody(BaseModel):
    pdf_base64: str


@app.post("/pdf/info")
def pdf_info(body: PdfInfoBody):
    import base64 as _b64

    try:
        return pdf_service.pdf_info(_b64.b64decode(body.pdf_base64))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class PdfGenerateBody(BaseModel):
    assets: list[dict]
    page_width_mm: float = 841.0
    page_height_mm: float = 594.0
    font_size_pt: float = 6.0
    title: Optional[str] = None


@app.post("/pdf/generate")
def pdf_generate(body: PdfGenerateBody):
    import base64 as _b64

    try:
        pdf_bytes = pdf_service.pdf_generate(
            body.assets, body.page_width_mm, body.page_height_mm,
            body.font_size_pt, body.title)
        return {"pdf_base64": _b64.b64encode(pdf_bytes).decode("ascii"),
                "size_bytes": len(pdf_bytes)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class PdfRenderBody(BaseModel):
    pdf_base64: str
    page_index: int = 0
    scale: float = 1.5


@app.post("/pdf/render")
def pdf_render(body: PdfRenderBody):
    import base64 as _b64

    try:
        return pdf_service.pdf_render(
            _b64.b64decode(body.pdf_base64), body.page_index, body.scale)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class CalibrateComputeBody(BaseModel):
    pdf_points_mm: list[list[float]]
    dwg_points: list[list[float]]


@app.post("/calibrate/compute")
def calibrate_compute(body: CalibrateComputeBody):
    try:
        return pdf_service.calibrate_compute(body.pdf_points_mm, body.dwg_points)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
