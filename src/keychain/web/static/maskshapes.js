// Shapes on the background and keep mask (shapekinds.js). A spline: click points round an area
// and the first point again to close it. A circle: from its centre out; a rectangle: corner to
// corner, each by dragging or by two clicks. The shapes stay editable: drag a handle to change
// one, click its outline to choose it and type its sizes, or press Delete with the pointer on it
// to take it off. With the fillet, a click on a rectangle's corner chooses it to round, or on its
// outline all four; the corners chosen are rounded all at once. With the dimension, a click on an
// edge or a dimension's value opens a box to type the size in (dimensions.js). The outlines show
// while the mask's tools are in hand; what the shapes mark shows in the mask (maskhistory.js).

import { dimensionLine, labelNear } from "./dimensions.js";
import { drawMaskShapes } from "./maskshapesdraw.js";
import { shapeGuide, SMALLEST } from "./shapeguide.js";
import { cornerNear, edgeNear, handleNear, outlineNear, shapeUnder } from "./shapehits.js";
import { dragged } from "./shapekinds.js";

const REACH_SCREEN_PX = 8; // a click this close to a point or a line takes hold of it

export class MaskShapes {
  /** history: the mask's steps, of which the shapes are the ones that are not strokes. on hears:
   * choose, the shape chosen, or null; fillet, the corners chosen with the fillet and those just
   * added; dimension, the dimension clicked, to type its size. */
  constructor(canvas, canvasPxPerScreenPx, history, on) {
    this.canvas = canvas;
    this.scale = canvasPxPerScreenPx;
    this.history = history;
    this.on = on;
    this.pixelMm = null; // known after the first preview, to show dimensions in mm
    this.shown = false; // while the mask's tools are in hand
    this.drawing = null; // { kind: "spline", points } or { kind: "circle" or "rect", from, to }
    this.pointer = null;
    this.held = null; // the handle being dragged
    this.chosen = null; // the shape whose sizes show
    this.filleted = []; // the rectangle corners chosen with the fillet, each { step, corner }
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
    if (method === "fillet") return this.#fillet(at);
    if (method === "dimension") return this.#dimension(at);
    this.held = handleNear(this.#shapes(), at, this.#reach());
    const clicked = this.held?.step ?? outlineNear(this.#shapes(), at, this.#reach());
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
      this.on.choose(this.chosen);
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

  /** Takes off the shape under the pointer, or with the dimension in hand the dimension whose
   * value is under it; true when the mask changed. */
  removeUnderPointer(method) {
    const dimension = method === "dimension" && this.pointer && labelNear(this.#shapes(), this.pointer, this.scale());
    if (dimension) dimension.step.dims = dimension.step.dims.filter((name) => name !== dimension.name);
    const step = !dimension && this.pointer && shapeUnder(this.#shapes(), this.pointer);
    if (step) this.history.remove(step);
    if (step === this.chosen || this.filleted.some((chosen) => chosen.step === step)) this.choose(null);
    this.draw();
    return Boolean(step);
  }

  cancel() {
    this.drawing = null;
    this.held = null;
    this.draw();
  }

  draw() {
    const { shown, chosen, filleted, drawing, pointer, pixelMm } = this;
    drawMaskShapes(this.canvas, this.scale(), { shown, shapes: this.#shapes(), chosen, filleted, drawing, pointer, pixelMm });
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
    this.filleted = [];
    this.on.choose(step);
  }

  /** A corner clicked is chosen to round, or no longer when it was; a rectangle's outline chooses
   * all four of its corners. Clicking away from them chooses none. */
  #fillet(at) {
    const hit = cornerNear(this.#shapes(), at, this.#reach());
    const rect = hit ? null : outlineNear(this.#shapes(), at, this.#reach());
    const clicked = hit ? [hit] : rect?.rect ? [0, 1, 2, 3].map((corner) => ({ step: rect, corner })) : [];
    const chosen = ({ step, corner }) => this.filleted.some((other) => other.step === step && other.corner === corner);
    const added = clicked.filter((one) => !chosen(one)).map(({ step, corner }) => ({ step, corner }));
    if (hit && added.length === 0) this.filleted = this.filleted.filter((one) => one.step !== hit.step || one.corner !== hit.corner);
    else this.filleted = clicked.length > 0 ? [...this.filleted, ...added] : [];
    this.chosen = null;
    this.on.fillet(this.filleted, added);
    this.draw();
    return false;
  }

  /** A dimension's value, or an edge, which is given a dimension if it had none, opens the box to
   * type its size in. */
  #dimension(at) {
    const hit = labelNear(this.#shapes(), at, this.scale()) ?? edgeNear(this.#shapes(), at, this.#reach());
    if (!hit || !this.pixelMm) return false;
    if (!hit.step.dims?.includes(hit.name)) hit.step.dims = [...(hit.step.dims ?? []), hit.name];
    this.choose(hit.step);
    this.draw();
    this.on.dimension(hit, dimensionLine(hit, this.scale()).label);
    return false;
  }

  #shapes() {
    return this.history.steps.filter((step) => !step.stroke);
  }

  #reach() {
    return REACH_SCREEN_PX * this.scale();
  }
}

function apart([x1, y1], [x2, y2]) {
  return Math.hypot(x1 - x2, y1 - y2);
}
