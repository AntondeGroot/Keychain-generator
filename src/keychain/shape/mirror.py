"""Text on the back. Both faces have the same layers, so seen from behind the picture shows
mirrored, and text in it reads backwards. Text inside an area drawn round it is turned over once
more on the back, about the area's middle, so from behind it reads the right way round. It can be
moved as well, to sit on what is behind it, such as a speech bubble that is not symmetric, and
turned and made smaller where the back has less room for it.

Where the text was and no longer is, the back takes the colour round the text: the colour most
of the area's edge runs through, leaving out ink. Ink is the lines, such as the outlines of the
letters and of a speech bubble, so it is rarely what text sits on."""

from dataclasses import dataclass

from shapely import affinity, unary_union
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from keychain.shape.layer import Layer, areas_only


@dataclass(frozen=True)
class Turn:
    area: BaseGeometry  # round the text, in mm
    shift: tuple[float, float]  # where the turned text moves, in mm, seen from the front
    degrees: float = 0.0  # anticlockwise as seen from behind, about the area's middle
    scale: float = 1.0  # about the area's middle


def landing(turn: Turn) -> BaseGeometry:
    """Where the area lands on the back, turned over, turned, sized and moved."""
    return _moved(turn, turn.area)


def back_face(face: list[Layer], turns: list[Turn], picture: BaseGeometry, ink: str) -> list[Layer]:
    """The back face's layers, as seen from the front like the face's; the face itself without
    turns. Only the picture turns: the rim and the ring stay where they are."""
    for turn in turns:
        face = _turned(face, turn, picture, ink)
    return face


def _turned(face: list[Layer], turn: Turn, picture: BaseGeometry, ink: str) -> list[Layer]:
    """Text landing past the picture's edge is left out there."""
    area = turn.area.intersection(picture)
    lands = _moved(turn, area).intersection(picture)
    around = _colour_round(face, turn.area.boundary.intersection(picture), ink)

    def turned_layer(layer: Layer) -> Layer:
        stays = layer.shape.difference(area.union(lands))
        turned = _moved(turn, layer.shape.intersection(area)).intersection(lands)
        filled = area.difference(lands) if layer.name == around else Polygon()
        return Layer(layer.name, areas_only(unary_union([stays, turned, filled])), layer.colour)

    layers = [turned_layer(layer) for layer in face]
    return [layer for layer in layers if not layer.shape.is_empty]


def _moved(turn: Turn, shape: BaseGeometry) -> BaseGeometry:
    """Anticlockwise from behind is clockwise from the front, where these shapes are."""
    left, bottom, right, top = turn.area.bounds
    middle = ((left + right) / 2, (bottom + top) / 2)
    turned = affinity.scale(shape, xfact=-turn.scale, yfact=turn.scale, origin=middle)
    turned = affinity.rotate(turned, -turn.degrees, origin=middle)
    return affinity.translate(turned, *turn.shift)


def _colour_round(face: list[Layer], edge: BaseGeometry, ink: str) -> str:
    """Along the curve drawn round the text, inside the picture: not along the picture's own
    edges, such as narrow gaps between its lines, which the rim's colour fills. Ink only when the
    edge runs through nothing else."""
    lengths = {layer.name: layer.shape.intersection(edge).length for layer in face if layer.name != ink}
    longest = max(lengths, key=lengths.__getitem__, default=None)
    return longest if longest and lengths[longest] > 0 else ink
