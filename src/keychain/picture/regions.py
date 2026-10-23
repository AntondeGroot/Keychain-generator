"""From a picture to a map of filament colours, cleaned up so every area can be printed."""

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.morphology import skeletonize

from keychain.picture.blends import without_edge_blends
from keychain.picture.connections import with_connections
from keychain.picture.handdrawn import with_curves
from keychain.picture.masks import closed, grown, opened
from keychain.picture.nearest import darkest, nearest_colours
from keychain.picture.painted import DetailMask, Painting
from keychain.picture.palette import Colour
from keychain.spec import KeychainSpec

OUTSIDE = -1
TARGET_MM_PER_PX = 0.025  # fine enough that the traced edges show no pixel steps
OPAQUE = 128  # alpha from which a pixel belongs to the picture
SPECK_DOT_LINES = 1.5  # a piece smaller than a dot this many lines across is a speck, not a detail
STRIP_LINES = 2  # a narrow part covering a square this many lines wide is a strip, not a tip


@dataclass(frozen=True)
class ColourMap:
    labels: np.ndarray  # palette index per pixel, OUTSIDE around the picture
    mm_per_px: float
    ink: int  # palette index of the lines, which also colours the rim and the core
    factor: int  # how many times the picture was enlarged
    detail: DetailMask  # in the picture's own pixels

    @property
    def inside(self) -> np.ndarray:
        return self.labels != OUTSIDE

    def tolerances_mm(self, rows: np.ndarray, columns: np.ndarray, tolerance_mm: float) -> np.ndarray:
        """The curve tolerance at these pixels of the map, after the painted detail areas."""
        return self.detail.tolerances(rows // self.factor, columns // self.factor, tolerance_mm)

    @property
    def widest_mm(self) -> float:
        """The widest side of the picture as printed."""
        return max(_size_px(self.inside)) * self.mm_per_px


def colour_map(
    image: Image.Image, palette: list[Colour], spec: KeychainSpec, painting: Painting | None = None
) -> ColourMap:
    """The picture enlarged until a pixel is about 0.025 mm, with one palette colour per pixel."""
    painting = painting or Painting.nothing_painted(image.size)
    image = painting.colours.over(image)
    factor, rough_mm_per_px = _enlargement(image, palette, spec, painting)
    big = _rgba(image.resize((image.width * factor, image.height * factor), Image.Resampling.BICUBIC))
    labels = nearest_colours(big[..., :3], palette, spec.smoothing_mm / rough_mm_per_px)
    inside = _inside(labels, big, painting, factor, spec, rough_mm_per_px)
    ink = darkest(palette)
    labels, inside, drawn = _hand_drawn(labels, inside, painting, palette, factor, rough_mm_per_px)
    # Closing gaps can make the picture a little larger, so the exact scale is measured after.
    mm_per_px = spec.mm_per_px(*_size_px(inside))
    line_radius_px = spec.min_line_mm / 2 / mm_per_px
    labels = without_edge_blends(labels, inside, palette, line_radius_px)
    labels, inside = with_connections(
        labels, inside, painting.drawing.connections, factor, ink, 2 * line_radius_px
    )
    inside &= ~painting.mask.enlarged(factor).background  # a line drawn across it does not bring it back
    labels = _with_printable_areas(labels, inside & ~drawn, ink, line_radius_px)
    return ColourMap(np.where(inside, labels, OUTSIDE), mm_per_px, ink, factor, painting.detail)


def _hand_drawn(
    labels: np.ndarray,
    inside: np.ndarray,
    painting: Painting,
    palette: list[Colour],
    factor: int,
    mm_per_px: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Curves drawn by hand say exactly where things are, so they come before any clean-up, and
    the clean-up leaves the drawn shapes as they are. Painted background is surely not the
    keychain, so it stays out even where a shape is drawn across it, such as all round a cut."""
    labels, inside, drawn = with_curves(labels, inside, painting.drawing, palette, factor, mm_per_px)
    return labels, inside & ~painting.mask.enlarged(factor).background, drawn


def _enlargement(
    image: Image.Image, palette: list[Colour], spec: KeychainSpec, painting: Painting
) -> tuple[int, float]:
    """How many times to enlarge the picture, and roughly how many mm a pixel then is."""
    small = _rgba(image)
    labels = nearest_colours(small[..., :3], palette)
    kept = painting.mask.applied(_drawn(labels, small, _background(labels, small)))
    mm_per_px = spec.mm_per_px(*_size_px(kept))
    factor = max(1, math.ceil(mm_per_px / TARGET_MM_PER_PX))
    return factor, mm_per_px / factor


def _inside(
    labels: np.ndarray,
    rgba: np.ndarray,
    painting: Painting,
    factor: int,
    spec: KeychainSpec,
    mm_per_px: float,
) -> np.ndarray:
    """The pixels of the picture, as opposed to the background around it, which gets the rim.

    Painted background comes off only after finding what the drawing encloses: a stroke
    through an outline would otherwise open it, and the whole inside would count as outside."""
    mask = painting.mask.enlarged(factor)
    background = _background(labels, rgba)
    drawn = _drawn(labels, rgba, background) | mask.keep | painting.colours.painted_enlarged(factor)
    inside = _picture_area(drawn, spec.gap_mm / 2 / mm_per_px) & ~mask.background
    line_radius_px = spec.min_line_mm / 2 / mm_per_px
    if background is None:
        return inside & ~_see_through(inside & ~drawn, inside, line_radius_px)
    return inside & ~_outer_notches((labels == background) & inside, inside, line_radius_px)


def _rgba(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGBA"), dtype=float)


def _background(labels: np.ndarray, rgba: np.ndarray) -> int | None:
    """The palette colour of the background, the most common along the border; none if the
    picture has a transparent background instead."""
    if not (rgba[..., 3] >= OPAQUE).all():
        return None
    border = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    return int(np.bincount(border).argmax())


def _drawn(labels: np.ndarray, rgba: np.ndarray, background: int | None) -> np.ndarray:
    """The pixels that are not background: opaque ones, or else those unlike the background."""
    if background is None:
        return rgba[..., 3] >= OPAQUE
    return labels != background


def _size_px(mask: np.ndarray) -> tuple[int, int]:
    """The width and height of what the mask covers."""
    rows, columns = np.nonzero(mask)
    if not len(rows):
        raise ValueError("the picture is empty: every pixel looks like the background")
    return int(np.ptp(columns)) + 1, int(np.ptp(rows)) + 1


def _picture_area(drawn: np.ndarray, gap_radius_px: float) -> np.ndarray:
    """The drawing with small openings in its outer line closed, so white parts inside stay in,
    such as a white dog whose outline has gaps between the tufts of fur."""
    return ndimage.binary_fill_holes(closed(drawn, gap_radius_px))


def _outer_notches(background: np.ndarray, inside: np.ndarray, radius_px: float) -> np.ndarray:
    """Background in narrow notches along the outside, such as between the tips of hair strands.

    Closing the openings in the outline also fills these, but they are background, not part of
    the picture: kept in, they are too narrow to print and the strands would merge."""
    pieces, wide, touching_outside = _background_pieces(background, inside, radius_px)
    return np.isin(pieces, np.setdiff1d(touching_outside, wide)) & (pieces > 0)


def _see_through(see_through: np.ndarray, inside: np.ndarray, radius_px: float) -> np.ndarray:
    """In a picture with a transparent background, the see-through parts that closing the
    outline took in: in notches along the outside, such as between whiskers, and areas closed
    off, such as between a dog's legs. They are no part of the picture, so the rim comes there,
    in its own colour; kept in, they took the colour hidden under the transparent pixels, often
    black. Only pinholes stay, too narrow for a rim to fit in."""
    pieces, wide, touching_outside = _background_pieces(see_through, inside, radius_px)
    return np.isin(pieces, np.union1d(touching_outside, wide)) & (pieces > 0)


def _background_pieces(area: np.ndarray, inside: np.ndarray, radius_px: float):
    """The connected pieces of background inside the picture, the ones wider than a line, and
    the ones touching the outside."""
    pieces, _ = ndimage.label(area)
    wide = np.unique(pieces[opened(area, radius_px)])
    touching_outside = np.unique(pieces[area & grown(~inside, 1)])
    return pieces, wide, touching_outside


def _with_printable_areas(labels: np.ndarray, inside: np.ndarray, ink: int, radius_px: float) -> np.ndarray:
    """Every colour area at least a printed line wide, the way one would fix it by hand.

    Specks, and colour areas that are narrow everywhere (blends along an edge, such as a
    skin-coloured fringe where orange hair fades into white), go to the colours around them.
    Narrow strips of an area that is wide elsewhere, such as hair along a hairline, are
    thickened instead of lost. A colour never grows over ink, so the lines stay whole."""
    labels = labels.copy()
    colours = sorted(set(np.unique(labels[inside]).tolist()) - {ink})
    for index in [ink, *colours]:
        area = (labels == index) & inside
        pieces, _ = ndimage.label(area)
        wide = np.isin(pieces, np.unique(pieces[opened(area, radius_px)]))
        loose = _specks(pieces, radius_px) | (area & ~wide if index != ink else False)
        _give_to_neighbours(labels, loose, inside)
        strips = _strips(area & ~loose & ~opened(area, radius_px), radius_px)
        may_take = inside if index == ink else inside & (labels != ink)
        labels[_widened(strips, area, radius_px) & may_take] = index
    return labels


def _specks(pieces: np.ndarray, radius_px: float) -> np.ndarray:
    """Pieces smaller than a printable dot."""
    sizes = np.bincount(pieces.ravel())
    too_small = np.nonzero(sizes < math.pi * (SPECK_DOT_LINES * radius_px) ** 2)[0]
    return np.isin(pieces, too_small) & (pieces > 0)


def _strips(narrow: np.ndarray, radius_px: float) -> np.ndarray:
    """Narrow parts long enough to be a strip, not the tip of a line or a sharp corner."""
    pieces, _ = ndimage.label(narrow)
    sizes = np.bincount(pieces.ravel())
    long_enough = np.nonzero(sizes >= (STRIP_LINES * 2 * radius_px) ** 2)[0]
    return np.isin(pieces, long_enough) & (pieces > 0)


def _widened(strips: np.ndarray, area: np.ndarray, radius_px: float) -> np.ndarray:
    """Each strip widened by what it lacks of a printed line, so that all come out a line wide.

    Widening by a whole line instead would make a strip just under a line nearly twice as wide
    as one just over it: lines drawn about as wide as each other would print unevenly."""
    pieces, count = ndimage.label(strips)
    if not count:
        return strips
    # Halfway across a strip, the distance to the first pixel beyond its edge is half its width,
    # plus half a pixel.
    middle = skeletonize(strips)
    depth = ndimage.distance_transform_edt(area)
    half_widths = np.asarray(ndimage.median(depth, np.where(middle, pieces, 0), range(1, count + 1))) - 0.5
    lacking_px = np.ceil(np.maximum(radius_px - half_widths, 0))
    widened = strips.copy()
    for distance_px in np.unique(lacking_px):
        widened |= grown(np.isin(pieces, np.flatnonzero(lacking_px == distance_px) + 1), distance_px)
    return widened


def _give_to_neighbours(labels: np.ndarray, loose: np.ndarray, inside: np.ndarray) -> None:
    """Each loose pixel takes the colour of the nearest pixel that is not loose."""
    keeping = inside & ~loose
    if not loose.any() or not keeping.any():
        return
    _, (rows, columns) = ndimage.distance_transform_edt(~keeping, return_indices=True)
    labels[loose] = labels[rows[loose], columns[loose]]
