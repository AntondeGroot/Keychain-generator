import pytest
from PIL import Image, ImageDraw
from shapely import unary_union
from shapely.geometry import Point, box

from keychain.design import Choices, TurnedText, assembled_keychain, traced_picture
from keychain.picture.palette import parse_colour
from keychain.shape.layer import Layer
from keychain.shape.mirror import Turn, back_face
from keychain.spec import KeychainSpec


def test_turned_text_moves_and_where_it_was_takes_the_colour_round_it():
    # A red picture with a black mark in an area round it, from x = -10 to 0: the mark turns
    # about x = -5 to run from -6 to -0.5, and moves 3 mm right, to run from -3 to 2.5.
    picture = box(-20, -10, 20, 10)
    mark = box(-9.5, -3, -4, 3)
    face = [Layer("red", picture.difference(mark), "#e03838"), Layer("black", mark, "#000000")]

    back = back_face(face, [Turn(box(-10, -5, 0, 5), (3, 0))], picture, "black")

    def colour_at(layers: list[Layer], point: Point) -> list[str]:
        return [layer.name for layer in layers if layer.shape.contains(point)]

    assert colour_at(back, Point(0, 0)) == ["black"]  # the mark, turned and moved
    assert colour_at(back, Point(-5, 0)) == ["red"]
    assert colour_at(back, Point(-8.5, 0)) == ["red"]  # the mark was here; the area's edge is red
    assert colour_at(face, Point(-8.5, 0)) == ["black"]  # the front is left as it was


def test_turned_text_is_turned_anticlockwise_as_seen_from_behind_and_sized_about_its_middle():
    # A black mark 3 by 2 mm, left of the middle of the area round it, (-5, 1), from 1 mm below
    # it to 1 mm above. Turned over it lies right of the middle; at half the size from x = -4.5
    # to -3 and y = 0.5 to 1.5; a quarter turn anticlockwise from behind, so clockwise from the
    # front, puts it below the middle: from x = -5.5 to -4.5 and y = -1 to 0.5.
    picture = box(-20, -10, 20, 10)
    mark = box(-9, 0, -6, 2)
    face = [Layer("red", picture.difference(mark), "#e03838"), Layer("black", mark, "#000000")]

    back = back_face(face, [Turn(box(-10, -4, 0, 6), (0, 0), degrees=90, scale=0.5)], picture, "black")

    [black] = [layer.shape for layer in back if layer.name == "black"]
    assert black.symmetric_difference(box(-5.5, -1, -4.5, 0.5)).area == pytest.approx(0, abs=1e-6)


def test_where_text_was_takes_the_colour_it_sits_on_not_the_ink_of_the_outlines_round_it():
    # Cream with a red mark, and ink lines along the top and bottom of the area round the mark:
    # 20 mm of the area's edge runs through ink, 10 mm through cream. The mark moves 3 mm right
    # and leaves the strip from x = -10 to -7.
    picture = box(-20, -10, 20, 10)
    mark = box(-9.5, -3, -4, 3)
    lines = box(-12, 4, 2, 6).union(box(-12, -6, 2, -4))
    cream = picture.difference(mark).difference(lines)
    face = [Layer("cream", cream, "#fce8b4"), Layer("red", mark, "#df2827"), Layer("black", lines, "#030202")]

    back = back_face(face, [Turn(box(-10, -5, 0, 5), (3, 0))], picture, "black")

    assert [layer.name for layer in back if layer.shape.contains(Point(-8.5, 0))] == ["cream"]


def test_the_colour_round_text_is_read_along_the_curve_drawn_not_along_gaps_in_the_picture():
    # Cream with a red mark, and four narrow gaps in the picture between ink lines, inside the
    # area round the mark. The rim's white fills them, and their edges, 64 mm, are longer than
    # the area's own, 30 mm.
    whole = box(-20, -10, 20, 10)
    gaps = unary_union([box(-9, y, -1, y + 0.05) for y in (-4, -2.5, 2.5, 4)])
    lines = gaps.buffer(0.3).difference(gaps)
    picture = whole.difference(gaps)
    mark = box(-9.5, -1, -4, 1)
    face = [
        Layer("cream", picture.difference(mark).difference(lines), "#fce8b4"),
        Layer("red", mark, "#df2827"),
        Layer("black", lines, "#030202"),
        Layer("white", whole.buffer(1.5).difference(whole).union(gaps), "#f9f9f8"),
    ]

    back = back_face(face, [Turn(box(-10, -5, 0, 5), (3, 0))], picture, "black")

    assert [layer.name for layer in back if layer.shape.contains(Point(-8.5, 0))] == ["cream"]


def test_text_moved_past_the_edge_of_the_picture_is_cut_off_and_the_rim_stays():
    # A red mark near the left of the picture, in a black rim from x = -21.5 to -20. The area
    # round it turns about x = -15, putting the mark from -16 to -12, and moves 6 mm left: from
    # -22 to -18, partly past the picture's edge.
    picture = box(-20, -10, 20, 10)
    rim = picture.buffer(1.5, join_style="mitre").difference(picture)
    mark = box(-18, -3, -14, 3)
    face = [
        Layer("cream", picture.difference(mark), "#fce8b4"),
        Layer("red", mark, "#df2827"),
        Layer("black", rim, "#030202"),
    ]

    back = back_face(face, [Turn(box(-19, -5, -11, 5), (-6, 0))], picture, "black")

    def colour_at(point: Point) -> list[str]:
        return [layer.name for layer in back if layer.shape.contains(point)]

    assert colour_at(Point(-19, 0)) == ["red"]  # the mark, inside the picture
    assert colour_at(Point(-20.75, 0)) == ["black"]  # past the edge: the rim, not the mark


def test_the_keychain_prints_turned_text_in_the_back_face_and_leaves_the_front_face_alone():
    # A white mark in a red disc, from x = 45 to 60 pixels, in an area round it from 40 to 90: on
    # the back the mark turns about x = 65, to run from 70 to 85, 25 pixels further right.
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 20, 180, 180), fill="#e03838", outline="black", width=6)
    draw.rectangle((45, 90, 60, 110), fill="white")
    palette = [parse_colour(text) for text in ("white=#ffffff", "black=#000000", "red=#e03838")]
    spec = KeychainSpec(width_mm=30)
    area = TurnedText(((40, 80), (90, 80), (90, 120), (40, 120)))

    keychain = assembled_keychain(
        traced_picture(image, palette, spec), palette, spec, Choices(turned_text=(area,))
    )

    bodies = {part.name: unary_union([slab.shape for slab in part.slabs]) for part in keychain.parts}
    front, back = bodies["front-white"].centroid, bodies["back-white"].centroid
    assert back.x - front.x == pytest.approx(25 * keychain.resolution.pixel_mm, abs=0.2)
    assert back.y == pytest.approx(front.y, abs=0.2)
    face_white = next(layer.shape for layer in keychain.face if layer.name == "white")
    assert bodies["front-white"].symmetric_difference(face_white).area < 1e-6  # the front as drawn


def test_a_point_on_the_page_s_picture_lands_where_the_traced_picture_has_it_in_mm():
    # A square from pixel 50 to pixel 150, so its edges are at 50 and 151 on the page, where
    # pixel i runs from i to i + 1. Down on the page is down on the keychain, where y points up.
    image = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(image).rectangle((50, 50, 150, 150), fill="#e03838", outline="black", width=4)
    palette = [parse_colour(text) for text in ("white=#ffffff", "black=#000000", "red=#e03838")]

    traced = traced_picture(image, palette, KeychainSpec(width_mm=30))

    left, bottom, right, top = traced.sheets.picture.bounds
    placement, pixel_mm = traced.placement, traced.resolution.pixel_mm
    assert placement.in_mm(50, 50) == pytest.approx((left, top), abs=pixel_mm / 2)
    assert placement.in_mm(151, 151) == pytest.approx((right, bottom), abs=pixel_mm / 2)
    assert placement.shift_in_mm(10, 10) == pytest.approx((10 * pixel_mm, -10 * pixel_mm))
