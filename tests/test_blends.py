import numpy as np

from keychain.picture.blends import without_edge_blends
from keychain.picture.palette import parse_colour

# Skin is nearly halfway between orange and white: what anti-aliasing makes of their edge.
PALETTE = [parse_colour(text) for text in ("white=#fefefe", "skin=#fabe93", "orange=#de7e31")]
WHITE, SKIN, ORANGE = range(3)
LINE_RADIUS_PX = 4  # half a printed line
MOST_OF_IT = 0.95


def test_a_skin_fringe_between_orange_and_white_goes_to_them_but_real_skin_stays():
    labels = np.full((60, 40), WHITE)
    labels[:30, 22:] = ORANGE
    labels[:30, 20:22] = SKIN  # a fringe 2 pixels wide along the orange-white edge
    labels[30:, 22:] = ORANGE
    labels[30:, 10:22] = SKIN  # a real area of skin, wider than a printed line, between the two
    inside = np.ones_like(labels, dtype=bool)

    cleaned = without_edge_blends(labels, inside, PALETTE, LINE_RADIUS_PX)

    assert not (cleaned[:30] == SKIN).any()
    # A sharp corner is narrower than a line too, so the corner where all four meet may go.
    assert (cleaned[30:, 10:22] == SKIN).mean() > MOST_OF_IT
