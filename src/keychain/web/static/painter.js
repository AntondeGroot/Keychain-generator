// Painting over the picture, on layers so an area can be both kept and detailed: "paint" with a
// filament colour, "mask" for background (red) and keep (green), "detail" for smooth (blue) and
// detailed (yellow). Connect lines go on top: click A, then B, to join an area up.
// The layers have the picture's own size, so the server can lay them over pixel for pixel.

const BRUSHES = {
  background: { layer: "mask", colour: "#ff0000" },
  keep: { layer: "mask", colour: "#00ff00" },
  smooth: { layer: "detail", colour: "#0000ff" },
  detailed: { layer: "detail", colour: "#ffff00" },
  paint: { layer: "paint", colour: null }, // the colour chosen with setPaintColour
};
const LINE_COLOUR = "#ff00ff";
const LINE_SCREEN_PX = 2;
const DOT_SCREEN_PX = 4;

export class Painter {
  /** layers: the painting canvases by name; lines: the canvas on top, which receives the pointer. */
  constructor(stack, pictureCanvas, layers, linesCanvas, onPainted) {
    this.stack = stack;
    this.picture = pictureCanvas;
    this.layers = layers;
    this.lines = linesCanvas;
    this.onPainted = onPainted;
    this.tool = "background";
    this.paintColour = "#000000";
    this.brushScreenPx = 20;
    this.painted = new Set();
    this.connections = []; // [[x, y], [x, y]] in picture pixels
    this.lineStart = null;
    this.onPick = null;
    this.last = null;
    linesCanvas.addEventListener("pointerdown", (event) => this.#down(event));
    linesCanvas.addEventListener("pointermove", (event) => this.#move(event));
    linesCanvas.addEventListener("pointerup", () => this.#up());
    linesCanvas.addEventListener("pointerleave", () => this.#up());
  }

  load(image) {
    for (const canvas of [this.picture, this.lines, ...Object.values(this.layers)]) {
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
    }
    this.picture.getContext("2d").drawImage(image, 0, 0);
    this.clear();
  }

  clear() {
    for (const canvas of Object.values(this.layers)) {
      canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
    }
    this.painted.clear();
    this.connections = [];
    this.lineStart = null;
    this.#drawLines();
  }

  setTool(tool) {
    this.tool = tool;
    this.lineStart = null;
    this.#drawLines();
  }

  setPaintColour(hex) {
    this.paintColour = hex;
  }

  setBrushSize(screenPx) {
    this.brushScreenPx = screenPx;
  }

  /** While set, a click reports the picture's colour there instead of painting. */
  pickColours(onPick) {
    this.onPick = onPick;
    this.stack.classList.toggle("picking", onPick !== null);
  }

  /** One layer as a PNG data URL, or null when nothing was painted on it. */
  dataUrl(layer) {
    return this.painted.has(layer) ? this.layers[layer].toDataURL("image/png") : null;
  }

  #down(event) {
    const point = this.#point(event);
    if (this.onPick) {
      this.onPick(this.#colourAt(point));
    } else if (this.tool === "connect") {
      this.#connectTo(point);
    } else {
      event.target.setPointerCapture(event.pointerId);
      this.last = point;
      this.#stroke(point, point);
    }
  }

  #move(event) {
    if (!this.last) return;
    const point = this.#point(event);
    this.#stroke(this.last, point);
    this.last = point;
  }

  #up() {
    if (!this.last) return;
    this.last = null;
    this.onPainted();
  }

  /** The first click sets A, the second B, which adds the connection. */
  #connectTo(point) {
    if (!this.lineStart) {
      this.lineStart = point;
    } else {
      this.connections.push([
        [this.lineStart.x, this.lineStart.y],
        [point.x, point.y],
      ]);
      this.lineStart = null;
      this.onPainted();
    }
    this.#drawLines();
  }

  #stroke(from, to) {
    const erasing = this.tool === "erase";
    if (erasing) this.#eraseLinesNear(to);
    const layers = erasing ? Object.keys(this.layers) : [BRUSHES[this.tool].layer];
    for (const layer of layers) {
      const context = this.layers[layer].getContext("2d");
      context.globalCompositeOperation = erasing ? "destination-out" : "source-over";
      context.strokeStyle = erasing ? "#000000" : (BRUSHES[this.tool].colour ?? this.paintColour);
      context.lineWidth = this.brushScreenPx * this.#canvasPxPerScreenPx();
      context.lineCap = "round";
      context.lineJoin = "round";
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
      context.stroke();
      if (!erasing) this.painted.add(layer);
    }
  }

  #eraseLinesNear(point) {
    const reach = (this.brushScreenPx / 2) * this.#canvasPxPerScreenPx();
    const kept = this.connections.filter(([a, b]) => distanceToSegment(point, a, b) > reach);
    if (kept.length === this.connections.length) return;
    this.connections = kept;
    this.#drawLines();
  }

  #drawLines() {
    const context = this.lines.getContext("2d");
    const scale = this.#canvasPxPerScreenPx();
    context.clearRect(0, 0, this.lines.width, this.lines.height);
    context.strokeStyle = LINE_COLOUR;
    context.fillStyle = LINE_COLOUR;
    context.lineWidth = LINE_SCREEN_PX * scale;
    context.setLineDash([4 * scale, 3 * scale]);
    for (const [[ax, ay], [bx, by]] of this.connections) {
      context.beginPath();
      context.moveTo(ax, ay);
      context.lineTo(bx, by);
      context.stroke();
      this.#dot(context, ax, ay, scale);
      this.#dot(context, bx, by, scale);
    }
    if (this.lineStart) this.#dot(context, this.lineStart.x, this.lineStart.y, scale);
  }

  #dot(context, x, y, scale) {
    context.beginPath();
    context.arc(x, y, DOT_SCREEN_PX * scale, 0, 2 * Math.PI);
    context.fill();
  }

  #point(event) {
    const scale = this.#canvasPxPerScreenPx();
    return { x: event.offsetX * scale, y: event.offsetY * scale };
  }

  #canvasPxPerScreenPx() {
    return this.picture.width / (this.picture.clientWidth || this.picture.width);
  }

  #colourAt({ x, y }) {
    const [red, green, blue] = this.picture.getContext("2d").getImageData(x, y, 1, 1).data;
    return "#" + [red, green, blue].map((value) => value.toString(16).padStart(2, "0")).join("");
  }
}

function distanceToSegment(point, [ax, ay], [bx, by]) {
  const dx = bx - ax;
  const dy = by - ay;
  const lengthSquared = dx * dx + dy * dy || 1;
  const along = Math.max(0, Math.min(1, ((point.x - ax) * dx + (point.y - ay) * dy) / lengthSquared));
  return Math.hypot(point.x - (ax + along * dx), point.y - (ay + along * dy));
}
