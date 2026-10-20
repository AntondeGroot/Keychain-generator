"""The colours of one face: every colour's area, and ink everywhere else inside the outline."""

from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from keychain.picture.palette import Colour
from keychain.picture.regions import ColourMap
from keychain.picture.tracing import centre_px, traced
from keychain.shape.islands import without_unprintable_islands
from keychain.shape.layer import Layer
from keychain.shape.outline import Outline
from keychain.spec import KeychainSpec


def picture_shape(colour_map: ColourMap, spec: KeychainSpec) -> BaseGeometry:
    return _traced(colour_map.inside, colour_map, spec)


def face_layers(
    colour_map: ColourMap, palette: list[Colour], outline: Outline, spec: KeychainSpec
) -> list[Layer]:
    """Layers that tile the outline exactly; the ink layer, last, includes the rim and the ring.

    Ink takes whatever the other colours leave, so the hairline gaps where three traced
    colours meet become part of a line instead of a hole in the face."""
    for_colours = outline.shape.difference(outline.ring)
    taken: BaseGeometry = Polygon()
    layers = []
    for index in _colours_used(colour_map):
        traced_area = _traced(colour_map.labels == index, colour_map, spec)
        shape = traced_area.intersection(for_colours).difference(taken)
        layers.append(Layer(palette[index].name, shape, palette[index].hex))
        taken = taken.union(shape)
    ink = palette[colour_map.ink]
    layers.append(Layer(ink.name, outline.shape.difference(taken), ink.hex))
    printable = without_unprintable_islands(layers, spec.min_line_mm)
    return [layer for layer in printable if not layer.shape.is_empty]


def _colours_used(colour_map: ColourMap) -> list[int]:
    used = set(colour_map.labels[colour_map.inside].tolist())
    return sorted(used - {colour_map.ink})


def _traced(mask, colour_map: ColourMap, spec: KeychainSpec) -> BaseGeometry:
    centre = centre_px(colour_map.inside)
    return traced(mask, colour_map.mm_per_px, centre, spec.simplify_mm)
