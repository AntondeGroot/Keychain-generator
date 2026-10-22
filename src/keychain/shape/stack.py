"""Stacking the layers: the back face on the print bed, the core, then the front face."""

from dataclasses import dataclass

from shapely.geometry.base import BaseGeometry

from keychain.picture.palette import Colour
from keychain.shape.layer import areas_only
from keychain.shape.shades import Filament
from keychain.spec import KeychainSpec

CORE = "core"


@dataclass(frozen=True)
class Slab:
    shape: BaseGeometry
    bottom_mm: float
    top_mm: float


@dataclass(frozen=True)
class Part:
    """One filament's body: slabs of different heights where shades put it in the outer layer
    only, or under the outer layer only."""

    name: str
    colour: str
    slabs: tuple[Slab, ...]


def stacked_parts(
    face: list[Filament], outline: BaseGeometry, core: Colour, spec: KeychainSpec
) -> list[Part]:
    """Both faces have the same layers, so seen from behind the picture shows mirrored. A face's
    outer layer is at the bottom of the back face and the top of the front face.

    The core is one colour across the whole keychain, the rim's, so the printer changes no
    filament in those layers, and the rim and core make one strong body."""
    core_bottom = spec.face_mm
    core_top = spec.face_mm + spec.core_mm
    back_outer, front_outer = (0.0, spec.shade_mm), (spec.thickness_mm - spec.shade_mm, spec.thickness_mm)
    back = [_part("back", filament, back_outer, (back_outer[1], core_bottom)) for filament in face]
    middle = Part(CORE, core.hex, (Slab(outline, core_bottom, core_top),))
    front = [_part("front", filament, front_outer, (core_top, front_outer[0])) for filament in face]
    return [*back, middle, *front]


def _part(side: str, filament: Filament, outer: tuple[float, float], inner: tuple[float, float]) -> Part:
    """Where the filament is in both layers it goes through the whole face, in one slab."""
    whole = (min(*outer, *inner), max(*outer, *inner))
    name = f"{side}-{filament.colour.name}"
    if filament.is_whole:
        return Part(name, filament.colour.hex, (Slab(filament.outer, *whole),))
    pieces = [
        (filament.outer.intersection(filament.inner), whole),
        (filament.outer.difference(filament.inner), outer),
        (filament.inner.difference(filament.outer), inner),
    ]
    slabs = (Slab(areas_only(shape), *heights) for shape, heights in pieces)
    return Part(name, filament.colour.hex, tuple(slab for slab in slabs if not slab.shape.is_empty))
