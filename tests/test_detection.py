import numpy as np
from PIL import Image, ImageDraw

from keychain.picture.detection import detect_colours
from keychain.picture.palette import Colour


def test_the_colours_of_a_character_painted_away_are_left_out():
    # A group picture: a yellow cat on the left, a brown one on the right, painted away.
    image = Image.new("RGB", (200, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 90, 90), fill="#fce514", outline="black", width=4)
    draw.ellipse((110, 10, 190, 90), fill="#b8853f", outline="black", width=4)
    background = np.zeros((100, 200), bool)
    background[:, 100:] = True

    assert "#b8853f" in {colour.hex for colour in detect_colours(image)}
    assert {colour.name for colour in detect_colours(image, background)} == {"white", "yellow", "black"}


def test_a_colour_chosen_by_hand_is_not_found_again():
    # The yellow was renamed gold by hand; finding the colours again must not add a yellow too.
    image = Image.new("RGB", (100, 100), "white")
    ImageDraw.Draw(image).ellipse((10, 10, 90, 90), fill="#fce514", outline="black", width=4)
    gold = Colour("gold", "#fae018")

    assert {colour.name for colour in detect_colours(image, known=[gold])} == {"white", "black"}
