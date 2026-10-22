"""Shades: one filament printed darker or lighter by what lies under its outer layer.

A dark red is one thin layer of red over ink; a light red is one thin layer of the lightest
colour, such as a semi-transparent white, over red. The red stays part of the red filament's
body either way, so the slicer has one red part, not one per shade."""

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from shapely import unary_union
from shapely.geometry.base import BaseGeometry

from keychain.picture.palette import Colour
from keychain.shape.layer import Layer, areas_only


class Tone(StrEnum):
    DARK = "dark"
    LIGHT = "light"


@dataclass(frozen=True)
class Shade:
    of: Colour  # the filament it is a shade of
    tone: Tone


@dataclass(frozen=True)
class Filament:
    """One filament's area of a face: in the outer layer, and in the rest of the face under it."""

    colour: Colour
    outer: BaseGeometry
    inner: BaseGeometry

    @property
    def is_whole(self) -> bool:
        """The same all the way through the face."""
        return self.outer is self.inner


def filaments(face: list[Layer], shades: dict[str, Shade], ink: Colour, lightest: Colour) -> list[Filament]:
    """The face by filament: a layer without a shade is its own filament all the way through."""
    colours: dict[str, Colour] = {}
    outer, inner = defaultdict(list), defaultdict(list)
    for layer in face:
        on_top, under = _printed_as(layer, shades.get(layer.name), ink, lightest)
        colours.setdefault(on_top.name, on_top)
        colours.setdefault(under.name, under)
        outer[on_top.name].append(layer.shape)
        inner[under.name].append(layer.shape)
    return [_filament(colour, outer[colour.name], inner[colour.name]) for colour in colours.values()]


def _filament(colour: Colour, outer: list[BaseGeometry], inner: list[BaseGeometry]) -> Filament:
    """Without shades the filament is the same in both layers: one shape, so no slab is split."""
    on_top = areas_only(unary_union(outer))
    return Filament(colour, on_top, on_top if inner == outer else areas_only(unary_union(inner)))


def check_shades(shades: dict[str, Shade]) -> None:
    """A shade is of a filament: not of itself, nor of another shade."""
    for name, shade in shades.items():
        if shade.of.name == name or shade.of.name in shades:
            raise ValueError(f"{name} can only be a shade of a colour that is not a shade itself")


def _printed_as(layer: Layer, shade: Shade | None, ink: Colour, lightest: Colour) -> tuple[Colour, Colour]:
    """The filament of the outer layer, and the one under it."""
    if shade is None:
        own = Colour(layer.name, layer.colour)
        return own, own
    if shade.tone is Tone.DARK:
        return shade.of, ink
    return lightest, shade.of
