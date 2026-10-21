import numpy as np
from PIL import Image, ImageDraw

from keychain.picture.handdrawn import Shape, with_curves
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
OUTLINE_PX = 2  # about 0.6 mm, a line no wider than the band an edge redraws


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


def test_an_edge_along_a_thin_outline_keeps_the_outline(spec):
    # Orange hair above a zigzag border, with a black outline thinner than the edge's band
    # below it and the background beyond: the edge redraws the hair's border with the outline.
    image = Image.new("RGB", (200, 200), "white")
    zigzag = [(30 + x, BORDER_ROW + (ZIGZAG_PX if (x // 6) % 2 else -ZIGZAG_PX)) for x in range(0, 141, 2)]
    draw = ImageDraw.Draw(image)
    draw.polygon([(30, 40), *[(x, y + OUTLINE_PX) for x, y in zigzag], (170, 40)], fill="black")
    draw.polygon([(30, 40), *zigzag, (170, 40)], fill="#de7e31")

    colours = colour_map(image, PALETTE, spec, _straight_edge())

    just_below = (int((BORDER_ROW + 1) * colours.factor), 100 * colours.factor)
    assert colours.labels[just_below] == BLACK


def test_an_edge_moves_the_border_at_every_pixel_along_it():
    # A short edge across the top of some hair, in a picture enlarged ten times: background
    # above row 150, orange below it, and the edge a little lower. All the orange above the
    # edge becomes background, with no pixel left over.
    factor, border_row = 10, 150
    rows, columns = np.indices((400, 1000))
    labels = np.where(rows < border_row, OUTSIDE, ORANGE)
    edge = ((68.0, 16.0), (72.0, 16.4))  # rows 164.5 to 168.5 once enlarged

    _, inside, _ = with_curves(labels, labels != OUTSIDE, Drawing(edges=(edge,)), PALETTE, factor, 0.6 / 27)

    edge_row = 164.5 + 4 * (columns - 684.5) / 40
    between = (rows >= border_row) & (rows < edge_row - 1) & (columns > 690) & (columns < 720)
    assert not inside[between].any()


def test_a_shape_replaces_the_strand_it_is_drawn_over(spec):
    # A black strand in orange hair, and a shape drawn a little to the right of it: the
    # strand ends up where the shape is, not as the two together.
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 40, 180, 160), fill="#de7e31", outline="black", width=4)
    draw.rectangle((94, 70, 101, 130), fill="black")
    shape = Shape(((97, 70), (104, 70), (104, 130), (97, 130)), "#000000")
    painting = Painting.of(image.size, drawing=Drawing(shapes=(shape,)))

    colours = colour_map(image, PALETTE, spec, painting)

    def label_at(x: float, y: int) -> int:
        return colours.labels[y * colours.factor, round(x * colours.factor)]

    assert label_at(95, 100) == ORANGE  # the picture's strand, left of the shape
    assert label_at(100.5, 100) == BLACK
    assert label_at(103, 100) == BLACK  # the shape, right of the picture's strand


def test_an_edge_keeps_each_colour_along_a_side_where_it_changes():
    # Background above row 100; below it black on the left and orange on the right, such as
    # the tip of an outline next to a strand of hair. An edge across them keeps both.
    rows, columns = np.indices((200, 400))
    labels = np.where(columns < 200, BLACK, ORANGE)
    inside = rows >= BORDER_ROW
    edge = ((40.0, BORDER_ROW - 2.0), (360.0, BORDER_ROW - 2.0))

    moved, inside, _ = with_curves(labels, inside, Drawing(edges=(edge,)), PALETTE, 1, 0.05)

    just_below = BORDER_ROW + 1
    assert (moved[just_below, 60:180] == BLACK).all()
    assert (moved[just_below, 220:340] == ORANGE).all()
    assert not inside[BORDER_ROW - 4, 60:340].any()


def test_an_edge_along_a_narrow_strip_of_hair_keeps_the_strip():
    # Skin below row 100 with hair above it, wide on the left; on the right the hair narrows to
    # a strip with the outline and the background past it, as where the back of the head meets
    # the quiff. An edge along the hairline keeps the strip hair, not the outline past it.
    rows, columns = np.indices((200, 400))
    hair_top = np.where(columns < 200, 40, 86)  # the strip 14 pixels wide, a little wider than the band
    labels = np.select(
        [rows >= BORDER_ROW, rows >= hair_top, rows >= hair_top - 6], [SKIN, ORANGE, BLACK], WHITE
    )
    inside = rows >= hair_top - 6
    edge = ((20.0, float(BORDER_ROW)), (380.0, float(BORDER_ROW)))

    moved, _, _ = with_curves(labels, inside, Drawing(edges=(edge,)), PALETTE, 1, 0.05)

    assert (moved[95, 220:360] == ORANGE).all()
