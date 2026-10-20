"""The keychain's shape: the picture with a rim around it, and a tab with the keyring hole."""

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from keychain.spec import KeychainSpec

JOIN_ROUNDING_MM = 2.0  # rounds the inside corners where the tab meets the rim


def keychain_outline(picture: BaseGeometry, spec: KeychainSpec) -> BaseGeometry:
    hole_centre = _hole_centre(picture, spec)
    hole_radius = spec.hole_mm / 2
    tab = hole_centre.buffer(hole_radius + spec.hole_wall_mm)
    joined = picture.buffer(spec.rim_mm).union(tab)
    rounded = joined.buffer(JOIN_ROUNDING_MM).buffer(-JOIN_ROUNDING_MM)
    return rounded.difference(hole_centre.buffer(hole_radius)).simplify(spec.simplify_mm)


def _hole_centre(picture: BaseGeometry, spec: KeychainSpec) -> Point:
    """Above the highest point of the picture, with a rim's width between the hole and it.

    Every other point of the picture is lower, so none of it comes closer to the hole."""
    top_x, top_y = max(_corners(picture), key=lambda corner: corner[1])
    return Point(top_x, top_y + spec.rim_mm + spec.hole_mm / 2)


def _corners(shape: BaseGeometry) -> list[tuple[float, float]]:
    return [corner for piece in getattr(shape, "geoms", [shape]) for corner in piece.exterior.coords]
