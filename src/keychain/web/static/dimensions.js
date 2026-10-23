// Dimensions on the mask's shapes, as in a CAD sketch: a circle's diameter, a rectangle's width
// or height, each a line along the size with its value in mm. A shape keeps the names of its
// dimensions in dims; a dimensioned size stays as it is while its handles are dragged
// (shapekinds.js), and typing a value changes it. Points are in picture pixels.

import { sizesOf } from "./shapekinds.js";

const OFFSET_SCREEN_PX = 14; // how far a dimension line stands off the shape
const TICK_SCREEN_PX = 5;
const FONT_SCREEN_PX = 12;
const LABEL_REACH_SCREEN_PX = 16; // a click this close to a label is on it
const COLOUR = "#0b5cad";
const HALO = "#ffffff";
const DECIMALS = 1;

/** The dimensions of the shapes, each { step, name }. */
export function dimensionsOf(steps) {
  return steps.flatMap((step) => (step.dims ?? []).map((name) => ({ step, name })));
}

/** Where the dimension's line runs and its value shows: { from, to, label }. */
export function dimensionLine({ step, name }, scale) {
  const offset = OFFSET_SCREEN_PX * scale;
  if (name === "diameter") {
    const { centre: [x, y], radius } = step.circle;
    return { from: [x - radius, y], to: [x + radius, y], label: [x, y - radius - offset] };
  }
  const { x, y, width, height } = step.rect;
  if (name === "width") return { from: [x, y - offset], to: [x + width, y - offset], label: [x + width / 2, y - 2 * offset] };
  return { from: [x + width + offset, y], to: [x + width + offset, y + height], label: [x + width + 2.5 * offset, y + height / 2] };
}

/** The dimension whose label is under the point; null if none is. */
export function labelNear(steps, at, scale) {
  const reach = LABEL_REACH_SCREEN_PX * scale;
  return dimensionsOf(steps).find((dimension) => apart(dimensionLine(dimension, scale).label, at) <= reach) ?? null;
}

/** The value as the label shows it and the box to type it in starts with. */
export function inMm(dimension, pixelMm) {
  return (sizesOf(dimension.step)[dimension.name] * pixelMm).toFixed(DECIMALS);
}

export function drawDimensions(context, steps, pixelMm, scale) {
  context.font = `${FONT_SCREEN_PX * scale}px system-ui, sans-serif`;
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.lineWidth = scale;
  for (const dimension of dimensionsOf(steps)) {
    const { from, to, label } = dimensionLine(dimension, scale);
    const text = (dimension.name === "diameter" ? "Ø " : "") + inMm(dimension, pixelMm);
    context.strokeStyle = context.fillStyle = COLOUR;
    line(context, from, to);
    for (const end of [from, to]) tick(context, end, from, to, TICK_SCREEN_PX * scale);
    context.lineWidth = 3 * scale;
    context.strokeStyle = HALO;
    context.strokeText(text, ...label);
    context.fillText(text, ...label);
    context.lineWidth = scale;
  }
}

function line(context, [x1, y1], [x2, y2]) {
  context.beginPath();
  context.moveTo(x1, y1);
  context.lineTo(x2, y2);
  context.stroke();
}

/** A short stroke across the line at its end. */
function tick(context, [x, y], [x1, y1], [x2, y2], length) {
  const along = Math.hypot(x2 - x1, y2 - y1) || 1;
  const [across, down] = [(y1 - y2) / along, (x2 - x1) / along];
  line(context, [x - across * length, y - down * length], [x + across * length, y + down * length]);
}

function apart([x1, y1], [x2, y2]) {
  return Math.hypot(x1 - x2, y1 - y2);
}
