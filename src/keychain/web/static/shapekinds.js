// The shapes that mark the mask, in picture pixels: a spline through clicked points, a circle
// round a centre, or a rectangle with rounded corners. Each gives its outline as samples, to fill
// and to draw, the handles that change it when dragged, and its sizes to type exactly.

import { spline } from "./handdrawn.js";

const CIRCLE_SAMPLES = 128;
const CORNER_SAMPLES = 16;
const CORNER_ANGLES = [Math.PI, 1.5 * Math.PI, 0, 0.5 * Math.PI]; // where each corner's arc starts, clockwise from the top left

/** A circle round from, or a rectangle with its corners at from and to: drawn by dragging. */
export function dragged(kind, from, to) {
  if (kind === "circle") return { circle: { centre: from, radius: apart(from, to) } };
  return { rect: { ...between(from, to), radii: [0, 0, 0, 0] } };
}

export function outline(step) {
  if (step.spline) return spline(step.spline, true);
  if (step.circle) return circleOutline(step.circle);
  return rectOutline(step.rect);
}

/** The points to drag, each { at, drag(to) }: a spline's points; a circle's centre, to move it,
 * and a point on its rim, for its size; a rectangle's corners, each pulled from the opposite one,
 * and its centre, to move it. */
export function handles(step) {
  if (step.spline) return step.spline.map((point) => ({ at: point, drag: (to) => point.splice(0, 2, ...to) }));
  if (step.circle) return circleHandles(step.circle);
  return rectHandles(step.rect);
}

/** The sizes there are fields for: a circle's diameter; a rectangle's width, height and the
 * radius of its corners, null where they differ. None for a spline. */
export function sizesOf(step) {
  if (step.circle) return { diameter: 2 * step.circle.radius };
  if (!step.rect) return {};
  const { width, height } = step.rect;
  return { width, height, radius: sharedRadius([0, 1, 2, 3].map((corner) => ({ step, corner }))) };
}

/** The radius rectangle corners, each { step, corner }, have in common; null where they differ. */
export function sharedRadius(corners) {
  const radii = corners.map(({ step, corner }) => step.rect.radii[corner]);
  return radii.every((radius) => radius === radii[0]) ? radii[0] : null;
}

/** Sets one of the sizes, keeping the shape's centre where it is; a radius for the corner given,
 * or else for all four. */
export function resize(step, name, px, corner = null) {
  if (name === "diameter") step.circle.radius = px / 2;
  if (name === "radius") {
    const radius = Math.min(px, smallestRadius(step.rect));
    if (corner === null) step.rect.radii = Array(4).fill(radius);
    else step.rect.radii[corner] = radius;
  }
  if (name !== "width" && name !== "height") return;
  const rect = step.rect;
  const [x, y] = centreOf(rect);
  rect[name] = px;
  Object.assign(rect, { x: x - rect.width / 2, y: y - rect.height / 2 });
}

/** The rectangle corner nearest the point, within reach, as { step, corner }; null if none is. */
export function cornerNear(steps, at, reach) {
  const all = steps.filter((step) => step.rect).flatMap((step) => corners(step.rect).map((point, corner) => ({ step, corner, point })));
  const within = all.filter(({ point }) => apart(point, at) <= reach);
  return within.reduce((best, hit) => (best && apart(best.point, at) <= apart(hit.point, at) ? best : hit), null);
}

/** Where a rectangle's corner would be, were it not rounded. */
export function cornerAt(step, corner) {
  return corners(step.rect)[corner];
}

function circleOutline({ centre: [x, y], radius }) {
  return Array.from({ length: CIRCLE_SAMPLES }, (_, i) => {
    const angle = (2 * Math.PI * i) / CIRCLE_SAMPLES;
    return [x + radius * Math.cos(angle), y + radius * Math.sin(angle)];
  });
}

/** Round each corner, the radius no more than half the shorter side. */
function rectOutline(rect) {
  return corners(rect).flatMap(([x, y], i) => {
    const radius = Math.min(rect.radii[i], smallestRadius(rect));
    const [inwardX, inwardY] = [i === 0 || i === 3 ? 1 : -1, i < 2 ? 1 : -1];
    const [centreX, centreY] = [x + inwardX * radius, y + inwardY * radius];
    return Array.from({ length: CORNER_SAMPLES + 1 }, (_, step) => {
      const angle = CORNER_ANGLES[i] + (step / CORNER_SAMPLES) * (Math.PI / 2);
      return [centreX + radius * Math.cos(angle), centreY + radius * Math.sin(angle)];
    });
  });
}

function circleHandles(circle) {
  const [x, y] = circle.centre;
  return [
    { at: circle.centre, drag: (to) => (circle.centre = to) },
    { at: [x + circle.radius, y], drag: (to) => (circle.radius = apart(circle.centre, to)) },
  ];
}

function rectHandles(rect) {
  const all = corners(rect);
  const pulled = all.map((at, i) => ({ at, drag: (to) => Object.assign(rect, between(all[(i + 2) % 4], to)) }));
  const centre = centreOf(rect);
  const move = (to) => Object.assign(rect, { x: to[0] - rect.width / 2, y: to[1] - rect.height / 2 });
  return [...pulled, { at: centre, drag: move }];
}

/** Top left, top right, bottom right, bottom left: clockwise on the page, where y points down. */
function corners({ x, y, width, height }) {
  return [
    [x, y],
    [x + width, y],
    [x + width, y + height],
    [x, y + height],
  ];
}

function centreOf({ x, y, width, height }) {
  return [x + width / 2, y + height / 2];
}

function smallestRadius({ width, height }) {
  return Math.min(width, height) / 2;
}

function between([x1, y1], [x2, y2]) {
  return { x: Math.min(x1, x2), y: Math.min(y1, y2), width: Math.abs(x2 - x1), height: Math.abs(y2 - y1) };
}

function apart([x1, y1], [x2, y2]) {
  return Math.hypot(x1 - x2, y1 - y2);
}
