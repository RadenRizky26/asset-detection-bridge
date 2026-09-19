# -*- coding: utf-8 -*-
"""Revision-cloud vertex generation.

Ported from markup_v4.0.py (section 5). The bridge converts these vertices
into a closed LWPolyline with bulge in the DWG; this module only computes
the 2D points (DWG units) so it stays AutoCAD-free.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

REV_CLOUD_BULGE = 0.41421356237  # tan(22.5°) — classic revcloud arc

Point = Tuple[float, float]


def distribute_segment_points(p1: Sequence[float], p2: Sequence[float],
                              target_length: float) -> List[Point]:
    """Subdivide segment p1->p2 into ~target_length pieces (excludes end point)."""
    x1, y1, x2, y2 = p1[0], p1[1], p2[0], p2[1]
    length = math.hypot(x2 - x1, y2 - y1)
    divisions = max(1, int(math.ceil(length / max(target_length, 0.001))))
    return [(x1 + (x2 - x1) * (i / divisions),
             y1 + (y2 - y1) * (i / divisions)) for i in range(divisions)]


def make_cloud_vertices(min_x: float, min_y: float, max_x: float, max_y: float,
                        margin: float, arc_length: float) -> List[Point]:
    """Rectangle corners (expanded by margin) subdivided into cloud vertices."""
    left, right = min_x - margin, max_x + margin
    bottom, top = min_y - margin, max_y + margin
    corners = [(left, bottom), (right, bottom), (right, top), (left, top)]

    vertices: List[Point] = []
    for i in range(4):
        p1, p2 = corners[i], corners[(i + 1) % 4]
        vertices.extend(distribute_segment_points(p1, p2, arc_length))
    return vertices


def cloud_for_text_bbox(min_x: float, min_y: float, max_x: float, max_y: float,
                        reference_text_height: float, margin_factor: float = 0.80,
                        arc_factor: float = 1.00) -> List[Point]:
    """Convenience wrapper mirroring create_revision_cloud_around_entity sizing."""
    margin = float(reference_text_height) * margin_factor
    arc_length = float(reference_text_height) * arc_factor
    return make_cloud_vertices(min_x, min_y, max_x, max_y, margin, arc_length)
