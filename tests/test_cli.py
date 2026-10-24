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


def test_a_height_alone_sets_the_height_and_leaves_the_width_to_follow(tmp_path):
    # Four times as wide as high: 20 mm high makes it 80 mm wide, not held to the default 50 mm.
    picture = tmp_path / "bar.png"
    image = Image.new("RGB", (440, 140), "white")
    ImageDraw.Draw(image).ellipse((20, 20, 419, 119), fill="#e03838", outline="black", width=6)
    image.save(picture)

    colours = ["white=#ffffff", "black=#000000", "red=#e03838"]
    main(["make", str(picture), "--colours", *colours, "--height", "20", "--out", str(tmp_path / "out")])

    core = trimesh.load(tmp_path / "out" / "bar" / "bar-core.stl")
    (left, _, _), (right, _, _) = core.bounds
    assert right - left == pytest.approx(80 + 2 * KeychainSpec().rim_mm, abs=0.1)


def test_a_projects_files_are_named_after_its_file_not_the_picture_it_was_made_from(tmp_path):
    project = tmp_path / "snoopy.keychain.json"  # the project saved as "Red Disc"
    project.write_text(json.dumps(_project_as_the_page_saves_it(width_mm=30)))

    main(["make", "--project", str(project), "--out", str(tmp_path / "out")])

    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == ["snoopy"]
    assert (tmp_path / "out" / "snoopy" / "snoopy.3mf").exists()
    assert (tmp_path / "out" / "snoopy" / "snoopy-core.stl").exists()
