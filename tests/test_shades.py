import pytest
from shapely.geometry import Point, box

from keychain.picture.palette import parse_colour
from keychain.shape.layer import Layer
from keychain.shape.shades import Shade, Tone, check_shades, filaments
from keychain.shape.stack import stacked_parts
from keychain.spec import KeychainSpec

RED, WHITE, BLACK = parse_colour("red=#e03838"), parse_colour("white=#ffffff"), parse_colour("black=#000000")


def test_a_dark_shade_is_its_colour_over_ink_and_a_light_one_the_lightest_colour_over_its_colour():
    # A red disc with a dark red square on the left and a light red one on the right.
    outline = Point(0, 0).buffer(25)
    dark, light = box(-15, -5, -5, 5), box(5, -5, 15, 5)
    face = [
        Layer("red", outline.difference(dark).difference(light), RED.hex),
        Layer("darkred", dark, "#801010"),
        Layer("pink", light, "#f4a0a0"),
    ]
    shades = {"darkred": Shade(RED, Tone.DARK), "pink": Shade(RED, Tone.LIGHT)}

    parts = stacked_parts(filaments(face, shades, BLACK, WHITE), outline, BLACK, KeychainSpec())

    def heights_at(point: Point) -> dict[str, tuple[float, float]]:
        """Each part's slab there, from its bottom to its top."""
        return {
            part.name: (round(slab.bottom_mm, 3), round(slab.top_mm, 3))
            for part in parts
            for slab in part.slabs
            if slab.shape.contains(point)
        }

    by_filament = {f"{side}-{colour}" for side in ("back", "front") for colour in ("red", "black", "white")}
    assert {part.name for part in parts} == {"core", *by_filament}  # none named after a shade
    core = {"core": (0.8, 2.2)}
    assert heights_at(Point(0, 15)) == {"back-red": (0, 0.8), **core, "front-red": (2.2, 3.0)}
    assert heights_at(Point(-10, 0)) == {
        **{"back-red": (0, 0.2), "back-black": (0.2, 0.8)},
        **core,
        **{"front-black": (2.2, 2.8), "front-red": (2.8, 3.0)},
    }
    assert heights_at(Point(10, 0)) == {
        **{"back-white": (0, 0.2), "back-red": (0.2, 0.8)},
        **core,
        **{"front-red": (2.2, 2.8), "front-white": (2.8, 3.0)},
    }


def test_a_shade_of_a_shade_is_refused_as_it_has_no_filament_to_print_in():
    # Dark red is a shade of red; a darker red still must point at red, not at the dark red.
    dark_red = parse_colour("darkred=#801010")
    shades = {"darkred": Shade(RED, Tone.DARK), "darkerred": Shade(dark_red, Tone.DARK)}

    with pytest.raises(ValueError, match="darkerred can only be a shade of a colour that is not a shade"):
        check_shades(shades)


def test_a_shade_layer_must_leave_room_under_it_in_the_face():
    # A face of a 3 mm keychain with a 1.4 mm core is 0.8 mm: a 0.8 mm shade layer is all of it.
    KeychainSpec(thickness_mm=3.0, core_mm=1.4, shade_mm=0.6)

    with pytest.raises(ValueError, match=r"outer layer \(0.8 mm\) must be thinner than a face"):
        KeychainSpec(thickness_mm=3.0, core_mm=1.4, shade_mm=0.8)
