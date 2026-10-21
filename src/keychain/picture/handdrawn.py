"""Curves drawn by hand over the picture, for edges the picture itself does not show cleanly.

An edge is an open curve from A to B through a few points: along it, the border between the
colours on either side follows the curve exactly, such as the outer edge of a head of hair. A
shape is a closed curve filled with one colour, such as a pill-shaped strand of a quiff. Both
are Catmull-Rom splines through the clicked points; the page draws the same curve."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree

from keychain.picture.blends import blend_triples
from keychain.picture.enclosed import with_enclosed_areas
from keychain.picture.masks import grown
from keychain.picture.nearest import darkest
from keychain.picture.palette import Colour

if TYPE_CHECKING:
    from keychain.picture.painted import Drawing

Point = tuple[float, float]  # (x, y) in pixels of the original picture
SAMPLES_PER_SPAN = 24  # points of the curve between two clicked points
EDGE_BAND_MM = 0.6  # pixels this close to an edge go to the colour on their side of it
SIDE_REACH = 2  # a side's colour is read beyond the band, up to this many band widths away
OUTSIDE = -1  # the side of an edge that is background
DRAWN = -2  # a shape, which an edge neither reads nor paints over
LEFT, RIGHT = -1, 1
SAMPLE_PX = 1.0  # spacing of the curve points used to find the nearest spot on it
PIECE_MM = 0.3  # an edge reads the colours either side of it in pieces this long
INK_LINE_SHARE = 0.6  # ink along this much of an edge, on one side, is a line the edge runs along
STEADY_PIECES = 3  # a piece of an edge takes the colours most of the pieces this far either side have


@dataclass(frozen=True)
class Shape:
    points: tuple[Point, ...]
    colour: str  # hex, matched to the nearest palette colour


def spline(points: list[Point] | tuple[Point, ...], closed: bool) -> np.ndarray:
    """A Catmull-Rom curve through the points, as (x, y) samples."""
    ring = np.asarray(points, dtype=float)
    if len(ring) < 2:
        return ring
    padded = np.vstack([ring[-1:], ring, ring[:2]]) if closed else np.vstack([ring[:1], ring, ring[-1:]])
    spans = len(ring) if closed else len(ring) - 1
    t = np.linspace(0, 1, SAMPLES_PER_SPAN, endpoint=False)[:, None]
    pieces = [_span(padded[i : i + 4], t) for i in range(spans)]
    end = padded[1:2] if closed else ring[-1:]
    return np.vstack([*pieces, end])


def with_curves(
    labels: np.ndarray,
    inside: np.ndarray,
    drawing: "Drawing",
    palette: list[Colour],
    factor: int,
    mm_per_px: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The shapes and the edges drawn, on the picture enlarged by the factor; also the pixels the
    shapes cover, which stay as drawn. Shapes come first: an edge ending at one, such as a
    strand of hair, fits round it. Last, an area the curves close off gets one colour."""
    labels, inside, drawn = _with_shapes(labels, inside, drawing.shapes, palette, factor, mm_per_px)
    before = np.where(drawn, DRAWN, np.where(inside, labels, OUTSIDE))
    current = _with_edges(before, drawing.edges, factor, mm_per_px, darkest(palette), blend_triples(palette))
    curves = [_enlarged(spline(points, closed=False), factor) for points in drawing.edges]
    curves += [_enlarged(spline(shape.points, closed=True), factor) for shape in drawing.shapes]
    current = with_enclosed_areas(current, before, curves, DRAWN)
    return np.where(current < 0, labels, current), current != OUTSIDE, drawn


def _with_shapes(
    labels: np.ndarray,
    inside: np.ndarray,
    shapes: tuple[Shape, ...],
    palette: list[Colour],
    factor: int,
    mm_per_px: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Each shape filled with its colour, on top of the picture; it counts as part of it. Also
    the pixels the shapes cover.

    A shape's border is where it is drawn: colour just outside it, such as the picture's own
    strand of hair next to the one drawn or the halo round its tip, goes to the colours around.
    A colour that runs on past that margin, such as an outline the shape touches, stays."""
    labels, inside = labels.copy(), inside.copy()
    drawn = np.zeros(labels.shape, dtype=bool)
    for shape in shapes:
        filled = _polygon_mask(labels.shape, _enlarged(spline(shape.points, closed=True), factor))
        labels[filled] = _nearest_index(shape.colour, palette)
        inside |= filled
        drawn |= filled
    if drawn.any():
        _without_overhang(labels, inside, drawn, EDGE_BAND_MM / mm_per_px)
    return labels, inside, drawn


def _with_edges(
    current: np.ndarray,
    edges: tuple[tuple[Point, ...], ...],
    factor: int,
    mm_per_px: float,
    ink: int,
    blends: list[tuple[int, int, int]],
) -> np.ndarray:
    """Along each edge, every pixel close to it takes the colour of its own side. Current holds
    the palette index per pixel, OUTSIDE for the background and DRAWN for the shapes.

    The colour of a side is what lies there now, just beyond the band: the two colours whose
    border the edge redraws. It is read piece by piece along the edge, as the colours can
    change along it, such as an edge across the top of the hair from a line to a strand. Where
    nothing lies beyond the band, such as between two edges drawn either side of a line, it is
    the colour in the band. A side that is background makes those pixels background. Except
    along an ink line thinner than the band, such as the outline of a head of hair: beyond the
    band lies past the line, so the line would be drawn over. Then that side is ink.

    Along the picture's outer edge, a side whose colour is a blend, such as the pale fringe
    where orange hair fades into the white around it, takes the colour it blends from instead.

    The drawn shapes stay as they are, and do not count as either side's colour."""
    current = current.copy()
    band_px = EDGE_BAND_MM / mm_per_px
    piece_samples = max(1, round(PIECE_MM / mm_per_px / SAMPLE_PX))
    for points in edges:
        band = _band(_enlarged(spline(points, closed=False), factor), current.shape, band_px)
        # Every piece reads the picture as it was before this edge, not as its neighbours left it.
        whole = [band.colour_beyond(side, current) for side in (LEFT, RIGHT)]
        pieces = band.pieces(piece_samples)
        decided = _steady([_side_colours(piece, current, whole, ink, blends) for piece in pieces])
        for piece, colours in zip(pieces, decided, strict=True):
            if colours is None:
                continue  # nothing to separate here
            for side, colour in zip((LEFT, RIGHT), colours, strict=True):
                on_side = (piece.sides == side) & (piece.distances <= band_px)
                on_side &= current[piece.rows, piece.columns] != DRAWN
                current[piece.rows[on_side], piece.columns[on_side]] = colour
    return current


def _side_colours(
    band: "Band", current: np.ndarray, whole: list[int], ink: int, blends: list[tuple[int, int, int]]
) -> list[int] | None:
    """The colours to give each side of a piece of an edge; none if both sides are the same.

    What lies beyond the band next to the piece is its side's colour if the band there agrees:
    then the colour changes along the edge, such as from an outline's tip to a strand of hair.
    If not, beyond the band lies past something thin along the edge, such as the outline past a
    narrow strip of hair, and the side's colour is what lies beyond the whole edge, if that is
    in the band here too."""
    colours = [
        band.colour_here(side, current, everywhere)
        for side, everywhere in zip((LEFT, RIGHT), whole, strict=True)
    ]
    if colours[0] == colours[1]:
        return None
    if OUTSIDE in colours:
        colours = [
            band.unblended(side, colour, current, blends)
            for side, colour in zip((LEFT, RIGHT), colours, strict=True)
        ]
    line_side = band.side_of_line(ink, current)
    if line_side is None:
        return colours
    # The line lies along this side: past it, beyond the band, can be anything. The other side
    # read ink only beyond the band, from some other line, so it is what lies in the band there.
    line, other = (LEFT, RIGHT).index(line_side), (RIGHT, LEFT).index(line_side)
    colours[line] = ink
    if colours[other] == ink:
        colours[other] = band.colour_within(-line_side, current, ink)
    return None if colours[0] == colours[1] else colours


def _steady(decided: list[list[int] | None]) -> list[list[int] | None]:
    """The colours of each piece of an edge as most of the pieces around it have them.

    A piece can read its sides wrong where the picture is blurred, such as where a halo hides
    the border between hair and its outline: it then sees the same colour on both sides, or a
    colour none of its neighbours see, and would leave a splotch the size of a piece. A real
    change of colour along the edge runs on over several pieces, so it stays."""
    steady = []
    for index, own in enumerate(decided):
        around = Counter(
            tuple(colours)
            for colours in decided[max(0, index - STEADY_PIECES) : index + STEADY_PIECES + 1]
            if colours is not None
        )
        if not around:
            steady.append(None)
            continue
        most = max(around.values())
        keep = own is not None and around[tuple(own)] == most
        steady.append(own if keep else list(next(c for c, n in around.items() if n == most)))
    return steady


@dataclass(frozen=True)
class Band:
    """The pixels close to an edge, with the side of the edge each lies on and how close."""

    rows: np.ndarray
    columns: np.ndarray
    sides: np.ndarray  # LEFT or RIGHT, looking along the edge from A to B
    distances: np.ndarray
    along: np.ndarray  # the nearest point of the curve, counted from A
    length: int  # the points of the curve, about a pixel apart
    width_px: float

    def pieces(self, samples: int) -> list["Band"]:
        """The band cut into pieces along the edge, each as long as this many points of the curve;
        the last one takes what is left, so no piece is too short to tell a line from a speck."""
        numbers = np.minimum(self.along // samples, max(0, self.length // samples - 1))
        return [
            Band(
                self.rows[part],
                self.columns[part],
                self.sides[part],
                self.distances[part],
                self.along[part],
                samples if number < numbers.max() else self.length - number * samples,
                self.width_px,
            )
            for number in np.unique(numbers)
            for part in [numbers == number]
        ]

    def colour_beyond(self, side: int, current: np.ndarray) -> int:
        """The most common colour on one side, just beyond the band, where the edge does not reach.

        If nothing lies beyond it, the side is between two parts of the edge, drawn either side of
        a line: then it is the line, the most common colour in the band other than background."""
        on_side = self.sides == side
        away = on_side & (self.distances > self.width_px)
        beyond = current[self.rows[away], self.columns[away]]
        within = current[self.rows[on_side], self.columns[on_side]]
        for values in (beyond[beyond != DRAWN], within[within >= 0]):
            if len(values):
                found, counts = np.unique(values, return_counts=True)
                return int(found[np.argmax(counts)])
        return OUTSIDE

    def unblended(
        self, side: int, colour: int, current: np.ndarray, blends: list[tuple[int, int, int]]
    ) -> int:
        """The colour, or if it is a blend of colours that lie on this side too, the most common of those."""
        on_side = self.sides == side
        found, counts = np.unique(current[self.rows[on_side], self.columns[on_side]], return_counts=True)
        amounts = dict(zip(found.tolist(), counts.tolist(), strict=True))
        parents = [
            parent for blend, *pair in blends if blend == colour for parent in pair if parent in amounts
        ]
        return max(parents, key=amounts.__getitem__, default=colour)

    def colour_here(self, side: int, current: np.ndarray, everywhere: int) -> int:
        """The colour beyond the band if the band agrees, else the colour beyond the whole edge
        if the band has it; see _side_colours."""
        local = self.colour_beyond(side, current)
        if local == self.colour_within(side, current, DRAWN):
            return local
        near = (self.sides == side) & (self.distances <= self.width_px)
        return everywhere if (current[self.rows[near], self.columns[near]] == everywhere).any() else local

    def colour_within(self, side: int, current: np.ndarray, besides: int) -> int:
        """The most common colour on one side within the band, other than the one given."""
        near = (self.sides == side) & (self.distances <= self.width_px)
        values = current[self.rows[near], self.columns[near]]
        values = values[(values != DRAWN) & (values != besides)]
        if not len(values):
            return besides
        found, counts = np.unique(values, return_counts=True)
        return int(found[np.argmax(counts)])

    def side_of_line(self, colour: int, current: np.ndarray) -> int | None:
        """The side a line of this colour runs along, within the band; none if it does not.

        A line lies along most of the edge, unlike a speck or the end of a stroke the edge only
        touches. An edge drawn on the line itself, along its border, has it on both sides: the
        line is on the side with more of it."""
        near = self.distances <= self.width_px
        found = near & (current[self.rows, self.columns] == colour)
        along = [len(np.unique(self.along[found & (self.sides == side)])) for side in (LEFT, RIGHT)]
        amounts = [np.count_nonzero(found & (self.sides == side)) for side in (LEFT, RIGHT)]
        lines = [
            side
            for side, reach in zip((LEFT, RIGHT), along, strict=True)
            if reach >= INK_LINE_SHARE * self.length
        ]
        if not lines:
            return None
        return max(lines, key=lambda side: amounts[(LEFT, RIGHT).index(side)])


def _without_overhang(labels: np.ndarray, inside: np.ndarray, drawn: np.ndarray, margin_px: float) -> None:
    """Pieces of any colour in the margin round the shapes that do not run on past the margin go
    to the nearest other colour that is not a shape, or the background."""
    current = np.where(inside, labels, OUTSIDE)
    margin = grown(drawn, margin_px) & ~drawn
    for index in np.unique(labels[margin & inside]):
        coloured = (current == index) & ~drawn
        pieces, _ = ndimage.label(coloured & margin)
        running_on = np.unique(pieces[ndimage.binary_dilation(coloured & ~margin)])
        overhang = (pieces > 0) & ~np.isin(pieces, running_on)
        if not overhang.any():
            continue
        _, (rows, columns) = ndimage.distance_transform_edt(coloured | drawn, return_indices=True)
        current[overhang] = current[rows[overhang], columns[overhang]]
    changed = current != np.where(inside, labels, OUTSIDE)
    labels[changed & (current != OUTSIDE)] = current[changed & (current != OUTSIDE)]
    inside[changed] = current[changed] != OUTSIDE


def _span(four: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Uniform Catmull-Rom between the middle two of four points."""
    p0, p1, p2, p3 = four
    return 0.5 * (
        2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t**2 + (3 * p1 - p0 - 3 * p2 + p3) * t**3
    )


def _band(curve: np.ndarray, shape: tuple[int, int], band_px: float) -> Band:
    """The pixels along the curve, out to where the sides' colours are read. Those beyond its two
    ends are left out, so the edge does not round off at its ends."""
    reach_px = SIDE_REACH * band_px
    rows, columns = _around(curve, shape, reach_px)
    pixels = np.column_stack([columns, rows]).astype(float)
    dense = _resampled(curve, SAMPLE_PX)
    distances, nearest = cKDTree(dense).query(pixels, distance_upper_bound=reach_px)
    close = distances <= reach_px
    rows, columns, pixels, distances, nearest = (
        rows[close],
        columns[close],
        pixels[close],
        distances[close],
        nearest[close],
    )
    tangents = np.gradient(dense, axis=0)
    offsets = pixels - dense[nearest]
    cross = tangents[nearest, 0] * offsets[:, 1] - tangents[nearest, 1] * offsets[:, 0]
    along = np.einsum("pk,pk->p", tangents[nearest], offsets)
    beyond_ends = ((nearest == 0) & (along < 0)) | ((nearest == len(dense) - 1) & (along > 0))
    keep = ~beyond_ends
    sides = np.where(cross[keep] < 0, LEFT, RIGHT)
    return Band(rows[keep], columns[keep], sides, distances[keep], nearest[keep], len(dense), band_px)


def _around(curve: np.ndarray, shape: tuple[int, int], margin_px: float) -> tuple[np.ndarray, np.ndarray]:
    """Rows and columns of every pixel in the curve's bounding box, widened by the margin. A wide
    line drawn by PIL would be quicker, but it leaves holes where the curve bends."""
    low = np.maximum(np.floor(curve.min(axis=0) - margin_px), 0).astype(int)
    high = np.minimum(np.ceil(curve.max(axis=0) + margin_px), [shape[1] - 1, shape[0] - 1]).astype(int)
    columns, rows = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
    return rows.ravel(), columns.ravel()


def _resampled(curve: np.ndarray, spacing_px: float) -> np.ndarray:
    """The curve with a point about every spacing, so the nearest point is close to the nearest spot."""
    steps = np.linalg.norm(np.diff(curve, axis=0), axis=1)
    along = np.concatenate([[0], np.cumsum(steps)])
    wanted = np.linspace(0, along[-1], max(2, int(along[-1] / spacing_px) + 1))
    return np.column_stack([np.interp(wanted, along, curve[:, axis]) for axis in range(2)])


def _nearest_index(hex_code: str, palette: list[Colour]) -> int:
    rgb = np.array([int(hex_code[i : i + 2], 16) for i in (1, 3, 5)])
    return int(np.argmin([np.linalg.norm(rgb - np.array(colour.rgb)) for colour in palette]))


def _enlarged(curve: np.ndarray, factor: int) -> np.ndarray:
    """The middle of the original pixels, in the enlarged picture."""
    return (curve + 0.5) * factor - 0.5


def _polygon_mask(shape: tuple[int, int], points: np.ndarray) -> np.ndarray:
    canvas = Image.new("1", (shape[1], shape[0]))
    ImageDraw.Draw(canvas).polygon([tuple(point) for point in points], fill=1)
    return np.asarray(canvas)
