# -*- coding: utf-8 -*-
"""Pure geometry helpers + 3-point affine transform.

Ported from markup_v4.0.py (sections 2 & 4). No external dependencies.
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple

Point = Tuple[float, float]
Vector = Tuple[float, float]


def distance(p1: Sequence[float], p2: Sequence[float]) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def angle_deg(p1: Sequence[float], p2: Sequence[float]) -> float:
    """Angle in degrees of the vector p1 -> p2."""
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))


def angle_between_vectors_deg(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Smallest angle in degrees between two 2D vectors."""
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1, mag2 = math.hypot(v1[0], v1[1]), math.hypot(v2[0], v2[1])
    if mag1 == 0 or mag2 == 0:
        return 0.0
    value = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(value))


class AffineMatrix:
    """2D affine transform:  X = a*x + b*y + c ;  Y = d*x + e*y + f."""

    __slots__ = ("a", "b", "c", "d", "e", "f")

    def __init__(self, a: float, b: float, c: float, d: float, e: float, f: float):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f

    def to_dict(self) -> dict:
        return {"a": self.a, "b": self.b, "c": self.c,
                "d": self.d, "e": self.e, "f": self.f}

    @classmethod
    def from_dict(cls, data: dict) -> "AffineMatrix":
        return cls(a=data["a"], b=data["b"], c=data["c"],
                   d=data["d"], e=data["e"], f=data["f"])

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (f"AffineMatrix(a={self.a:.6f}, b={self.b:.6f}, c={self.c:.6f}, "
                f"d={self.d:.6f}, e={self.e:.6f}, f={self.f:.6f})")


def affine_from_3_points(
    src: Sequence[Sequence[float]],
    dst: Sequence[Sequence[float]],
) -> AffineMatrix:
    """Solve the 6-parameter affine transform mapping src -> dst.

    src/dst: three 2D points each, in matching order
    (bottom-left, bottom-right, top-left).
    Raises ValueError when the source points are collinear.
    """
    (p1, p2, p3), (q1, q2, q3) = src, dst
    v1x, v1y = p2[0] - p1[0], p2[1] - p1[1]
    v2x, v2y = p3[0] - p1[0], p3[1] - p1[1]
    w1x, w1y = q2[0] - q1[0], q2[1] - q1[1]
    w2x, w2y = q3[0] - q1[0], q3[1] - q1[1]

    det = v1x * v2y - v2x * v1y
    if abs(det) < 1e-12:
        raise ValueError("Reference points are collinear.")

    a = (w1x * v2y - w2x * v1y) / det
    b = (-w1x * v2x + w2x * v1x) / det
    d = (w1y * v2y - w2y * v1y) / det
    e = (-w1y * v2x + w2y * v1x) / det
    c = q1[0] - a * p1[0] - b * p1[1]
    f = q1[1] - d * p1[0] - e * p1[1]

    return AffineMatrix(a=a, b=b, c=c, d=d, e=e, f=f)


def transform_point(matrix: AffineMatrix, point: Sequence[float],
                    nudge: Sequence[float] = (0.0, 0.0)) -> Point:
    """Apply the affine matrix to a point, plus an optional (dx, dy) nudge."""
    x, y = point
    X = matrix.a * x + matrix.b * y + matrix.c + nudge[0]
    Y = matrix.d * x + matrix.e * y + matrix.f + nudge[1]
    return (X, Y)


def transform_vector(matrix: AffineMatrix, vector: Sequence[float]) -> Vector:
    """Apply only the linear part of the matrix to a direction vector."""
    x, y = vector
    return (matrix.a * x + matrix.b * y, matrix.d * x + matrix.e * y)


def transformed_text_properties(matrix: AffineMatrix, pdf_rotation_deg: float,
                                reference_text_height: float) -> Tuple[float, float]:
    """Rotation (deg, 0-360) and height for inserted text.

    Mirrors markup_v4.0.py: height always follows the DWG reference text;
    rotation follows the transformed PDF baseline direction.
    """
    theta = math.radians(pdf_rotation_deg)
    baseline = (math.cos(theta), math.sin(theta))
    tx, ty = transform_vector(matrix, baseline)
    rotation_deg = math.degrees(math.atan2(ty, tx)) % 360
    return rotation_deg, float(reference_text_height)
