// Shapes on the background and keep mask (shapekinds.js). A spline: click points round an area
// and the first point again to close it. A circle: from its centre out; a rectangle: corner to
// corner, each by dragging or by two clicks. The shapes stay editable: drag a handle to change
// one, click its outline to choose it and type its sizes, or press Delete with the pointer on it
// to take it off. Their outlines show while the mask's tools are in hand; what they mark shows
// in the mask itself (maskhistory.js).

import { distanceToCurve, insideCurve } from "./closedcurve.js";
import { spline } from "./handdrawn.js";
import { shapeGuide, SMALLEST } from "./shapeguide.js";
import { dragged, handles, outline } from "./shapekinds.js";

const LINE_SCREEN_PX = 2;
const DASH_SCREEN_PX = [6, 4];
const POINT_SCREEN_PX = 3;
const HANDLE_SCREEN_PX = 5;
const REACH_SCREEN_PX = 8; // a click this close to a point or a line takes hold of it
const OUTLINE = "#1d1d1b";
const CHOSEN = "#00a3e0";
const HANDLE_FILL = "#ffffff";

export class MaskShapes {
  /** history: the mask's steps, of which the shapes are the ones that are not strokes; onChoose
   * hears the shape chosen, or null. */
  constructor(canvas, canvasPxPerScreenPx, history, onChoose) {
    this.canvas = canvas;
    this.scale = canvasPxPerScreenPx;
    this.history = history;
    this.onChoose = onChoose;
    this.shown = false; // while the mask's tools are in hand
    this.drawing = null; // { kind: "spline", points } or { kind: "circle" or "rect", from, to }
    this.pointer = null;
    this.held = null; // the handle being dragged
    this.chosen = null; // the shape whose sizes show
  }

  /** What to do next, said plainly: the page shows it above the picture. */
  guide(action, method) {
    return shapeGuide(this.drawing, action, method);
  }

  /** True while the pointer should stay with the picture: dragging a handle or a new shape. */
  get holding() {
    return Boolean(this.held || (this.drawing && !this.drawing.points));
  }

  show(shown) {
    this.shown = shown;
    if (!shown) this.cancel();
    this.draw();
  }

  /** Takes hold of a handle, chooses the shape clicked on, or draws; true when a shape was added. */
  down(point, action, method) {
    const at = [point.x, point.y];
    if (this.drawing?.points) return this.#splineClick(at, action);
    if (this.drawing) return this.#finish(action);
    this.held = this.#handleNear(at);
    const clicked = this.held?.step ?? this.#outlineNear(at);
    if (clicked) this.choose(clicked);
    else this.drawing = method === "spline" ? { kind: "spline", points: [at] } : { kind: method, from: at, to: at };
    this.draw();
    return false;
  }

  move(point) {
    this.pointer = point && [point.x, point.y];
    if (this.held && point) {
      this.held.drag(this.pointer);
      this.history.draw();
      this.onChoose(this.chosen);
    }
    if (this.drawing && !this.drawing.points && point) this.drawing.to = this.pointer;
    if (this.drawing || this.held) this.draw();
  }

  /** Lets go: of a handle, or of a shape dragged out; true when the mask changed. */
  up(action) {
    const moved = Boolean(this.held);
    this.held = null;
    const { from, to } = this.drawing ?? {};
    if (from && apart(from, to) > this.#reach()) return this.#finish(action);
    return moved;
  }

  /** Takes off the shape under the pointer; true when there was one. */
  removeUnderPointer() {
    const step = this.pointer && this.#shapes().findLast((shape) => insideCurve(outline(shape), this.pointer));
    if (step) this.history.remove(step);
    if (step === this.chosen) this.choose(null);
    this.draw();
    return Boolean(step);
  }

  cancel() {
    this.drawing = null;
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
    context.setLineDash(DASH_SCREEN_PX.map((length) => length * scale));
    for (const shape of this.#shapes()) stroke(context, outline(shape), shape === this.chosen ? CHOSEN : OUTLINE, true);
    if (this.drawing) stroke(context, this.#drawn(), OUTLINE, !this.drawing.points);
    context.setLineDash([]);
    for (const [x, y] of this.drawing?.points ?? []) circle(context, x, y, POINT_SCREEN_PX * scale, OUTLINE);
    if (this.drawing) return;
    for (const { at: [x, y] } of this.#shapes().flatMap(handles)) circle(context, x, y, HANDLE_SCREEN_PX * scale, HANDLE_FILL, OUTLINE);
  }

  /** The shape being drawn as it is so far: a spline runs on to the pointer. */
  #drawn() {
    const { kind, points, from, to } = this.drawing;
    if (points) return spline([...points, ...(this.pointer ? [this.pointer] : [])], false);
    return outline(dragged(kind, from, to));
  }

  #splineClick(at, action) {
    const { points } = this.drawing;
    if (points.length >= SMALLEST && apart(points[0], at) <= this.#reach()) return this.#add({ action, spline: points });
    points.push(at);
    this.draw();
    return false;
  }

  #finish(action) {
    const { kind, from, to } = this.drawing;
    return this.#add({ action, ...dragged(kind, from, to) });
  }

  #add(step) {
    this.history.add(step);
    this.drawing = null;
    this.choose(step);
    this.draw();
    return true;
  }

  /** The shape whose sizes show, or null for none. */
  choose(step) {
    this.chosen = step;
    this.onChoose(step);
  }

  #shapes() {
    return this.history.steps.filter((step) => !step.stroke);
  }

  /** The handle nearest the point, within reach, with the shape it belongs to; null if none is. */
  #handleNear(at) {
    const all = this.#shapes().flatMap((step) => handles(step).map((handle) => ({ ...handle, step })));
    const within = all.filter((handle) => apart(handle.at, at) <= this.#reach());
    return within.reduce((best, handle) => (best && apart(best.at, at) <= apart(handle.at, at) ? best : handle), null);
  }

  #outlineNear(at) {
    return this.#shapes().findLast((step) => distanceToCurve(outline(step), at) <= this.#reach()) ?? null;
  }

  #reach() {
    return REACH_SCREEN_PX * this.scale();
  }
}

function stroke(context, samples, colour, closed) {
  context.strokeStyle = colour;
  context.beginPath();
  samples.forEach(([x, y], index) => (index ? context.lineTo(x, y) : context.moveTo(x, y)));
  if (closed) context.closePath();
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
