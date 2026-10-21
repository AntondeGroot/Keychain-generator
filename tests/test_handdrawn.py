import numpy as np
from PIL import Image, ImageDraw

from keychain.picture.handdrawn import Shape
from keychain.picture.painted import Drawing, Painting
from keychain.picture.palette import parse_colour
from keychain.picture.regions import OUTSIDE, colour_map

PALETTE = [
    parse_colour(text) for text in ("white=#ffffff", "black=#000000", "skin=#fabe93", "orange=#de7e31")
]
WHITE, BLACK, SKIN, ORANGE = range(4)
COLUMNS = range(40, 160, 10)  # where the border is measured, along its length
ZIGZAG_PX = 1.5  # about 0.2 mm either side, the kind of wobble an edge is drawn to calm
BORDER_ROW = 100


def _zigzag_border(below: str) -> Image.Image:
    """Orange above a zigzag border at row 100; below it the given colour, inside a black frame."""
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 40, 180, 160), fill=below, outline="black", width=4)
    zigzag = [(24 + x, BORDER_ROW + (ZIGZAG_PX if (x // 6) % 2 else -ZIGZAG_PX)) for x in range(0, 153, 2)]
    draw.polygon([(24, 44), *zigzag, (176, 44)], fill="#de7e31")
    return image


def _straight_edge(row: float = BORDER_ROW) -> Painting:
    return Painting.of((200, 200), drawing=Drawing(edges=(((30, row), (100, row), (170, row)),)))


def _first_row_below_the_orange(labels: np.ndarray, factor: int, column: int) -> float:
    """In picture pixels, where the orange ends going down the column."""
    down = labels[44 * factor :, column * factor + factor // 2]
    return 44 + np.argmax(down != ORANGE) / factor


def test_an_edge_straightens_a_zigzag_border_between_two_colours(spec):
    image = _zigzag_border(below="#fabe93")

    def border(painting: Painting | None) -> list[float]:
        colours = colour_map(image, PALETTE, spec, painting)
        return [_first_row_below_the_orange(colours.labels, colours.factor, column) for column in COLUMNS]

    assert np.ptp(border(None)) > 2  # the zigzag is there without an edge
    assert np.ptp(border(_straight_edge())) < 0.2  # and straight with one


def test_a_shape_gets_its_colour_and_counts_as_part_of_the_picture(spec):
    image = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(image).rectangle((20, 40, 180, 160), fill="#fabe93", outline="black", width=4)
    inside_the_skin = Shape(((80, 90), (120, 90), (120, 110), (80, 110)), "#de7e31")
    on_the_background = Shape(((90, 5), (110, 5), (110, 25), (90, 25)), "#000000")
    painting = Painting.of(image.size, drawing=Drawing(shapes=(inside_the_skin, on_the_background)))

    colours = colour_map(image, PALETTE, spec, painting)

    def label_at(x: int, y: int) -> int:
        return colours.labels[y * colours.factor, x * colours.factor]

    assert label_at(100, 100) == ORANGE
    assert label_at(100, 15) == BLACK  # drawn on the background, so now part of the picture


def test_an_edge_with_background_on_one_side_makes_that_side_background(spec):
    # An orange area with no outline of its own, its zigzag edge against the white background.
    image = Image.new("RGB", (200, 200), "white")
    zigzag = [(30 + x, BORDER_ROW + (ZIGZAG_PX if (x // 6) % 2 else -ZIGZAG_PX)) for x in range(0, 141, 2)]
    ImageDraw.Draw(image).polygon([(30, 40), *zigzag, (170, 40)], fill="#de7e31")

    colours = colour_map(image, PALETTE, spec, _straight_edge())

    rows = [_first_row_below_the_orange(colours.labels, colours.factor, column) for column in COLUMNS]
    just_below = (int((BORDER_ROW + 1) * colours.factor), COLUMNS[0] * colours.factor)
    assert np.ptp(rows) < 0.2
    assert colours.labels[just_below] == OUTSIDE
