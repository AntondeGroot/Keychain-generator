import pytest
from shapely.geometry import Point, Polygon, box

from keychain.shape.outline import keychain_outline
from keychain.spec import KeychainSpec


def test_automatic_hole_goes_above_the_picture_its_rim_clear_of_it():
    # A triangle with its peak off-centre, like Tintin's quiff: the hole goes above the peak.
    picture = Polygon([(-20, -15), (20, -15), (8, 15)])
    spec = KeychainSpec()

    outline = keychain_outline(picture, spec)

    hole = Point(outline.hole_centre).buffer(spec.hole_mm / 2)
    assert outline.hole_centre[0] == pytest.approx(8)
    assert picture.distance(hole) == pytest.approx(spec.hole_rim_mm, abs=0.01)
    assert not outline.shape.intersects(hole.buffer(-0.01))  # a real hole, cut out
    # with material all around it; the outline is simplified to keep files small, so up to
    # that tolerance of the ring's exact circle may fall just outside it
    assert outline.shape.buffer(spec.simplify_mm).contains(outline.ring)


def test_the_holes_rim_stays_off_the_picture_and_a_hole_inside_it_is_only_cut_through():
    # The rim is in the rim colour on both faces: on the picture it would paint over it.
    picture = Polygon([(-20, -15), (20, -15), (20, 15), (-20, 15)])
    spec = KeychainSpec()

    inside = keychain_outline(picture, spec, hole_centre=(0, 0))
    across_the_edge = keychain_outline(picture, spec, hole_centre=(0, 15))

    assert inside.ring.is_empty
    assert not inside.shape.intersects(Point(0, 0).buffer(spec.hole_mm / 2 - 0.01))  # still a hole
    assert across_the_edge.ring.area > 1  # the half off the picture has its rim
    assert across_the_edge.ring.intersection(picture).area < 1e-6


def test_the_hole_has_a_rim_of_its_own_width_not_the_pictures():
    picture = Polygon([(-20, -15), (20, -15), (8, 15)])
    spec = KeychainSpec(rim_mm=1, hole_mm=4, hole_rim_mm=3)

    outline = keychain_outline(picture, spec)

    centre = Point(outline.hole_centre)
    hole = centre.buffer(2)
    assert picture.distance(hole) == pytest.approx(3, abs=0.01)  # clear of the picture by its own rim
    assert outline.ring.area == pytest.approx(centre.buffer(2 + 3).difference(hole).area, rel=0.01)


def test_a_wider_neck_fills_out_where_the_tab_meets_the_keychain_and_nowhere_else():
    # A picture with a deep V cut into its bottom, far from the hole above its top right corner.
    picture = Polygon([(-20, -15), (-8, -15), (0, -5), (8, -15), (20, -15), (20, 15), (-20, 15)])

    narrow = keychain_outline(picture, KeychainSpec(neck_mm=2)).shape
    wide = keychain_outline(picture, KeychainSpec(neck_mm=8)).shape

    near_the_tab = box(5, 0, 30, 30)
    assert wide.difference(narrow).intersection(near_the_tab).area > 5
    assert narrow.symmetric_difference(wide).difference(near_the_tab).area < 0.05  # the V stays cut
