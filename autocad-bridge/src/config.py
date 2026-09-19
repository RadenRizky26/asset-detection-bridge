# -*- coding: utf-8 -*-
"""Bridge service configuration (environment-driven)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    port: int = field(default_factory=lambda: _get_int("AUTOCAD_BRIDGE_PORT", 8765))
    cors_allow_origins: list = field(default_factory=lambda: [
        o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",") if o.strip()
    ])

    com_retry_count: int = field(default_factory=lambda: _get_int("AUTOCAD_COM_RETRY_COUNT", 12))
    com_retry_delay: float = field(default_factory=lambda: _get_float("AUTOCAD_COM_RETRY_DELAY", 0.15))
    import_object_delay: float = field(default_factory=lambda: _get_float("AUTOCAD_IMPORT_OBJECT_DELAY", 0.05))

    default_import_layer: str = field(default_factory=lambda: os.environ.get("DEFAULT_IMPORT_LAYER", "PDF_TAG_IMPORT"))
    default_import_layer_color: int = field(default_factory=lambda: _get_int("DEFAULT_IMPORT_LAYER_COLOR", 5))
    default_rev_cloud_layer: str = field(default_factory=lambda: os.environ.get("DEFAULT_REV_CLOUD_LAYER", "PDF_REV_CLOUD"))
    default_rev_cloud_color: int = field(default_factory=lambda: _get_int("DEFAULT_REV_CLOUD_COLOR", 1))
    create_rev_cloud: bool = field(default_factory=lambda: _get_bool("CREATE_REV_CLOUD", True))
    rev_cloud_margin_factor: float = field(default_factory=lambda: _get_float("REV_CLOUD_MARGIN_FACTOR", 0.80))
    rev_cloud_arc_factor: float = field(default_factory=lambda: _get_float("REV_CLOUD_ARC_FACTOR", 1.00))
    rev_cloud_bulge: float = field(default_factory=lambda: _get_float("REV_CLOUD_BULGE", 0.41421356237))

    ignore_text_contains: list = field(default_factory=lambda: [
        p.strip() for p in os.environ.get("IGNORE_TEXT_CONTAINS", "tidak ada di lapangan").split(",") if p.strip()
    ])
    tag_nudge_x: float = field(default_factory=lambda: _get_float("TAG_NUDGE_X", 0.0))
    tag_nudge_y: float = field(default_factory=lambda: _get_float("TAG_NUDGE_Y", 0.0))
    text_height_factor: float = field(default_factory=lambda: _get_float("TEXT_HEIGHT_FACTOR", 1.0))
    force_endpoint_osnap: bool = field(default_factory=lambda: _get_bool("FORCE_ENDPOINT_OSNAP", True))


settings = Settings()
