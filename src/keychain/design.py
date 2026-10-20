"""From a picture and its filament colours to the parts of a keychain."""

from dataclasses import dataclass

from PIL import Image

from keychain.picture.painted import Painting
from keychain.picture.palette import Colour
from keychain.picture.regions import colour_map
from keychain.shape.faces import face_layers, traced_sheets, with_rim_in
from keychain.shape.layer import Layer
from keychain.shape.outline import Outline, keychain_outline
from keychain.shape.stack import Part, stacked_parts
from keychain.spec import KeychainSpec


@dataclass(frozen=True)
class Keychain:
    face: list[Layer]  # the colours as seen from the front
    outline: Outline
    parts: list[Part]


def design_keychain(
    image: Image.Image,
    palette: list[Colour],
    spec: KeychainSpec,
    painting: Painting | None = None,
    hole_centre: tuple[float, float] | None = None,
    rim_colour: Colour | None = None,
) -> Keychain:
    """Without painting, the background is found automatically and one curve tolerance holds
    everywhere; without a hole centre, the hole goes above the picture; without a rim colour,
    the rim, the ring and the core are ink."""
    colours = colour_map(image, palette, spec, painting)
    ink = palette[colours.ink]
    sheets = traced_sheets(colours, spec)
    outline = keychain_outline(sheets.picture, spec, hole_centre)
    face = face_layers(sheets, ink, palette, outline, spec)
    rim = rim_colour or ink
    if rim != ink:
        face = with_rim_in(face, outline.shape.difference(sheets.picture), rim)
    return Keychain(face, outline, stacked_parts(face, outline.shape, rim, spec))
