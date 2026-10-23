// Splines drawn by hand through clicked points: the same Catmull-Rom curve the server draws.
// Click points; click the last point again to finish an open spline, an edge, or the first
// point to close it into a shape. An edge redraws the border between the colours either side
// of it, a shape is filled with its colour. A click near a finished curve snaps onto it, so a
// new spline can start or end exactly on another one; holding Alt places the point freely.
// While drawing, the curve runs on to the pointer, as it would be with a click there. Otherwise
// the points of the curve under the pointer show as handles to drag (splineedit.js).

const SAMPLES_PER_SPAN = 24; // as on the server, so the page shows the curve that gets made
const CLOSE_SCREEN_PX = 8; // a click this close to a point finishes the curve
const EDGE_COLOUR = "#00a3e0";
const LINE_SCREEN_PX = 2;
const POINT_SCREEN_PX = 3;
const SHAPE_OPACITY = 0.8;
const FINISH_RING_COLOUR = "#ff8c00"; // the last point, to click to finish an edge
const CLOSE_RING_COLOUR = "#1fbf4a"; // the first point, to click to close a shape
const RING_SCREEN_PX = 7;
const SHAPE_SMALLEST = 3; // points a shape needs before it can be closed
const SNAP_SCREEN_PX = 8; // a click this close to a finished curve lands on it
const SNAP_COLOUR = "#d81b60"; // where a click would land on a finished curve
const SNAP_SCREEN_RADIUS_PX = 4;
const HANDLE_SCREEN_PX = 4; // a point of a curve, to drag
const HANDLE_LIT_SCREEN_PX = 6; // the one under the pointer
const HANDLE_FILL = "#ffffff";

export class HandDrawn {
  constructor(canvas, canvasPxPerScreenPx) {
    this.canvas = canvas;
    this.scale = canvasPxPerScreenPx;
    this.edges = []; // each [[x, y], ...] in picture pixels
    this.shapes = []; // each { points, colour }
    this.current = null; // the spline being drawn: { points, colour }
    this.finished = null; // "Edge" or "Shape": what the spline just finished became, to say so
    this.snap = null; // [x, y] on a finished curve, where a click under the pointer would land
    this.pointer = null; // { x, y } in picture pixels, while over the picture
    this.handles = null; // { curves, near }: the points of these curves shown, the one at near lit up
  }

  /** What to do next, said plainly: the page shows it above the picture. */
  guide(colourName) {
    const count = this.current?.points.length ?? 0;
    const finish = "Done? Click the last point again (orange ring).";
    const done = { Edge: "Edge smoothed.", Shape: "Shape added." }[this.finished];
    if (count === 0 && done) return `${done} Click to draw another curve, or pick another tool.`;
    if (count === 0)
      return "Spline: click to draw a curve. It doesn't need to be a closed loop: use it to replace a generated harsh edge with a smooth one. You can connect start to end and create a shape: useful for small detailed areas. Click on another curve (pink dot) to start or end exactly on it; hold Alt to place a point freely. Move over a curve to see its points, and drag one to move it.";
    if (count === 1) return "Spline: keep clicking along the curve.";
    if (count < SHAPE_SMALLEST) return `Spline: keep clicking along the curve. ${finish} Esc cancels.`;
    return `Spline: keep clicking along the curve. ${finish} Want a shape in ${colourName} instead? Click the first point (green ring). Esc cancels.`;
  }

  /** Adds a point, on a finished curve when near one and snapping, or finishes the spline as an
   * edge or a shape; true when that finished one. */
  click(point, colour, snapping) {
    if (!this.current) this.current = { points: [], colour };
    const points = this.current.points;
    this.finished = this.#finishing(point);
    if (this.finished === "Edge") this.edges.push(points);
    if (this.finished === "Shape") this.shapes.push({ points, colour: this.current.colour });
    if (this.finished) {
      this.current = null;
    } else {
      points.push((snapping && this.onCurve(point)) || [point.x, point.y]);
    }
    this.snap = null;
    this.pointer = point;
    this.draw();
    return this.finished !== null;
  }

  /** Follows the pointer: the curve being drawn runs on to it, and where a click would land on a
   * finished curve shows; null when the pointer leaves the picture. */
  hover(point, snapping) {
    const snap = point && snapping && !this.#finishing(point) ? this.onCurve(point) : null;
    if (!this.current && !snap && !this.snap) return;
    this.snap = snap;
    this.pointer = point;
    this.draw();
  }

  cancel() {
    this.current = null;
    this.finished = null;
    this.snap = null;
    this.draw();
  }

  set(edges, shapes) {
    this.edges = edges.map((points) => points.map(([x, y]) => [x, y]));
    this.shapes = shapes.map(({ points, colour }) => ({ points: points.map(([x, y]) => [x, y]), colour }));
    this.current = null;
    this.draw();
  }

  /** Removes the curves within reach of the point; true when any went. */
  eraseNear(point, reach) {
    const far = (points, closed) => spline(points, closed).every(([x, y]) => !near(point, [x, y], reach));
    const edges = this.edges.filter((points) => far(points, false));
    const shapes = this.shapes.filter(({ points }) => far(points, true));
    if (edges.length === this.edges.length && shapes.length === this.shapes.length) return false;
    this.edges = edges;
    this.shapes = shapes;
    this.draw();
    return true;
  }

  draw() {
    const context = this.canvas.getContext("2d");
    const scale = this.scale();
    const toPicture = context.getTransform(); // the canvas can be sharper than the picture
    context.resetTransform();
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    context.setTransform(toPicture);
    context.lineWidth = LINE_SCREEN_PX * scale;
    for (const { points, colour } of this.shapes) fillCurve(context, spline(points, true), colour);
    for (const points of this.edges) strokeCurve(context, spline(points, false));
    if (this.current) this.#drawCurrent(context, scale);
    if (this.snap) dot(context, ...this.snap, SNAP_SCREEN_RADIUS_PX * scale, SNAP_COLOUR);
    if (this.handles) this.#drawHandles(context, scale);
  }

  /** The points of the curves under the pointer, to drag; the one under the pointer lit up. */
  #drawHandles(context, scale) {
    for (const point of this.handles.curves.flat()) {
      const lit = point === this.handles.near;
      handle(context, point, (lit ? HANDLE_LIT_SCREEN_PX : HANDLE_SCREEN_PX) * scale, lit);
    }
  }

  #drawCurrent(context, scale) {
    const { points } = this.current;
    strokeCurve(context, this.#curveToPointer());
    for (const [x, y] of points) dot(context, x, y, POINT_SCREEN_PX * scale, EDGE_COLOUR);
    const radius = RING_SCREEN_PX * scale;
    if (points.length >= 2) ring(context, points.at(-1), radius, scale, FINISH_RING_COLOUR);
    if (points.length >= SHAPE_SMALLEST) ring(context, points[0], radius, scale, CLOSE_RING_COLOUR);
  }

  /** The curve being drawn as a click at the pointer would make it: on to the pointer, or closed
   * or finished when the pointer is on the first or last point's ring. */
  #curveToPointer() {
    const { points } = this.current;
    if (!this.pointer) return spline(points, false);
    const finishing = this.#finishing(this.pointer);
    if (finishing === "Shape") return [...spline(points, true), points[0]];
    if (finishing === "Edge") return spline(points, false);
    return spline([...points, this.snap ?? [this.pointer.x, this.pointer.y]], false);
  }

  /** "Shape" when the point closes the spline being drawn, "Edge" when it finishes it, else null. */
  #finishing(point) {
    const points = this.current?.points ?? [];
    const reach = CLOSE_SCREEN_PX * this.scale();
    const toFirst = points.length >= SHAPE_SMALLEST ? distance(point, points[0]) : Infinity;
    const toLast = points.length >= 2 ? distance(point, points.at(-1)) : Infinity;
    if (toFirst <= reach && toFirst <= toLast) return "Shape";
    return toLast <= reach ? "Edge" : null;
  }

  /** The nearest point on a finished curve within reach, as [x, y]; null when none is near.
   * The curves whose points are in leaveOut do not count, such as those being moved. */
  onCurve(point, leaveOut = new Set()) {
    return this.#nearestOnCurve(point, leaveOut)?.at ?? null;
  }

  /** The points of the finished curve within reach of the point; null when none is near. */
  curveNear(point) {
    return this.#nearestOnCurve(point, new Set())?.points ?? null;
  }

  #nearestOnCurve(point, leaveOut) {
    let nearest = null;
    let nearestDistance = SNAP_SCREEN_PX * this.scale();
    const curves = [
      ...this.edges.map((points) => ({ points, closed: false })),
      ...this.shapes.map(({ points }) => ({ points, closed: true })),
    ].filter(({ points }) => !leaveOut.has(points));
    for (const { points, closed } of curves) {
      const samples = spline(points, closed);
      for (let i = 1; i < samples.length; i++) {
        const on = nearestOnSegment(point, samples[i - 1], samples[i]);
        if (distance(point, on) <= nearestDistance) [nearest, nearestDistance] = [{ at: on, points }, distance(point, on)];
      }
    }
    return nearest;
  }
}

/** A Catmull-Rom curve through the points, as [x, y] samples; the server uses the same formula. */
export function spline(points, closed) {
  if (points.length < 2) return points;
  const padded = closed
    ? [points.at(-1), ...points, points[0], points[1]]
    : [points[0], ...points, points.at(-1)];
  const spans = closed ? points.length : points.length - 1;
  const samples = [];
  for (let i = 0; i < spans; i++) {
    const [p0, p1, p2, p3] = padded.slice(i, i + 4);
    for (let step = 0; step < SAMPLES_PER_SPAN; step++) samples.push(span(p0, p1, p2, p3, step / SAMPLES_PER_SPAN));
  }
  samples.push(closed ? points[0] : points.at(-1));
  return samples;
}

function span(p0, p1, p2, p3, t) {
  return [0, 1].map(
    (axis) =>
      0.5 *
      (2 * p1[axis] +
        (p2[axis] - p0[axis]) * t +
        (2 * p0[axis] - 5 * p1[axis] + 4 * p2[axis] - p3[axis]) * t ** 2 +
        (3 * p1[axis] - p0[axis] - 3 * p2[axis] + p3[axis]) * t ** 3),
  );
}

function near(point, at, reach) {
  return distance(point, at) <= reach;
}

function distance(point, [x, y]) {
  return Math.hypot(point.x - x, point.y - y);
}

function nearestOnSegment(point, [x1, y1], [x2, y2]) {
  const length2 = (x2 - x1) ** 2 + (y2 - y1) ** 2;
  const t = length2 ? ((point.x - x1) * (x2 - x1) + (point.y - y1) * (y2 - y1)) / length2 : 0;
  const along = Math.min(1, Math.max(0, t));
  return [x1 + along * (x2 - x1), y1 + along * (y2 - y1)];
}

function strokeCurve(context, samples) {
  if (samples.length < 2) return;
  context.strokeStyle = EDGE_COLOUR;
  context.beginPath();
  samples.forEach(([x, y], index) => (index ? context.lineTo(x, y) : context.moveTo(x, y)));
  context.stroke();
}

function fillCurve(context, samples, colour) {
  context.globalAlpha = SHAPE_OPACITY;
  context.fillStyle = colour;
  context.beginPath();
  samples.forEach(([x, y], index) => (index ? context.lineTo(x, y) : context.moveTo(x, y)));
  context.closePath();
  context.fill();
  context.globalAlpha = 1;
  strokeCurve(context, [...samples, samples[0]]);
}

function ring(context, [x, y], radius, scale, colour) {
  context.strokeStyle = colour;
  context.lineWidth = 2 * LINE_SCREEN_PX * scale;
  context.beginPath();
  context.arc(x, y, radius, 0, 2 * Math.PI);
  context.stroke();
  context.lineWidth = LINE_SCREEN_PX * scale;
}

function handle(context, [x, y], radius, lit) {
  context.fillStyle = lit ? FINISH_RING_COLOUR : HANDLE_FILL;
  context.strokeStyle = EDGE_COLOUR;
  context.beginPath();
  context.arc(x, y, radius, 0, 2 * Math.PI);
  context.fill();
  context.stroke();
}

function dot(context, x, y, radius, colour) {
  context.fillStyle = colour;
  context.beginPath();
  context.arc(x, y, radius, 0, 2 * Math.PI);
  context.fill();
}
