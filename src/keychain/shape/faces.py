"""The colours of one face: every colour's area, and ink everywhere else inside the outline."""

from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from keychain.picture.palette import Colour
from keychain.picture.regions import ColourMap
from keychain.picture.tracing import centre_px, traced
from keychain.shape.islands import without_unprintable_islands
from keychain.shape.layer import Layer, areas_only
from keychain.shape.outline import Outline
from keychain.spec import KeychainSpec


@dataclass(frozen=True)
class Sheets:
    """The colours stacked like sheets of paper, the largest at the bottom.

    Each sheet is traced from its colour together with every colour above it, so between two
    colours there is one curve, the upper sheet's edge, and neighbours fit without gaps or
    overlaps. The picture is made of the same curves: the sheets with the ink lines, so its
    edge is exactly a colour's edge wherever a colour meets the background."""

    colours: list[int]  # palette indices, bottom to top
    shapes: list[BaseGeometry]
    picture: BaseGeometry


def traced_sheets(colour_map: ColourMap, spec: KeychainSpec) -> Sheets:
    order = _bottom_to_top(colour_map)
    shapes = [_traced(np.isin(colour_map.labels, order[i:]), colour_map, spec) for i in range(len(order))]
    ink_lines = _traced(colour_map.labels == colour_map.ink, colour_map, spec)
    bottom = shapes[0] if shapes else Polygon()
    return Sheets(order, shapes, areas_only(bottom.union(ink_lines)))


def face_layers(
    sheets: Sheets, ink: Colour, palette: list[Colour], outline: Outline, spec: KeychainSpec
) -> list[Layer]:
    """Layers that tile the outline exactly; the ink layer, last, includes the rim and the ring."""
    for_colours = outline.shape.difference(outline.ring)
    layers = []
    covered: BaseGeometry = Polygon()
    for index, sheet in reversed(list(zip(sheets.colours, sheets.shapes, strict=True))):
        visible = areas_only(sheet.intersection(for_colours).difference(covered))
        layers.insert(0, Layer(palette[index].name, visible, palette[index].hex))
        covered = covered.union(visible)
    layers.append(Layer(ink.name, areas_only(outline.shape.difference(covered)), ink.hex))
    printable = without_unprintable_islands(layers, spec.min_line_mm)
    return [layer for layer in printable if not layer.shape.is_empty]


def with_rim_in(face: list[Layer], rim: BaseGeometry, colour: Colour) -> list[Layer]:
    """The face with the rim and the ring in this colour instead of ink. With a light rim, a
    drawing's outer lines stay visible, such as hair strands that would merge with a black rim.

    The rim joins the layer of that colour if the picture has one, so it stays one part."""
    without_rim = [Layer(layer.name, areas_only(layer.shape.difference(rim)), layer.colour) for layer in face]
    if colour.name not in {layer.name for layer in face}:
        return [*without_rim, Layer(colour.name, rim, colour.hex)]
    return [
        Layer(layer.name, areas_only(layer.shape.union(rim)), layer.colour)
        if layer.name == colour.name
        else layer
        for layer in without_rim
    ]


def _bottom_to_top(colour_map: ColourMap) -> list[int]:
    """The colours other than ink, largest area first, so small details lie on top."""
    used = colour_map.labels[colour_map.inside]
    counts = np.bincount(used, minlength=used.max() + 1)
    return sorted(
        (index for index in np.nonzero(counts)[0] if index != colour_map.ink), key=lambda i: -counts[i]
    )


def _traced(mask, colour_map: ColourMap, spec: KeychainSpec) -> BaseGeometry:
    centre = centre_px(colour_map.inside)
    return traced(mask, colour_map.mm_per_px, centre, spec, colour_map.tolerances_mm)
