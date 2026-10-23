// What to do next with the mask's shapes, said plainly: the page shows it above the picture.

export const SMALLEST = 3; // points a spline needs before it can be closed

const MARKING = { background: "background", keep: "keep", erase: "erased", cut: "the keychain's outline" };
const STARTS = {
  spline: "Spline: click points round an area",
  circle: "Circle: press at the centre and drag out",
  rect: "Rectangle: press at a corner and drag to the opposite one",
};
const FILLET =
  "Fillet: click rectangle corners to round them by the radius below, or a rectangle's outline for all four; click a chosen corner again to leave it out. A radius typed rounds all the corners chosen.";
const EDITING = "Click a shape's outline to type its sizes, drag its handles to change it; Delete takes off the shape under the pointer.";
const DIMENSION =
  "Dimension: click a circle for its diameter, or a rectangle's edge for its width or height, and type the size in mm. A dimensioned size stays while the handles are dragged; click a value to change it, Delete on it takes it off.";
const DRAWING = {
  circle: "Circle: let go, or click, where the rim goes. Esc cancels.",
  rect: "Rectangle: let go, or click, where the opposite corner goes. Esc cancels.",
};

/** drawing: the shape being drawn, as maskshapes.js keeps it, or null. */
export function shapeGuide(drawing, action, method) {
  const points = drawing?.points;
  if (drawing && !points) return DRAWING[drawing.kind];
  if (points?.length >= SMALLEST) return "Spline: click the first point again to close it. Esc cancels.";
  if (points) return "Spline: keep clicking round the area. Esc cancels.";
  if (method === "fillet") return FILLET;
  if (method === "dimension") return DIMENSION;
  return `${STARTS[method]} to make it ${MARKING[action]}. ${EDITING}`;
}
