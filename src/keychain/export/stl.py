"""Extruding a flat shape into a printable body between two heights."""

import shapely
import trimesh
from shapely.geometry.base import BaseGeometry

# Specks smaller than this cannot be printed and only make the slicer complain.
MIN_PART_AREA_MM2 = 0.01
# STL and 3MF readers store 32-bit floats, about 4 µm apart at 50 mm. Corners closer than
# that merge on load and leave a broken edge, so they are snapped to a coarser grid first.
GRID_MM = 1e-4


def extruded(shape: BaseGeometry, bottom_mm: float, top_mm: float) -> trimesh.Trimesh:
    snapped = shapely.set_precision(shape, GRID_MM)
    polygons = [piece for piece in getattr(snapped, "geoms", [snapped]) if piece.area > MIN_PART_AREA_MM2]
    bodies = [trimesh.creation.extrude_polygon(polygon, top_mm - bottom_mm) for polygon in polygons]
    mesh = trimesh.util.concatenate(bodies)
    mesh.apply_translation((0, 0, bottom_mm))
    mesh.merge_vertices()  # 3MF triangles must share corner indices, or the part is not watertight
    return mesh
