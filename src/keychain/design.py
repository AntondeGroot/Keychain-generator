"""From a picture and its filament colours to the parts of a keychain."""

from dataclasses import dataclass

from PIL import Image

from keychain.picture.painted import DetailMask, PaintedMask
from keychain.picture.palette import Colour
from keychain.picture.regions import colour_map
from keychain.shape.faces import face_layers, picture_shape
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
    painted: PaintedMask | None = None,
    hole_centre: tuple[float, float] | None = None,
    detail: DetailMask | None = None,
) -> Keychain:
    """Without a painted mask, the background is found automatically; without a hole centre,
    the hole goes above the picture; without a detail mask, one tolerance holds everywhere."""
    colours = colour_map(image, palette, spec, painted, detail)
    outline = keychain_outline(picture_shape(colours, spec), spec, hole_centre)
    face = face_layers(colours, palette, outline, spec)
    return Keychain(face, outline, stacked_parts(face, outline.shape, palette[colours.ink], spec))
