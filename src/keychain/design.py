"""From a picture and its filament colours to the parts of a keychain.

In two stages. Tracing the picture into colour curves takes nearly all the time; assembling
the keychain around those curves (rim, ring, rim colour, layers) takes a fraction of a second.
So a page that only changes the rim or the ring can keep the traced picture and reassemble:
the picture keeps its width, and the rim comes round it."""

from dataclasses import dataclass

from PIL import Image
from shapely.geometry.base import BaseGeometry

from keychain.picture.painted import Painting
from keychain.picture.palette import Colour
from keychain.picture.regions import colour_map
from keychain.picture.resolution import Resolution
from keychain.shape.faces import Sheets, face_layers, traced_sheets, with_rim_in
from keychain.shape.layer import Layer
from keychain.shape.outline import Outline, keychain_outline
from keychain.shape.stack import Part, stacked_parts
from keychain.spec import KeychainSpec


@dataclass(frozen=True)
class Keychain:
    face: list[Layer]  # the colours as seen from the front
    picture: BaseGeometry  # without the rim and the ring
    outline: Outline
    parts: list[Part]
    resolution: Resolution


@dataclass(frozen=True)
class TracedPicture:
    """The picture as colour curves, before any rim or ring."""

    sheets: Sheets
    ink: int  # palette index of the lines
    resolution: Resolution


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
    traced = traced_picture(image, palette, spec, painting)
    return assembled_keychain(traced, palette, spec, hole_centre, rim_colour)


def traced_picture(
    image: Image.Image, palette: list[Colour], spec: KeychainSpec, painting: Painting | None = None
) -> TracedPicture:
    colours = colour_map(image, palette, spec, painting)
    return TracedPicture(
        traced_sheets(colours, spec),
        colours.ink,
        Resolution(colours.widest_mm, colours.mm_per_px * colours.factor),
    )


def assembled_keychain(
    traced: TracedPicture,
    palette: list[Colour],
    spec: KeychainSpec,
    hole_centre: tuple[float, float] | None = None,
    rim_colour: Colour | None = None,
) -> Keychain:
    """The keychain around a traced picture: rim, ring, the colours of a face, and the layers."""
    sheets = traced.sheets
    ink = palette[traced.ink]
    outline = keychain_outline(sheets.picture, spec, hole_centre)
    face = face_layers(sheets, ink, palette, outline, spec)
    rim = rim_colour or ink
    if rim != ink:
        face = with_rim_in(face, outline.shape.difference(sheets.picture), rim)
    parts = stacked_parts(face, outline.shape, rim, spec)
    return Keychain(face, sheets.picture, outline, parts, traced.resolution)
