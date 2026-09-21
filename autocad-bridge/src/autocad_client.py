# -*- coding: utf-8 -*-
"""AutoCAD COM client with retry logic. Windows + AutoCAD required.

Ported from markup_v4.0.py (sections 4-5). All COM calls go through
:func:`com_call_retry` to survive transient RPC hiccups.
"""

from __future__ import annotations

import math
import time
from typing import Any, List, Optional

try:
    import pythoncom
    import win32com.client
    _COM_AVAILABLE = True
except ImportError:  # non-Windows dev machines: importable, but unusable
    pythoncom = None  # type: ignore[assignment]
    win32com = None  # type: ignore[assignment]
    _COM_AVAILABLE = False

from config import settings


def require_com() -> None:
    if not _COM_AVAILABLE:
        raise RuntimeError(
            "pywin32 is not available. The bridge service must run on Windows with AutoCAD installed."
        )


def com_call_retry(func, *args, **kwargs):
    """Call a COM function, retrying on transient failures."""
    last_error: Optional[Exception] = None
    for _ in range(settings.com_retry_count):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            try:
                pythoncom.PumpWaitingMessages()
            except Exception:
                pass
            time.sleep(settings.com_retry_delay)
    raise last_error  # type: ignore[misc]


def cad_point(x: float, y: float, z: float = 0.0):
    require_com()
    return win32com.client.VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_R8, (float(x), float(y), float(z)))


def connect_active_doc():
    """Connect to the running AutoCAD session and return (acad, doc)."""
    require_com()
    try:
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
    except Exception:
        raise RuntimeError("Gagal terhubung: Aplikasi AutoCAD belum dibuka!")
    acad.Visible = True
    try:
        doc = acad.ActiveDocument
        _ = doc.Name
        _ = doc.Utility
    except Exception:
        raise RuntimeError("Gagal mengakses file DWG aktif! Pastikan file DWG sudah terbuka di AutoCAD.")
    return acad, doc


def connection_state() -> dict:
    """Non-throwing connection probe for /health."""
    try:
        acad, doc = connect_active_doc()
        name = com_call_retry(lambda: doc.Name)
        return {"connected": True, "doc_name": name, "detail": None}
    except Exception as exc:
        return {"connected": False, "doc_name": None, "detail": str(exc)}


def ensure_layer(doc, name: str, color_index: int = 5):
    try:
        layer = doc.Layers.Item(name)
    except Exception:
        layer = doc.Layers.Add(name)
    try:
        layer.Color = color_index
    except Exception:
        pass
    return layer


def get_target_space(doc, target_space: str = "ModelSpace"):
    if target_space.lower() == "modelspace":
        return doc.ModelSpace
    if target_space.lower() == "paperspace":
        return doc.PaperSpace
    raise ValueError('target_space must be "ModelSpace" or "PaperSpace".')


def list_layers(doc) -> List[str]:
    names: List[str] = []
    count = int(com_call_retry(lambda: doc.Layers.Count))
    for i in range(count):
        try:
            names.append(str(com_call_retry(doc.Layers.Item, i).Name))
        except Exception:
            continue
    return names


def get_document_utility_robust(doc):
    for _ in range(10):
        try:
            utility = doc.Utility
            _ = utility.Prompt
            return utility
        except Exception:
            time.sleep(0.20)
    raise RuntimeError("Could not access AutoCAD Document.Utility.")


def pick_three_frame_points(doc):
    """Interactive 3-point DWG calibration (blocks until the user clicks 3x)."""
    utility = get_document_utility_robust(doc)
    old_osmode = None
    if settings.force_endpoint_osnap:
        try:
            old_osmode = doc.GetVariable("OSMODE")
            doc.SetVariable("OSMODE", 1)
        except Exception:
            old_osmode = None
    try:
        utility.Prompt("\n==============================================")
        utility.Prompt("\nPDF -> DWG : 3 POINT CALIBRATION (via Web)")
        utility.Prompt("\nKlik titik FRAME pada gambar DWG aktif:")
        utility.Prompt("\n1 = KIRI BAWAH | 2 = KANAN BAWAH | 3 = KIRI ATAS")
        utility.Prompt("\n==============================================")
        points = []
        for label in ("1/3 Klik POJOK KIRI BAWAH frame",
                      "2/3 Klik POJOK KANAN BAWAH frame",
                      "3/3 Klik POJOK KIRI ATAS frame"):
            utility.Prompt(f"\n{label}: ")
            pt = utility.GetPoint()
            points.append((float(pt[0]), float(pt[1])))
        return points[0], points[1], points[2]
    finally:
        if settings.force_endpoint_osnap and old_osmode is not None:
            try:
                doc.SetVariable("OSMODE", old_osmode)
            except Exception:
                pass


def _reference_text_height(entity) -> float:
    obj_name = getattr(entity, "ObjectName", "")
    if obj_name == "AcDbText":
        return float(entity.Height)
    if obj_name == "AcDbMText":
        try:
            return float(entity.TextHeight)
        except Exception:
            return float(entity.Height)
    raise ValueError("Not a TEXT/MTEXT entity.")


def list_text_entities(doc, layer: Optional[str] = None, limit: int = 200) -> List[dict]:
    """Scan ModelSpace for TEXT/MTEXT entities (for the web dropdown picker)."""
    space = get_target_space(doc, "ModelSpace")
    out: List[dict] = []
    count = int(com_call_retry(lambda: space.Count))
    for i in range(count):
        if len(out) >= limit:
            break
        try:
            entity = com_call_retry(space.Item, i)
        except Exception:
            continue
        try:
            obj_name = getattr(entity, "ObjectName", "")
            if obj_name not in ("AcDbText", "AcDbMText"):
                continue
            if layer and str(getattr(entity, "Layer", "")) != layer:
                continue
            handle = str(com_call_retry(lambda: entity.Handle))
            text = str(getattr(entity, "TextString", "") or "").strip()
            if not text:
                continue
            height = _reference_text_height(entity)
            style = getattr(entity, "StyleName", None)
            try:
                ins = entity.InsertionPoint
                ix, iy = float(ins[0]), float(ins[1])
            except Exception:
                ix, iy = 0.0, 0.0
            out.append({
                "handle": handle,
                "object_name": obj_name,
                "text": text[:120],
                "height": height,
                "style": str(style) if style else None,
                "insertion_x": ix,
                "insertion_y": iy,
            })
        except Exception:
            continue
    return out


def find_entity_by_handle(doc, handle: str):
    """Resolve a TEXT/MTEXT entity by handle (from the dropdown selection)."""
    space = get_target_space(doc, "ModelSpace")
    count = int(com_call_retry(lambda: space.Count))
    for i in range(count):
        try:
            entity = com_call_retry(space.Item, i)
            if str(com_call_retry(lambda: entity.Handle)) == handle:
                return entity
        except Exception:
            continue
    raise RuntimeError(f"Entity with handle {handle} not found in ModelSpace.")


def add_single_line_text(space, text: str, x: float, y: float, height: float,
                         rotation_deg: float, layer_name: str, text_style=None):
    entity = com_call_retry(space.AddText, text, cad_point(x, y, 0.0), float(height))
    entity.Layer = layer_name
    entity.Rotation = math.radians(rotation_deg)
    if text_style:
        try:
            entity.StyleName = text_style
        except Exception:
            pass
    return entity


def get_entity_bounding_box(entity):
    min_point, max_point = com_call_retry(entity.GetBoundingBox)
    return (float(min_point[0]), float(min_point[1]),
            float(max_point[0]), float(max_point[1]))


def create_revision_cloud(space, min_x: float, min_y: float, max_x: float, max_y: float,
                          layer_name: str, reference_text_height: float):
    """Closed LWPolyline with bulge around a rectangle (matches markup_v4.0.py)."""
    from pdf_markup_core.cloud import cloud_for_text_bbox

    vertices = cloud_for_text_bbox(
        min_x, min_y, max_x, max_y, float(reference_text_height),
        margin_factor=settings.rev_cloud_margin_factor,
        arc_factor=settings.rev_cloud_arc_factor,
    )
    coords: List[float] = []
    for x, y in vertices:
        coords.extend([float(x), float(y)])
    points_variant = win32com.client.VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(coords))
    cloud = com_call_retry(space.AddLightWeightPolyline, points_variant)
    com_call_retry(setattr, cloud, "Layer", layer_name)
    com_call_retry(setattr, cloud, "Closed", True)
    bulge = abs(settings.rev_cloud_bulge)
    for index in range(len(vertices)):
        try:
            com_call_retry(cloud.SetBulge, index, bulge)
        except Exception:
            pass
    return cloud


def safe_document_save(doc) -> None:
    for _ in range(settings.com_retry_count):
        try:
            doc.Save()
            return
        except Exception:
            try:
                pythoncom.PumpWaitingMessages()
            except Exception:
                pass
            time.sleep(max(settings.com_retry_delay, 0.25))
    raise RuntimeError("AutoCAD Save failed after retries.")
