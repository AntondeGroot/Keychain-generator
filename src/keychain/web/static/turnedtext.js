// Areas round text to turn on the back: seen from behind, the picture shows mirrored, so the
// server turns the back inside each area to read the right way round. Click points round the
// text and the first point again to close the area, a spline as the paint spline is. A click
// inside a closed area, while none is being drawn, takes it off. Where the text lands on the back
// is moved in the back's preview.

import { insideCurve } from "./closedcurve.js";
import { spline } from "./handdrawn.js";

const DASH_SCREEN_PX = [6, 4];
const LINE_SCREEN_PX = 2;
const POINT_SCREEN_PX = 3;
const CLOSE_SCREEN_PX = 8; // a click this close to the first point closes the area
const SMALLEST = 3; // points an area needs before it can be closed

export class TurnedText {
  /** canvasPxPerScreenPx: a function, as the scale changes when the page is resized. */
  constructor(canvas, canvasPxPerScreenPx) {
    this.canvas = canvas;
    this.scale = canvasPxPerScreenPx;
    this.areas = []; // { points: [[x, y], ...], shift: [x, y] } in picture pixels
    this.current = null; // the points of the area being drawn
    this.pointer = null;
  }

  /** What to do next, said plainly: the page shows it above the picture. */
  guide() {
    if (!this.current) return "Select text: click points round the text. Click inside an area to take it off.";
    if (this.current.length < SMALLEST) return "Select text: keep clicking round the text. Esc cancels.";
    return "Select text: click the first point again to close the area. Esc cancels.";
  }

  /** Adds a point, closes the area, or takes off the one clicked; true when the areas changed. */
  click(point) {
    const at = [point.x, point.y];
    if (!this.current) {
      const kept = this.areas.filter((area) => !insideCurve(spline(area.points, true), at));
      if (kept.length < this.areas.length) return this.#changed(kept);
      this.current = [at];
    } else if (this.current.length >= SMALLEST && distance(this.current[0], at) <= CLOSE_SCREEN_PX * this.scale()) {
      const points = this.current;
      this.current = null;
      return this.#changed([...this.areas, { points, shift: [0, 0] }]);
    } else {
      this.current.push(at);
    }
    this.draw();
    return false;
  }

  hover(point) {
    this.pointer = point && [point.x, point.y];
    if (this.current) this.draw();
  }

  /** Moves where an area's text lands on the back, by a move in picture pixels. */
  shift(index, [x, y]) {
    const [shiftX, shiftY] = this.areas[index].shift;
    this.areas[index].shift = [shiftX + x, shiftY + y];
  }

  cancel() {
    this.current = null;
    this.draw();
  }

  /** Areas from a project; boxes saved before areas were splines are left out. */
  set(areas) {
    this.areas = areas.filter((area) => area.points).map(({ points, shift }) => ({ points, shift: [...shift] }));
    this.current = null;
    this.draw();
  }

  /** Dashed in dark over light, so the areas show on any picture. */
  draw() {
    const context = this.canvas.getContext("2d");
    const scale = this.scale();
    const toPicture = context.getTransform(); // the canvas can be sharper than the picture
    context.resetTransform();
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    context.setTransform(toPicture);
    context.lineWidth = LINE_SCREEN_PX * scale;
    const curves = this.areas.map(({ points }) => spline(points, true));
    if (this.current) curves.push(spline([...this.current, ...(this.pointer ? [this.pointer] : [])], false));
    for (const [colour, dash] of [["#ffffff", []], ["#1d1d1b", DASH_SCREEN_PX]]) {
      context.strokeStyle = colour;
      context.setLineDash(dash.map((length) => length * scale));
      for (const samples of curves) stroke(context, samples);
    }
    context.fillStyle = "#1d1d1b";
    for (const [x, y] of this.current ?? []) {
      context.beginPath();
      context.arc(x, y, POINT_SCREEN_PX * scale, 0, 2 * Math.PI);
      context.fill();
    }
  }

  #changed(areas) {
    this.areas = areas;
    this.draw();
    return true;
  }
}

function stroke(context, samples) {
  context.beginPath();
  samples.forEach(([x, y], index) => (index ? context.lineTo(x, y) : context.moveTo(x, y)));
  context.stroke();
}

function distance([x1, y1], [x2, y2]) {
  return Math.hypot(x1 - x2, y1 - y2);
}
