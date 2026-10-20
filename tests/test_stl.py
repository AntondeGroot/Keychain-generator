import pytest
import trimesh
from shapely.geometry import Polygon

from keychain.export.stl import extruded

THICKNESS_MM = 0.8


def test_a_hole_touching_the_outer_edge_at_one_point_still_gives_a_watertight_part():
    # Valid as a flat shape, but in a mesh that point would belong to two walls at once. Such
    # shapes turn up where a colour reaches the rim between two strands of hair.
    hole_on_the_edge = [(5, 0), (7, 3), (3, 3)]
    shape = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], holes=[hole_on_the_edge])
    assert shape.is_valid

    mesh = extruded(shape, 0, THICKNESS_MM)
    as_saved = trimesh.load(trimesh.util.wrap_as_stream(mesh.export(file_type="stl")), file_type="stl")

    assert as_saved.is_watertight
    assert as_saved.volume == pytest.approx(shape.area * THICKNESS_MM, rel=1e-3)
