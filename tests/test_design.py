import pytest
from PIL import Image, ImageDraw
from shapely.geometry import Point

from keychain.design import design_keychain
from keychain.picture.painted import PaintedMask
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
    overlap_mm2 = sum(shape.area for shape in shapes.values()) - keychain.outline.shape.area
    assert set(shapes) == {"red", "black"}  # the white around the disc is not part of it
    assert overlap_mm2 == pytest.approx(0, abs=1e-3)
    assert shapes["red"].union(shapes["black"]).symmetric_difference(keychain.outline.shape).area < 1e-3
    min_x, _, max_x, _ = keychain.outline.shape.bounds
    assert max_x - min_x == pytest.approx(50, abs=0.1)


def test_background_painted_across_an_outline_removes_only_the_stroke():
    # A white disc inside a black line, like Snowy. Opening the line must not let the white
    # inside count as background: then the whole disc would turn into ink.
    image = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(image).ellipse((20, 20, 180, 180), outline="black", width=6)
    stroke = Image.new("RGBA", image.size)
    ImageDraw.Draw(stroke).line((100, 5, 100, 40), fill="red", width=8)
    painted = PaintedMask.from_image(stroke, image.size)

    untouched = design_keychain(image, PALETTE[:2], KeychainSpec())
    with_stroke = design_keychain(image, PALETTE[:2], KeychainSpec(), painted)

    white_mm2 = {layer.name: layer.shape.area for layer in with_stroke.face}.get("white", 0)
    untouched_white_mm2 = {layer.name: layer.shape.area for layer in untouched.face}["white"]
    assert white_mm2 > 0.95 * untouched_white_mm2


def test_a_colour_left_out_of_the_palette_goes_to_the_nearest_colour():
    # Pink blush on skin, printed without pink: the blush must become skin, not white or ink.
    palette = [parse_colour(text) for text in ("white=#ffffff", "black=#000000", "skin=#fabe93")]

    def face_with_cheek(cheek: str) -> dict:
        image = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((20, 20, 180, 180), fill="#fabe93", outline="black", width=6)
        draw.ellipse((75, 75, 125, 125), fill=cheek)
        keychain = design_keychain(image, palette, KeychainSpec())
        return {layer.name: layer.shape for layer in keychain.face}

    plain, blushed = face_with_cheek("#fabe93"), face_with_cheek("#f8a888")

    assert blushed["skin"].contains(Point(0, 0))  # the blush sits in the middle of the picture
    assert blushed["skin"].area == pytest.approx(plain["skin"].area, rel=0.01)
