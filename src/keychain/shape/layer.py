"""One colour of one face of the keychain."""

from dataclasses import dataclass

from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class Layer:
    name: str
    shape: BaseGeometry
    colour: str
