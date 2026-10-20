"""From a picture and its filament colours to the parts of a keychain."""

from dataclasses import dataclass

from PIL import Image
from shapely.geometry.base import BaseGeometry

from keychain.picture.palette import Colour
from keychain.picture.regions import colour_map
from keychain.shape.faces import face_layers, picture_shape
from keychain.shape.layer import Layer
from keychain.shape.outline import keychain_outline
from keychain.shape.stack import Part, stacked_parts
from keychain.spec import KeychainSpec


@dataclass(frozen=True)
class Keychain:
    face: list[Layer]  # the colours as seen from the front
    outline: BaseGeometry
    parts: list[Part]


def design_keychain(image: Image.Image, palette: list[Colour], spec: KeychainSpec) -> Keychain:
    colours = colour_map(image, palette, spec)
    outline = keychain_outline(picture_shape(colours, spec), spec)
    face = face_layers(colours, palette, outline, spec)
    return Keychain(face, outline, stacked_parts(face, outline, palette[colours.ink], spec))
