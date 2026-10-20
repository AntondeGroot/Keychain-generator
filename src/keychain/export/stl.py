"""Extruding a flat shape into a printable body between two heights."""

import itertools

import shapely
import trimesh
from shapely.geometry import LinearRing, Polygon
from shapely.geometry.base import BaseGeometry

# Specks smaller than this cannot be printed and only make the slicer complain.
MIN_PART_AREA_MM2 = 0.01
# STL and 3MF readers store 32-bit floats, about 4 µm apart at 50 mm. Corners closer than
# that merge on load and leave a broken edge, so they are snapped to a coarser grid first.
GRID_MM = 1e-4


def extruded(shape: BaseGeometry, bottom_mm: float, top_mm: float) -> trimesh.Trimesh:
    snapped = shapely.set_precision(shape, GRID_MM)
    polygons = [
        polygon
        for piece in shapely.get_parts(snapped)
        for polygon in _without_touching_rings(piece)
        if polygon.area > MIN_PART_AREA_MM2
    ]
    bodies = [trimesh.creation.extrude_polygon(polygon, top_mm - bottom_mm) for polygon in polygons]
    mesh = trimesh.util.concatenate(bodies)
    mesh.apply_translation((0, 0, bottom_mm))
    mesh.merge_vertices()  # 3MF triangles must share corner indices, or the part is not watertight
    return mesh


def _without_touching_rings(polygon: Polygon) -> list[Polygon]:
    """The polygon, pulled in by a grid step where a hole touches another ring at one point.

    That is a valid shape, but the point would belong to two walls of the body at once, so the
    mesh would not be watertight. The step is far below anything a printer can show."""
    rings = [LinearRing(polygon.exterior.coords), *(LinearRing(hole.coords) for hole in polygon.interiors)]
    if not any(first.intersects(second) for first, second in itertools.combinations(rings, 2)):
        return [polygon]
    pulled_in = polygon.buffer(-GRID_MM, join_style="mitre")
    return [piece for piece in shapely.get_parts(pulled_in) if isinstance(piece, Polygon)]
