"""Validate normalized polygon geometry before storing a camera parking spot.

The AI service accepts up to 50 vertices and uses the same normalized [0, 1]
coordinate space. The stored REST schema uses {x, y} dictionaries.
"""
from collections.abc import Sequence
from math import isfinite

from app.schemas.spots import Point

# Small but nonzero normalized area. Reject collapsed or numerically unstable spots.
MIN_AREA = 1e-10
EPSILON = 1e-12


def _cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: tuple[float, float], b: tuple[float, float], p: tuple[float, float]) -> bool:
    return (min(a[0], b[0]) - EPSILON <= p[0] <= max(a[0], b[0]) + EPSILON
            and min(a[1], b[1]) - EPSILON <= p[1] <= max(a[1], b[1]) + EPSILON)


def _intersects(a: tuple[float, float], b: tuple[float, float],
                c: tuple[float, float], d: tuple[float, float]) -> bool:
    ab_c = _cross(a, b, c)
    ab_d = _cross(a, b, d)
    cd_a = _cross(c, d, a)
    cd_b = _cross(c, d, b)
    if ((ab_c > EPSILON and ab_d < -EPSILON or ab_c < -EPSILON and ab_d > EPSILON)
            and (cd_a > EPSILON and cd_b < -EPSILON or cd_a < -EPSILON and cd_b > EPSILON)):
        return True
    return (abs(ab_c) <= EPSILON and _on_segment(a, b, c)
            or abs(ab_d) <= EPSILON and _on_segment(a, b, d)
            or abs(cd_a) <= EPSILON and _on_segment(c, d, a)
            or abs(cd_b) <= EPSILON and _on_segment(c, d, b))


def validate_polygon(polygon: Sequence[Point]) -> list[dict[str, float]]:
    """Return JSON-ready vertices, raising ValueError for invalid geometry."""
    if not 3 <= len(polygon) <= 50:
        raise ValueError("Polygon must contain 3 to 50 vertices")
    coords = [(float(p.x), float(p.y)) for p in polygon]
    if not all(isfinite(x) and isfinite(y) and 0 <= x <= 1 and 0 <= y <= 1 for x, y in coords):
        raise ValueError("Polygon vertices must be finite normalized coordinates in [0,1]")
    if len(set(coords)) != len(coords):
        raise ValueError("Polygon vertices must be distinct (do not repeat the closing point)")
    n = len(coords)
    area2 = sum(coords[i][0] * coords[(i + 1) % n][1]
                - coords[(i + 1) % n][0] * coords[i][1] for i in range(n))
    if abs(area2) / 2 <= MIN_AREA:
        raise ValueError("Polygon must have a nonzero area")
    for i in range(n):
        a, b = coords[i], coords[(i + 1) % n]
        for j in range(i + 1, n):
            # Consecutive edges (including first/last) always share a vertex.
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if _intersects(a, b, coords[j], coords[(j + 1) % n]):
                raise ValueError("Polygon edges must not intersect or touch")
    return [{"x": x, "y": y} for x, y in coords]
