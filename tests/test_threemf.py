from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
import trimesh
from shapely.geometry import Point, box

from keychain.export.threemf import keychain_3mf
from keychain.picture.palette import parse_colour
from keychain.shape.layer import Layer
from keychain.shape.stack import stacked_parts
from keychain.spec import KeychainSpec

CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def _parts(package: bytes) -> dict[str, trimesh.Trimesh]:
    model = ElementTree.fromstring(ZipFile(BytesIO(package)).read("3D/3dmodel.model"))
    parts = {}
    for part in model.iter(f"{CORE}object"):
        if (mesh := part.find(f"{CORE}mesh")) is not None:
            vertices = [[float(v.get(axis)) for axis in "xyz"] for v in mesh.iter(f"{CORE}vertex")]
            corners = ("v1", "v2", "v3")
            faces = [[int(t.get(corner)) for corner in corners] for t in mesh.iter(f"{CORE}triangle")]
            parts[part.get("name")] = trimesh.Trimesh(vertices, faces, process=False)
    return parts


def test_3mf_stacks_back_face_core_and_front_face_as_watertight_parts():
    outline = Point(0, 0).buffer(25)
    letter = box(-10, -5, 10, 5)
    face = [Layer("red", letter, "#e03838"), Layer("black", outline.difference(letter), "#000000")]
    parts = stacked_parts(face, outline, parse_colour("black=#000000"), KeychainSpec())

    meshes = _parts(keychain_3mf("disc", parts))

    expected_heights = {
        "back-red": (0.0, 0.8),
        "back-black": (0.0, 0.8),
        "core": (0.8, 2.2),
        "front-red": (2.2, 3.0),
        "front-black": (2.2, 3.0),
    }
    assert set(meshes) == set(expected_heights)
    for name, (bottom, top) in expected_heights.items():
        (_, _, mesh_bottom), (_, _, mesh_top) = meshes[name].bounds
        assert meshes[name].is_watertight, name
        assert (mesh_bottom, mesh_top) == pytest.approx((bottom, top)), name
