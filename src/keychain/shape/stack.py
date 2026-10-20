"""Stacking the layers: the back face on the print bed, the core, then the front face."""

from dataclasses import dataclass

from shapely.geometry.base import BaseGeometry

from keychain.picture.palette import Colour
from keychain.shape.layer import Layer
from keychain.spec import KeychainSpec

CORE = "core"


@dataclass(frozen=True)
class Part:
    name: str
    shape: BaseGeometry
    colour: str
    bottom_mm: float
    top_mm: float


def stacked_parts(face: list[Layer], outline: BaseGeometry, ink: Colour, spec: KeychainSpec) -> list[Part]:
    """Both faces have the same layers, so seen from behind the picture shows mirrored."""
    core_bottom = spec.face_mm
    core_top = spec.face_mm + spec.core_mm
    back = [_part("back", layer, 0.0, core_bottom) for layer in face]
    core = Part(CORE, outline, ink.hex, core_bottom, core_top)
    front = [_part("front", layer, core_top, spec.thickness_mm) for layer in face]
    return [*back, core, *front]


def _part(side: str, layer: Layer, bottom_mm: float, top_mm: float) -> Part:
    return Part(f"{side}-{layer.name}", layer.shape, layer.colour, bottom_mm, top_mm)
