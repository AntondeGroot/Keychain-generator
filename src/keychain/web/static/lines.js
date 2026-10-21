// Connect lines drawn on top of the picture: click A, then B, to say an area runs on between them.

const LINE_COLOUR = "#ff00ff";
const LINE_SCREEN_PX = 2;
const DOT_SCREEN_PX = 4;
const DASH_SCREEN_PX = [4, 3];

export class ConnectLines {
  /** canvasPxPerScreenPx: a function, as the scale changes when the page is resized. */
  constructor(canvas, canvasPxPerScreenPx) {
    this.canvas = canvas;
    this.scale = canvasPxPerScreenPx;
    this.connections = []; // [[x, y], [x, y]] in picture pixels
    this.start = null;
  }

  /** The first click sets A, the second B; true when that completed a line. */
  click(point) {
    const completed = this.start !== null;
    if (completed) {
      this.connections.push([
        [this.start.x, this.start.y],
        [point.x, point.y],
      ]);
      this.start = null;
    } else {
      this.start = point;
    }
    this.draw();
    return completed;
  }

  /** What to do next, said plainly: the page shows it above the picture. */
  guide() {
    if (this.start) return "Connect: now click point B, where the area goes on. Esc cancels.";
    return "Connect: click point A, inside the colour that should run on to point B.";
  }

  /** Forgets a half-drawn line, such as when another tool is chosen. */
  cancel() {
    this.start = null;
    this.draw();
  }

  set(connections) {
    this.connections = connections.map(([a, b]) => [[...a], [...b]]);
    this.start = null;
    this.draw();
  }

  /** Removes the lines within reach of the point; true when any went. */
  eraseNear(point, reach) {
    const kept = this.connections.filter(([a, b]) => distanceToSegment(point, a, b) > reach);
    if (kept.length === this.connections.length) return false;
    this.set(kept);
    return true;
  }

  draw() {
    const context = this.canvas.getContext("2d");
    const scale = this.scale();
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    context.strokeStyle = LINE_COLOUR;
    context.fillStyle = LINE_COLOUR;
    context.lineWidth = LINE_SCREEN_PX * scale;
    context.setLineDash(DASH_SCREEN_PX.map((length) => length * scale));
    for (const [[ax, ay], [bx, by]] of this.connections) {
      context.beginPath();
      context.moveTo(ax, ay);
      context.lineTo(bx, by);
      context.stroke();
      dot(context, ax, ay, scale);
      dot(context, bx, by, scale);
    }
    if (this.start) dot(context, this.start.x, this.start.y, scale);
  }
}

function dot(context, x, y, scale) {
  context.beginPath();
  context.arc(x, y, DOT_SCREEN_PX * scale, 0, 2 * Math.PI);
  context.fill();
}

function distanceToSegment(point, [ax, ay], [bx, by]) {
  const dx = bx - ax;
  const dy = by - ay;
  const lengthSquared = dx * dx + dy * dy || 1;
  const along = Math.max(0, Math.min(1, ((point.x - ax) * dx + (point.y - ay) * dy) / lengthSquared));
  return Math.hypot(point.x - (ax + along * dx), point.y - (ay + along * dy));
}
