// Edges and shapes drawn by hand as splines through clicked points: the same Catmull-Rom curve
// the server draws. Click points; click the last point again to finish an edge, or the first
// point to close a shape. An edge redraws the border between the colours either side of it, a
// shape is filled with its colour.

const SAMPLES_PER_SPAN = 24; // as on the server, so the page shows the curve that gets made
const CLOSE_SCREEN_PX = 8; // a click this close to a point finishes the curve
const EDGE_COLOUR = "#00a3e0";
const LINE_SCREEN_PX = 2;
const POINT_SCREEN_PX = 3;
const SHAPE_OPACITY = 0.8;
const FINISH_RING_COLOUR = "#ff8c00"; // the point to click to finish, ringed in a colour that stands out
const FINISH_RING_SCREEN_PX = 7;
const SHAPE_SMALLEST = 3; // points a shape needs before it can be closed

export class HandDrawn {
  constructor(canvas, canvasPxPerScreenPx) {
    this.canvas = canvas;
    this.scale = canvasPxPerScreenPx;
    this.edges = []; // each [[x, y], ...] in picture pixels
    this.shapes = []; // each { points, colour }
    this.current = null; // the curve being drawn: { kind, points, colour }
    this.finished = null; // the kind of curve just finished, to say so
  }

  /** What to do next, said plainly: the page shows it above the picture. */
  guide(kind, colourName) {
    const count = this.current?.kind === kind ? this.current.points.length : 0;
    const points = `${count} point${count === 1 ? "" : "s"}`;
    if (kind === "edge") {
      if (count === 0 && this.finished === "edge") return "Edge done. Click to start another edge, or choose another tool.";
      if (count === 0) return "Edge: click the first point of the edge.";
      if (count === 1) return "Edge: 1 point. Click the next point along the edge.";
      return `Edge: ${points}. Keep clicking along the edge. To finish: click the last point again, the one with the orange ring. Esc cancels.`;
    }
    if (count === 0 && this.finished === "shape") return "Shape done. Click to start another shape, or choose another tool.";
    if (count === 0) return `Shape in ${colourName}: click the first point round the shape.`;
    if (count < SHAPE_SMALLEST) return `Shape in ${colourName}: ${points}. Click at least ${SHAPE_SMALLEST} points round the shape.`;
    return `Shape in ${colourName}: ${points}. To close the shape: click the first point again, the one with the orange ring. Esc cancels.`;
  }

  /** Adds a point, or finishes the curve; true when that finished one. */
  click(point, kind, colour) {
    if (this.current?.kind !== kind) this.current = { kind, points: [], colour };
    const points = this.current.points;
    const reach = CLOSE_SCREEN_PX * this.scale();
    const finishesEdge = kind === "edge" && points.length >= 2 && near(point, points.at(-1), reach);
    const closesShape = kind === "shape" && points.length >= SHAPE_SMALLEST && near(point, points[0], reach);
    this.finished = finishesEdge || closesShape ? kind : null;
    if (finishesEdge) this.edges.push(points);
    if (closesShape) this.shapes.push({ points, colour: this.current.colour });
    if (finishesEdge || closesShape) {
      this.current = null;
    } else {
      points.push([point.x, point.y]);
    }
    this.draw();
    return finishesEdge || closesShape;
  }

  cancel() {
    this.current = null;
    this.finished = null;
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
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    context.lineWidth = LINE_SCREEN_PX * scale;
    for (const { points, colour } of this.shapes) fillCurve(context, spline(points, true), colour);
    for (const points of this.edges) strokeCurve(context, spline(points, false));
    if (!this.current) return;
    const { kind, points, colour } = this.current;
    strokeCurve(context, spline(points, false));
    for (const [x, y] of points) dot(context, x, y, POINT_SCREEN_PX * scale, kind === "shape" ? colour : EDGE_COLOUR);
    const finishAt = kind === "edge" ? (points.length >= 2 ? points.at(-1) : null) : points.length >= SHAPE_SMALLEST ? points[0] : null;
    if (finishAt) ring(context, finishAt, FINISH_RING_SCREEN_PX * scale, scale);
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

function near(point, [x, y], reach) {
  return Math.hypot(point.x - x, point.y - y) <= reach;
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

function ring(context, [x, y], radius, scale) {
  context.strokeStyle = FINISH_RING_COLOUR;
  context.lineWidth = 2 * LINE_SCREEN_PX * scale;
  context.beginPath();
  context.arc(x, y, radius, 0, 2 * Math.PI);
  context.stroke();
  context.lineWidth = LINE_SCREEN_PX * scale;
}

function dot(context, x, y, radius, colour) {
  context.fillStyle = colour;
  context.beginPath();
  context.arc(x, y, radius, 0, 2 * Math.PI);
  context.fill();
}
