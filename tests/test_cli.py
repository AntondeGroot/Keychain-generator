import base64
import json
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
import trimesh
from PIL import Image, ImageDraw

from keychain.cli import main
from keychain.spec import KeychainSpec

WHITE = "#ffffff"


def _project_as_the_page_saves_it(width_mm: float) -> dict:
    image = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(image).ellipse((20, 20, 180, 180), fill="#e03838", outline="black", width=6)
    png = BytesIO()
    image.save(png, "PNG")
    colours = [
        {"name": "white", "hex": WHITE},
        {"name": "black", "hex": "#000000"},
        {"name": "red", "hex": "#e03838"},
    ]
    return {
        "format": "keychain-project",
        "version": 1,
        "image": "data:image/png;base64," + base64.b64encode(png.getvalue()).decode(),
        "mask": None,
        "detail": None,
        "paint": None,
        "connections": [],
        "rim": "white",
        "colours": colours,
        "spec": {"width_mm": width_mm},
        "hole": None,
        "name": "Red Disc",
    }


def test_make_builds_a_saved_project_with_size_options_from_the_command_line_winning(tmp_path):
    project = tmp_path / "red-disc.keychain.json"
    project.write_text(json.dumps(_project_as_the_page_saves_it(width_mm=30)))

    main(["make", "--project", str(project), "--width", "35", "--out", str(tmp_path / "out")])

    folder = tmp_path / "out" / "red-disc"
    core = trimesh.load(folder / "red-disc-core.stl")
    model = ElementTree.fromstring(ZipFile(folder / "red-disc.3mf").read("3D/3dmodel.model"))
    colours = {
        base.get("name"): base.get("displaycolor") for base in model.iter() if base.get("displaycolor")
    }
    (left, _, _), (right, _, _) = core.bounds
    picture_and_rim = 35 + 2 * KeychainSpec().rim_mm
    assert right - left == pytest.approx(picture_and_rim, abs=0.1)  # the option, not the project's 30 mm
    assert colours["core"] == WHITE.upper()  # the project's white rim, so a white core
