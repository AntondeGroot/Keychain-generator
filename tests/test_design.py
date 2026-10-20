import pytest
from PIL import Image, ImageDraw

from keychain.design import design_keychain
from keychain.picture.palette import parse_colour
from keychain.spec import KeychainSpec

PALETTE = [parse_colour(text) for text in ("white=#ffffff", "black=#000000", "red=#e03838")]


def _red_disc_with_black_outline() -> Image.Image:
    image = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(image).ellipse((20, 20, 180, 180), fill="#e03838", outline="black", width=6)
    return image


def test_face_colours_tile_the_keychain_and_the_background_is_left_out():
    keychain = design_keychain(_red_disc_with_black_outline(), PALETTE, KeychainSpec(width_mm=50))

    shapes = {layer.name: layer.shape for layer in keychain.face}
    overlap_mm2 = sum(shape.area for shape in shapes.values()) - keychain.outline.area
    assert set(shapes) == {"red", "black"}  # the white around the disc is not part of it
    assert overlap_mm2 == pytest.approx(0, abs=1e-3)
    assert shapes["red"].union(shapes["black"]).symmetric_difference(keychain.outline).area < 1e-3
    min_x, _, max_x, _ = keychain.outline.bounds
    assert max_x - min_x == pytest.approx(50, abs=0.1)
