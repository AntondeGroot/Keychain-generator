// What the pointer is on among the mask's shapes, the topmost first: a handle to drag, a shape's
// outline, a rectangle's corner, an edge to dimension, or the inside of a shape. Points and reach
// are in picture pixels.

import { distanceToCurve, insideCurve } from "./closedcurve.js";
import { cornerAt, handles, outline } from "./shapekinds.js";

const CORNERS = [0, 1, 2, 3]; // top left, top right, bottom right, bottom left

/** The handle nearest the point, within reach, with the shape it belongs to; null if none is. */
export function handleNear(steps, at, reach) {
  const all = steps.flatMap((step) => handles(step).map((handle) => ({ ...handle, step })));
  return nearest(all, (handle) => handle.at, at, reach);
}

/** The shape whose outline runs within reach of the point; null if none does. */
export function outlineNear(steps, at, reach) {
  return steps.findLast((step) => distanceToCurve(outline(step), at) <= reach) ?? null;
}

/** The shape the point is inside; null if none. */
export function shapeUnder(steps, at) {
  return steps.findLast((step) => insideCurve(outline(step), at)) ?? null;
}

/** The rectangle corner nearest the point, within reach, as { step, corner }; null if none is. */
export function cornerNear(steps, at, reach) {
  const all = steps.filter((step) => step.rect).flatMap((step) => CORNERS.map((corner) => ({ step, corner })));
  const hit = nearest(all, ({ step, corner }) => cornerAt(step, corner), at, reach);
  return hit && { step: hit.step, corner: hit.corner };
}

/** The size the edge within reach of the point gives, as { step, name }: a circle's rim its
 * diameter, a rectangle's top or bottom its width, either side its height; null if none is near. */
export function edgeNear(steps, at, reach) {
  for (const step of [...steps].reverse()) {
    if (step.circle && distanceToCurve(outline(step), at) <= reach) return { step, name: "diameter" };
    if (!step.rect) continue;
    const [topLeft, topRight, bottomRight, bottomLeft] = CORNERS.map((corner) => cornerAt(step, corner));
    const near = (...edges) => edges.some((edge) => distanceToCurve(edge, at) <= reach);
    if (near([topLeft, topRight], [bottomLeft, bottomRight])) return { step, name: "width" };
    if (near([topLeft, bottomLeft], [topRight, bottomRight])) return { step, name: "height" };
  }
  return null;
}

function nearest(items, pointOf, at, reach) {
  const within = items.filter((item) => apart(pointOf(item), at) <= reach);
  return within.reduce((best, item) => (best && apart(pointOf(best), at) <= apart(pointOf(item), at) ? best : item), null);
}

function apart([x1, y1], [x2, y2]) {
  return Math.hypot(x1 - x2, y1 - y2);
}
