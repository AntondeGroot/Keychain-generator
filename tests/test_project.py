import json

from keychain.project import read_project


def test_an_old_project_with_the_widest_side_opens_as_a_square_for_the_picture_to_fit_in(tmp_path):
    # Version 1 saved one width for the widest side, whichever way the picture was turned.
    project = tmp_path / "old.keychain.json"
    old = {"format": "keychain-project", "version": 1, "spec": {"width_mm": 75, "rim_mm": 1.5}}
    project.write_text(json.dumps(old))

    assert read_project(project)["spec"] == {"width_mm": 75, "height_mm": 75, "rim_mm": 1.5}
