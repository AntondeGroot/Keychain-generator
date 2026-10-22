import pytest
import shapely
from PIL import Image, ImageDraw
from shapely.geometry import Point

from keychain.design import design_keychain
from keychain.picture.painted import Drawing, PaintedMask, Painting
from keychain.picture.palette import Colour, parse_colour, rim_colour
from keychain.spec import KeychainSpec

PALETTE = [parse_colour(text) for text in ("white=#ffffff", "black=#000000", "red=#e03838")]


def _red_disc_with_black_outline() -> Image.Image:
    image = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(image).ellipse((20, 20, 180, 180), fill="#e03838", outline="black", width=6)
    return image


def test_face_colours_tile_the_keychain_and_the_background_is_left_out(spec):
    keychain = design_keychain(_red_disc_with_black_outline(), PALETTE, spec)

    shapes = {layer.name: layer.shape for layer in keychain.face}
    overlap_mm2 = sum(shape.area for shape in shapes.values()) - keychain.outline.shape.area
    assert set(shapes) == {"red", "black"}  # the white around the disc is not part of it
    assert overlap_mm2 == pytest.approx(0, abs=1e-3)
    assert shapes["red"].union(shapes["black"]).symmetric_difference(keychain.outline.shape).area < 1e-3
    min_x, _, max_x, _ = keychain.outline.shape.bounds
    assert max_x - min_x == pytest.approx(spec.width_mm + 2 * spec.rim_mm, abs=0.1)  # the rim comes round


def test_a_picture_given_a_width_and_a_height_fits_within_both():
    # Twice as wide as high: in a box 30 mm wide and 10 mm high, the height decides.
    image = Image.new("RGB", (240, 140), "white")
    ImageDraw.Draw(image).ellipse((20, 20, 219, 119), fill="#e03838", outline="black", width=6)

    keychain = design_keychain(image, PALETTE, KeychainSpec(width_mm=30, height_mm=10))

    min_x, min_y, max_x, max_y = keychain.picture.bounds
    assert (max_x - min_x, max_y - min_y) == pytest.approx((20, 10), abs=0.1)


def test_background_painted_across_an_outline_removes_only_the_stroke(spec):
    # A white disc inside a black line, like Snowy. Opening the line must not let the white
    # inside count as background: then the whole disc would turn into ink. The stroke is wider
    # than the gaps that get closed by themselves, about 3 mm, so it really opens the line.
    image = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(image).ellipse((20, 20, 180, 180), outline="black", width=6)
    stroke = Image.new("RGBA", image.size)
    ImageDraw.Draw(stroke).line((100, 5, 100, 40), fill="red", width=20)
    painting = Painting.of(image.size, mask=PaintedMask.from_image(stroke, image.size))

    untouched = design_keychain(image, PALETTE[:2], spec)
    with_stroke = design_keychain(image, PALETTE[:2], spec, painting)

    white_mm2 = {layer.name: layer.shape.area for layer in with_stroke.face}.get("white", 0)
    untouched_white_mm2 = {layer.name: layer.shape.area for layer in untouched.face}["white"]
    assert white_mm2 > 0.95 * untouched_white_mm2


def test_a_colour_left_out_of_the_palette_goes_to_the_nearest_colour(spec):
    # Pink blush on skin, printed without pink: the blush must become skin, not white or ink.
    palette = [parse_colour(text) for text in ("white=#ffffff", "black=#000000", "skin=#fabe93")]

    def face_with_cheek(cheek: str) -> dict:
        image = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((20, 20, 180, 180), fill="#fabe93", outline="black", width=6)
        draw.ellipse((75, 75, 125, 125), fill=cheek)
        keychain = design_keychain(image, palette, spec)
        return {layer.name: layer.shape for layer in keychain.face}

    plain, blushed = face_with_cheek("#fabe93"), face_with_cheek("#f8a888")

    assert blushed["skin"].contains(Point(0, 0))  # the blush sits in the middle of the picture
    assert blushed["skin"].area == pytest.approx(plain["skin"].area, rel=0.01)


def test_a_narrow_strip_joining_two_areas_of_a_colour_is_thickened_not_lost(spec):
    # Two patches of hair joined by a strip of 1 pixel, about 0.15 mm on the keychain, like
    # the hair along Tintin's hairline: too narrow to print, but part of the drawing.
    palette = [
        parse_colour(text) for text in ("white=#ffffff", "black=#000000", "skin=#fabe93", "orange=#de7e31")
    ]
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 50, 180, 150), fill="#fabe93", outline="black", width=6)
    draw.ellipse((40, 80, 80, 120), fill="#de7e31")
    draw.ellipse((120, 80, 160, 120), fill="#de7e31")
    draw.line((70, 100, 130, 100), fill="#de7e31", width=1)

    orange = {layer.name: layer.shape for layer in design_keychain(image, palette, spec).face}["orange"]

    just_under_half_a_line = spec.min_line_mm / 2 - 0.01
    printable_part = orange.buffer(-just_under_half_a_line).buffer(just_under_half_a_line)
    assert shapely.get_num_geometries(orange) == 1  # the strip still joins the two patches
    assert shapely.get_num_geometries(printable_part) == 1  # and is wide enough to print all along


def test_a_connect_line_joins_two_areas_of_the_colour_where_it_starts(spec):
    # Two patches of hair with skin between them, like a hairline that fades out in the picture.
    palette = [
        parse_colour(text) for text in ("white=#ffffff", "black=#000000", "skin=#fabe93", "orange=#de7e31")
    ]
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 50, 180, 150), fill="#fabe93", outline="black", width=6)
    draw.ellipse((40, 80, 80, 120), fill="#de7e31")
    draw.ellipse((120, 80, 160, 120), fill="#de7e31")
    from_one_patch_to_the_other = (((70, 100), (130, 100)),)

    def orange_pieces(painting: Painting | None) -> int:
        face = design_keychain(image, palette, spec, painting).face
        return shapely.get_num_geometries(next(layer.shape for layer in face if layer.name == "orange"))

    assert orange_pieces(None) == 2
    joined = Painting.of(image.size, drawing=Drawing(connections=from_one_patch_to_the_other))
    assert orange_pieces(joined) == 1


def test_a_white_rim_joins_the_white_part_and_the_core_takes_the_rim_colour(spec):
    # The core in the rim's colour: those layers need no filament change, and form one body.
    image = _red_disc_with_black_outline()
    white, black, _ = PALETTE

    def rim_and_core(rim_colour: Colour | None) -> tuple[str, str]:
        keychain = design_keychain(image, PALETTE, spec, rim_colour=rim_colour)
        _, _, right, _ = keychain.outline.shape.bounds
        in_the_rim = Point(right - 0.5, 0)  # the rim is 1.5 mm wide around the picture
        rim_layer = next(layer.name for layer in keychain.face if layer.shape.contains(in_the_rim))
        core = next(part for part in keychain.parts if part.name == "core")
        return rim_layer, core.colour

    assert rim_and_core(None) == ("black", black.hex)
    assert rim_and_core(white) == ("white", white.hex)


def test_a_rim_in_a_colour_the_picture_does_not_have_is_a_part_of_its_own(spec):
    # A green rim round a red disc: green is no colour of the picture, but still gets printed.
    keychain = design_keychain(
        _red_disc_with_black_outline(), PALETTE, spec, rim_colour=rim_colour("#2e7d32", PALETTE)
    )

    layers = {layer.name: layer for layer in keychain.face}
    assert set(layers) == {"red", "black", "green"}
    assert layers["green"].colour == "#2e7d32"
    picture = layers["red"].shape.union(layers["black"].shape)
    assert layers["green"].shape.area == pytest.approx(keychain.outline.shape.area - picture.area, abs=1e-3)
    assert {part.name for part in keychain.parts} >= {"front-green", "back-green", "core"}
