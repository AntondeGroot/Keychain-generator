"""From a picture and its filament colours to the parts of a keychain.

In two stages. Tracing the picture into colour curves takes nearly all the time; assembling
the keychain around those curves (rim, ring, rim colour, layers) takes a fraction of a second.
So a page that only changes the rim or the ring can keep the traced picture and reassemble:
the picture keeps its width, and the rim comes round it."""

from collections.abc import Callable
from dataclasses import dataclass, field

from PIL import Image
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from keychain.picture.handdrawn import spline
from keychain.picture.nearest import darkest, lightest
from keychain.picture.painted import Painting
from keychain.picture.palette import Colour
from keychain.picture.regions import colour_map
from keychain.picture.resolution import Resolution
from keychain.picture.tracing import Placement, centre_px
from keychain.shape.faces import Sheets, face_layers, traced_sheets, with_rim_in
from keychain.shape.layer import Layer
from keychain.shape.mirror import Turn, back_face
from keychain.shape.outline import Outline, keychain_outline
from keychain.shape.shades import Filament, Shade, check_shades, filaments
from keychain.shape.stack import Part, stacked_parts
from keychain.spec import KeychainSpec


@dataclass(frozen=True)
class Keychain:
    face: list[Layer]  # the colours as seen from the front
    back: list[Layer]  # the back's colours, also as seen from the front: the face unless text turns
    turns: list[Turn]
    picture: BaseGeometry  # without the rim and the ring
    outline: Outline
    parts: list[Part]
    resolution: Resolution


@dataclass(frozen=True)
class TurnedText:
    """An area round text, drawn on the page's picture, to turn on the back so it reads right."""

    points: tuple[tuple[float, float], ...]  # a closed spline through them, in picture pixels
    shift: tuple[float, float] = (0.0, 0.0)  # where the turned text moves, in picture pixels


@dataclass(frozen=True)
class Choices:
    """What the page chooses besides the picture, its colours and its sizes. Left out, the hole
    goes above the picture, the rim, the ring and the core are ink, no colour is a shade, and no
    text is turned."""

    hole_centre: tuple[float, float] | None = None
    rim_colour: Colour | None = None
    shades: dict[str, Shade] = field(default_factory=dict)  # by colour name, printed in another filament
    turned_text: tuple[TurnedText, ...] = ()


@dataclass(frozen=True)
class TracedPicture:
    """The picture as colour curves, before any rim or ring."""

    sheets: Sheets
    ink: int  # palette index of the lines
    resolution: Resolution
    placement: Placement  # where the page's picture pixels are in mm

    def turn_in_mm(self, text: TurnedText) -> Turn:
        """The area round the text and its shift, from the page's picture pixels to mm."""
        area = Polygon([self.placement.in_mm(x, y) for x, y in spline(text.points, closed=True)])
        return Turn(area.buffer(0), self.placement.shift_in_mm(*text.shift))


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
    return assembled_keychain(traced, palette, spec, Choices(hole_centre, rim_colour))


def traced_picture(
    image: Image.Image, palette: list[Colour], spec: KeychainSpec, painting: Painting | None = None
) -> TracedPicture:
    colours = colour_map(image, palette, spec, painting)
    return TracedPicture(
        traced_sheets(colours, spec),
        colours.ink,
        Resolution(colours.widest_mm, colours.mm_per_px * colours.factor),
        Placement(colours.mm_per_px, colours.factor, centre_px(colours.inside)),
    )


def assembled_keychain(
    traced: TracedPicture, palette: list[Colour], spec: KeychainSpec, choices: Choices | None = None
) -> Keychain:
    """The keychain around a traced picture: rim, ring, the colours of each face, and the layers."""
    choices = choices or Choices()
    sheets = traced.sheets
    ink = palette[traced.ink]
    outline = keychain_outline(sheets.picture, spec, choices.hole_centre)
    face = face_layers(sheets, ink, palette, outline, spec)
    rim = choices.rim_colour or ink
    if rim != ink:
        face = with_rim_in(face, outline.shape.difference(sheets.picture), rim)
    turns = [traced.turn_in_mm(text) for text in choices.turned_text]
    back = back_face(face, turns, sheets.picture.difference(outline.ring), ink.name)
    printed = _by_filament(palette, choices.shades)
    parts = stacked_parts(printed(face), outline.shape, rim, spec, printed(back))
    return Keychain(face, back, turns, sheets.picture, outline, parts, traced.resolution)


def _by_filament(palette: list[Colour], shades: dict[str, Shade]) -> Callable[[list[Layer]], list[Filament]]:
    """A face by filament: a dark shade over ink, a light one under the lightest colour, of the
    colours that are filaments."""
    check_shades(shades)
    real = [colour for colour in palette if colour.name not in shades]
    under_dark, over_light = real[darkest(real)], real[lightest(real)]
    return lambda face: filaments(face, shades, under_dark, over_light)
