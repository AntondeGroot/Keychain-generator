import pytest
from shapely.geometry import Point, Polygon

from keychain.shape.outline import keychain_outline
from keychain.spec import KeychainSpec


def test_automatic_hole_goes_above_the_picture_a_rim_width_clear_of_it():
    # A triangle with its peak off-centre, like Tintin's quiff: the hole goes above the peak.
    picture = Polygon([(-20, -15), (20, -15), (8, 15)])
    spec = KeychainSpec()

    outline = keychain_outline(picture, spec)

    hole = Point(outline.hole_centre).buffer(spec.hole_mm / 2)
    assert outline.hole_centre[0] == pytest.approx(8)
    assert picture.distance(hole) == pytest.approx(spec.rim_mm, abs=0.01)
    assert not outline.shape.intersects(hole.buffer(-0.01))  # a real hole, cut out
    # with material all around it; the outline is simplified to keep files small, so up to
    # that tolerance of the ring's exact circle may fall just outside it
    assert outline.shape.buffer(spec.simplify_mm).contains(outline.ring)


def test_the_ink_band_round_the_automatic_hole_stays_off_the_picture():
    # The band is ink on both faces, over whatever lies beneath: on the picture it would paint
    # the top of a quiff black.
    picture = Polygon([(-20, -15), (20, -15), (8, 15)])

    outline = keychain_outline(picture, KeychainSpec())

    assert outline.ring.intersection(picture).area < 1e-3
