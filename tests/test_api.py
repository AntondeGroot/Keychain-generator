import base64
from io import BytesIO

from PIL import Image, ImageDraw

from keychain.spec import KeychainSpec
from keychain.web.api import designed_from_request


def test_the_page_names_the_colour_a_shade_is_of_by_its_place_in_the_list():
    # A red disc with a dark red square. The red has no name, so the server names it; the page
    # can only point at it by its place in the list.
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 20, 180, 180), fill="#e03838", outline="black", width=6)
    draw.rectangle((70, 70, 130, 130), fill="#801010")
    png = BytesIO()
    image.save(png, "PNG")
    colours = [
        {"name": "white", "hex": "#ffffff"},
        {"name": "darkred", "hex": "#801010", "shade": {"of": 3, "tone": "dark"}},
        {"name": "black", "hex": "#000000"},
        {"name": "", "hex": "#e03838"},
    ]
    request = {
        "image": "data:image/png;base64," + base64.b64encode(png.getvalue()).decode(),
        "colours": colours,
        "spec": {"width_mm": 25},
    }

    keychain = designed_from_request(request)

    assert "darkred" in {layer.name for layer in keychain.face}  # the preview still shows it
    by_filament = {f"{side}-{colour}" for side in ("back", "front") for colour in ("red", "black")}
    assert {part.name for part in keychain.parts} == {"core", *by_filament}
    in_the_square = keychain.picture.centroid
    on_top = next(
        part.name
        for part in keychain.parts
        for slab in part.slabs
        if slab.top_mm == KeychainSpec().thickness_mm and slab.shape.contains(in_the_square)
    )
    assert on_top == "front-red"
