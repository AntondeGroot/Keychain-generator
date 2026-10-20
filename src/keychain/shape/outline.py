"""The keychain's shape: the picture with a rim around it, and a ring with the keyring hole."""

from dataclasses import dataclass

from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points

from keychain.spec import KeychainSpec

JOIN_ROUNDING_MM = 2.0  # rounds the inside corners where the ring meets the rim


@dataclass(frozen=True)
class Outline:
    shape: BaseGeometry  # the keychain seen from above, with the hole cut out
    ring: BaseGeometry  # the band around the hole, ink on both faces
    hole_centre: tuple[float, float]


def keychain_outline(
    picture: BaseGeometry, spec: KeychainSpec, hole_centre: tuple[float, float] | None = None
) -> Outline:
    """With no hole centre given, the hole goes above the highest point of the picture."""
    centre = Point(hole_centre) if hole_centre else _default_hole_centre(picture, spec)
    hole = centre.buffer(spec.hole_mm / 2)
    ring = centre.buffer(spec.hole_mm / 2 + spec.hole_wall_mm)
    body = picture.buffer(spec.rim_mm)
    joined = body.union(ring).union(_stem(body, ring, centre))
    rounded = joined.buffer(JOIN_ROUNDING_MM).buffer(-JOIN_ROUNDING_MM)
    shape = rounded.difference(hole).simplify(spec.simplify_mm)
    return Outline(shape, ring.difference(hole), (centre.x, centre.y))


def _default_hole_centre(picture: BaseGeometry, spec: KeychainSpec) -> Point:
    """Above the highest point of the picture, with a rim's width between the hole and it.

    Every other point of the picture is lower, so none of it comes closer to the hole."""
    top_x, top_y = max(_corners(picture), key=lambda corner: corner[1])
    return Point(top_x, top_y + spec.rim_mm + spec.hole_mm / 2)


def _stem(body: BaseGeometry, ring: BaseGeometry, centre: Point) -> BaseGeometry:
    """A strip as wide as the ring to the nearest part of the body, for a ring placed apart."""
    if ring.intersects(body):
        return Polygon()
    nearest_on_body, _ = nearest_points(body, centre)
    ring_radius = centre.distance(Point(ring.exterior.coords[0]))
    return LineString([nearest_on_body, centre]).buffer(ring_radius)


def _corners(shape: BaseGeometry) -> list[tuple[float, float]]:
    return [corner for piece in getattr(shape, "geoms", [shape]) for corner in piece.exterior.coords]
