from PIL import Image, ImageDraw

from keychain.picture.palette import parse_colour
from keychain.picture.regions import colour_map
from keychain.spec import KeychainSpec

PALETTE = [parse_colour(text) for text in ("white=#ffffff", "black=#000000", "orange=#de7e31")]
WHITE = 0
SMALL_KEYCHAIN_MM = 25  # about 0.14 mm per pixel of the drawing below


def _dog_face_and_quiff() -> Image.Image:
    """Left, a white face inside a black outline with a small gap, like Snowy's fur. Right, two
    strands of hair sticking up from an orange quiff, with a notch of background between them
    that is narrower than a printed line."""
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 60, 90, 130), outline="black", width=4)
    draw.rectangle((53, 58, 56, 66), fill="white")  # the gap in the face's outline, about 0.6 mm
    draw.rectangle((120, 100, 180, 150), fill="#de7e31", outline="black", width=4)
    draw.rectangle((136, 85, 140, 105), fill="black")
    draw.rectangle((143, 85, 147, 105), fill="black")  # 2 pixels apart, about 0.3 mm
    return image


def test_background_between_strand_tips_stays_outside_while_an_enclosed_face_stays_in():
    colours = colour_map(_dog_face_and_quiff(), PALETTE, KeychainSpec(width_mm=SMALL_KEYCHAIN_MM))

    def pixel(x: int, y: int) -> tuple[int, int]:
        middle = colours.factor // 2
        return y * colours.factor + middle, x * colours.factor + middle

    face, notch = pixel(55, 95), pixel(141, 92)
    assert colours.inside[face] and colours.labels[face] == WHITE  # closed despite the gap
    assert not colours.inside[notch]  # background, which the rim will cover, not the picture
