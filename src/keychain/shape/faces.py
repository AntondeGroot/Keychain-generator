"""The colours of one face: every colour's area, and ink everywhere else inside the outline."""

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


def picture_shape(colour_map: ColourMap, spec: KeychainSpec) -> BaseGeometry:
    return _traced(colour_map.inside, colour_map, spec)


def face_layers(
    colour_map: ColourMap, palette: list[Colour], outline: Outline, spec: KeychainSpec
) -> list[Layer]:
    """Layers that tile the outline exactly; the ink layer, last, includes the rim and the ring.

    The colours are stacked like sheets of paper, the largest at the bottom. Each sheet is
    traced from its colour together with every colour above it, so between two colours there
    is one curve, the upper sheet's edge, and neighbours fit without gaps or overlaps."""
    for_colours = outline.shape.difference(outline.ring)
    order = _bottom_to_top(colour_map)
    sheets = [_traced(np.isin(colour_map.labels, order[i:]), colour_map, spec) for i in range(len(order))]
    layers = []
    covered: BaseGeometry = Polygon()
    for index, sheet in reversed(list(zip(order, sheets, strict=True))):
        visible = areas_only(sheet.intersection(for_colours).difference(covered))
        layers.insert(0, Layer(palette[index].name, visible, palette[index].hex))
        covered = covered.union(visible)
    ink = palette[colour_map.ink]
    layers.append(Layer(ink.name, areas_only(outline.shape.difference(covered)), ink.hex))
    printable = without_unprintable_islands(layers, spec.min_line_mm)
    return [layer for layer in printable if not layer.shape.is_empty]


def _bottom_to_top(colour_map: ColourMap) -> list[int]:
    """The colours other than ink, largest area first, so small details lie on top."""
    used = colour_map.labels[colour_map.inside]
    counts = np.bincount(used, minlength=used.max() + 1)
    return sorted(
        (index for index in np.nonzero(counts)[0] if index != colour_map.ink), key=lambda i: -counts[i]
    )


def _traced(mask, colour_map: ColourMap, spec: KeychainSpec) -> BaseGeometry:
    centre = centre_px(colour_map.inside)
    return traced(mask, colour_map.mm_per_px, centre, spec)
