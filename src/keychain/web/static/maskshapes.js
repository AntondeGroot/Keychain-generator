// Shapes on the background and keep mask, drawn as splines: click points round an area and the
// first point again to close it. The shapes stay editable: drag a point to move it, or press
// Delete with the pointer on a shape to take it off. Their outlines show while the mask's tools
// are in hand; what they mark shows in the mask itself (maskhistory.js).

import { insideCurve } from "./closedcurve.js";
import { spline } from "./handdrawn.js";

const LINE_SCREEN_PX = 2;
const DASH_SCREEN_PX = [6, 4];
const POINT_SCREEN_PX = 3;
const HANDLE_SCREEN_PX = 5;
const REACH_SCREEN_PX = 8; // a click this close to a point closes the shape or takes hold of it
const SMALLEST = 3; // points a shape needs before it can be closed
const OUTLINE = "#1d1d1b";
const HANDLE_FILL = "#ffffff";

export class MaskShapes {
  /** history: the mask's steps, of which the shapes are the ones with a spline. */
  constructor(canvas, canvasPxPerScreenPx, history) {
    this.canvas = canvas;
    this.scale = canvasPxPerScreenPx;
    this.history = history;
    this.shown = false; // while the mask's tools are in hand
    this.current = null; // the points of the shape being drawn
    this.pointer = null;
    this.held = null; // the point being dragged
  }

  guide(action) {
    const marking = { background: "background", keep: "keep", erase: "erased" }[action];
    const start = `Shape: click points round an area to make it ${marking}.`;
    if (!this.current) return `${start} Drag a point to move it; Delete takes off the shape under the pointer.`;
    if (this.current.length < SMALLEST) return "Shape: keep clicking round the area. Esc cancels.";
    return "Shape: click the first point again to close it. Esc cancels.";
  }

  show(shown) {
    this.shown = shown;
    if (!shown) this.cancel();
    this.draw();
  }

  /** Takes hold of a shape's point, or adds a point; true when a shape was closed. */
  down(point, action) {
    const at = [point.x, point.y];
    this.held = this.current ? null : this.#nearestPoint(at);
    if (this.held) return false;
    if (!this.current) {
      this.current = [at];
    } else if (this.current.length >= SMALLEST && apart(this.current[0], at) <= this.#reach()) {
      this.history.add({ action, spline: this.current });
      this.current = null;
    } else {
      this.current.push(at);
    }
    this.draw();
    return this.current === null;
  }

  move(point) {
    this.pointer = point && [point.x, point.y];
    if (this.held && point) {
      [this.held[0], this.held[1]] = this.pointer;
      this.history.draw();
    }
    if (this.current || this.held) this.draw();
  }

  /** Lets go of a point; true when one was moved. */
  up() {
    const moved = Boolean(this.held);
    this.held = null;
    return moved;
  }

  /** Takes off the shape under the pointer; true when there was one. */
  removeUnderPointer() {
    const step = this.pointer && this.#shapes().find(({ spline: points }) => insideCurve(spline(points, true), this.pointer));
    if (step) this.history.remove(step);
    this.draw();
    return Boolean(step);
  }

  cancel() {
    this.current = null;
    this.held = null;
    this.draw();
  }

  draw() {
    const context = this.canvas.getContext("2d");
    const scale = this.scale();
    const toPicture = context.getTransform(); // the canvas can be sharper than the picture
    context.resetTransform();
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    context.setTransform(toPicture);
    if (!this.shown) return;
    context.lineWidth = LINE_SCREEN_PX * scale;
    context.strokeStyle = OUTLINE;
    context.setLineDash(DASH_SCREEN_PX.map((length) => length * scale));
    for (const { spline: points } of this.#shapes()) stroke(context, spline(points, true));
    if (this.current) stroke(context, spline([...this.current, ...(this.pointer ? [this.pointer] : [])], false));
    context.setLineDash([]);
    for (const [x, y] of this.current ?? []) circle(context, x, y, POINT_SCREEN_PX * scale, OUTLINE);
    if (this.current) return;
    for (const { spline: points } of this.#shapes()) {
      for (const [x, y] of points) circle(context, x, y, HANDLE_SCREEN_PX * scale, HANDLE_FILL, OUTLINE);
    }
  }

  #shapes() {
    return this.history.steps.filter((step) => step.spline);
  }

  #nearestPoint(at) {
    const points = this.#shapes().flatMap(({ spline: points }) => points);
    const within = points.filter((point) => apart(point, at) <= this.#reach());
    return within.reduce((best, point) => (best && apart(best, at) <= apart(point, at) ? best : point), null);
  }

  #reach() {
    return REACH_SCREEN_PX * this.scale();
  }
}

function stroke(context, samples) {
  context.beginPath();
  samples.forEach(([x, y], index) => (index ? context.lineTo(x, y) : context.moveTo(x, y)));
  context.stroke();
}

function circle(context, x, y, radius, fill, outline = null) {
  context.fillStyle = fill;
  context.beginPath();
  context.arc(x, y, radius, 0, 2 * Math.PI);
  context.fill();
  if (!outline) return;
  context.strokeStyle = outline;
  context.stroke();
}

function apart([x1, y1], [x2, y2]) {
  return Math.hypot(x1 - x2, y1 - y2);
}
