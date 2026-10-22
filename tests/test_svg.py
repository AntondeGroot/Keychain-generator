from xml.etree import ElementTree

from PIL import Image, ImageDraw

from keychain.design import design_keychain
from keychain.export.svg import face_svg
from keychain.picture.palette import parse_colour
from keychain.spec import KeychainSpec

SVG = "{http://www.w3.org/2000/svg}"


def test_the_preview_gives_the_width_below_and_the_height_beside_without_the_rim():
    # Twice as wide as high, 30 mm wide; the rim of 1.5 mm on either side is not counted.
    image = Image.new("RGB", (240, 140), "white")
    ImageDraw.Draw(image).ellipse((20, 20, 219, 119), fill="#e03838", outline="black", width=6)
    palette = [parse_colour(text) for text in ("white=#ffffff", "black=#000000", "red=#e03838")]
    keychain = design_keychain(image, palette, KeychainSpec(width_mm=30))

    svg = ElementTree.fromstring(face_svg(keychain.face, keychain.outline.shape, keychain.picture))

    scale = svg.find(f"{SVG}g[@id='scale']")
    assert [text.text for text in scale.iter(f"{SVG}text")] == ["30.0 mm", "15.0 mm"]
