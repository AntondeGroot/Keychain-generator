// The background and keep mask, kept as the steps it was made in: brush strokes and shapes, each
// marking background, marking keep or erasing. Drawn again in order whenever a shape changes, so
// a shape can be moved after more was painted, and what came after it stays on top. A project
// saved before the steps were kept starts from its painted mask.

import { loadedImage } from "./project.js";
import { outline } from "./shapekinds.js";

const COLOURS = { background: "#ff0000", keep: "#00ff00", erase: "#000000" }; // as the server reads them

export class MaskHistory {
  constructor(canvas) {
    this.canvas = canvas;
    this.base = null; // the mask a project was saved with, before its steps were kept
    this.steps = []; // each { action, stroke: { width, points } }, or { action } with a shape (shapekinds.js)
  }

  get painted() {
    return Boolean(this.base) || this.steps.length > 0;
  }

  /** As a project keeps it, to give back to restore. */
  get saved() {
    return { base: this.base?.src ?? null, steps: this.steps };
  }

  async restore({ base = null, steps = [] }) {
    this.base = base && (await loadedImage(base));
    this.steps = steps;
    this.draw();
  }

  clear() {
    this.base = null;
    this.steps = [];
    this.draw();
  }

  /** A new step, drawn at once on top of the others. */
  add(step) {
    this.steps.push(step);
    drawStep(this.#context(), step);
  }

  /** The stroke being painted runs on to the point. */
  extendStroke(point) {
    const step = this.steps.at(-1);
    step.stroke.points.push(point);
    drawSegment(this.#context(), step, step.stroke.points.at(-2), point);
  }

  remove(step) {
    this.steps = this.steps.filter((other) => other !== step);
    this.draw();
  }

  draw() {
    const context = this.#context();
    context.globalCompositeOperation = "source-over";
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (this.base) context.drawImage(this.base, 0, 0);
    for (const step of this.steps) drawStep(context, step);
  }

  dataUrl() {
    return this.painted ? this.canvas.toDataURL("image/png") : null;
  }

  #context() {
    return this.canvas.getContext("2d");
  }
}

function drawStep(context, step) {
  paintAs(context, step.action);
  if (!step.stroke) return fillClosed(context, outline(step));
  const { points } = step.stroke;
  for (let i = 0; i < points.length; i++) drawSegment(context, step, points[Math.max(0, i - 1)], points[i]);
}

function drawSegment(context, { action, stroke }, [x1, y1], [x2, y2]) {
  paintAs(context, action);
  context.lineWidth = stroke.width;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.beginPath();
  context.moveTo(x1, y1);
  context.lineTo(x2, y2);
  context.stroke();
}

function paintAs(context, action) {
  context.globalCompositeOperation = action === "erase" ? "destination-out" : "source-over";
  context.strokeStyle = context.fillStyle = COLOURS[action];
}

function fillClosed(context, samples) {
  context.beginPath();
  samples.forEach(([x, y], index) => (index ? context.lineTo(x, y) : context.moveTo(x, y)));
  context.closePath();
  context.fill();
}
