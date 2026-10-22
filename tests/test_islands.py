from shapely.geometry import Point, box

from keychain.shape.islands import without_unprintable_islands
from keychain.shape.layer import Layer, areas_only

MIN_LINE_MM = 0.4  # a printable dot is about 0.5 mm2; the specks below are 0.04 mm2


def test_each_speck_goes_to_the_colour_around_it_even_when_one_colour_has_specks_in_several():
    in_red, in_blue = box(4.9, 4.9, 5.1, 5.1), box(14.9, 4.9, 15.1, 5.1)
    red = Layer("red", areas_only(box(0, 0, 10, 10).difference(in_red)), "#e03838")
    blue = Layer("blue", areas_only(box(10, 0, 20, 10).difference(in_blue)), "#2050e0")
    black = Layer("black", areas_only(box(20, 0, 30, 10).union(in_red).union(in_blue)), "#000000")

    cleaned = without_unprintable_islands([red, blue, black], MIN_LINE_MM)

    layers = {layer.name: layer.shape for layer in cleaned}
    assert layers["red"].contains(Point(5, 5))
    assert layers["blue"].contains(Point(15, 5))
    assert layers["black"].equals(box(20, 0, 30, 10))  # the printable part stays


def test_a_small_piece_that_can_be_printed_stays_while_a_thin_one_as_large_goes():
    # Both about 1 mm2: a dot of 1 x 1 mm prints, a strip 0.3 mm wide is thinner than a line.
    dot, strip = box(2, 2, 3, 3), box(6, 2, 6.3, 5.3)
    red = Layer("red", areas_only(box(0, 0, 10, 10).difference(dot).difference(strip)), "#e03838")
    black = Layer("black", areas_only(dot.union(strip)), "#000000")

    cleaned = without_unprintable_islands([red, black], MIN_LINE_MM)

    layers = {layer.name: layer.shape for layer in cleaned}
    assert layers["black"].equals(dot)
    assert layers["red"].contains(Point(6.15, 3.5))
