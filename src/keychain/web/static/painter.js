// Painting over the picture, on layers so an area can be both kept and detailed: "paint" with a
// filament colour, "mask" for background (red) and keep (green), "detail" for smooth (blue) and
// detailed (yellow). On top: connect lines (click A, then B, to join an area up) and splines
// through clicked points, open as edges or closed as shapes. One eraser takes off the mask, the
// other the details: the detail layer, the colour paint, and the lines and curves.
// The layers have the picture's own size, so the server can lay them over pixel for pixel.

import { HandDrawn } from "./handdrawn.js";
import { ConnectLines } from "./lines.js";
import { SplineEditor } from "./splineedit.js";
import { loadedImage } from "./project.js";

const SHARPEST_OVERLAY_PX = 4096; // the lines and curves are drawn this sharp at most, along the longest side

const ERASERS = {
  "erase-mask": { layers: ["mask"], drawing: false },
  "erase-details": { layers: ["detail", "paint"], drawing: true }, // with the lines and curves
};

const BRUSHES = {
  background: { layer: "mask", colour: "#ff0000" },
  keep: { layer: "mask", colour: "#00ff00" },
  smooth: { layer: "detail", colour: "#0000ff" },
  detailed: { layer: "detail", colour: "#ffff00" },
  paint: { layer: "paint", colour: null }, // the colour chosen with setPaintColour
};

export class Painter {
  /** layers: the painting canvases by name; overlays: the canvases for the curves and, on top and
   * receiving the pointer, the connect lines. onPainted is told the brush after a stroke. */
  constructor(stack, pictureCanvas, layers, overlays, onPainted) {
    this.stack = stack;
    this.picture = pictureCanvas;
    this.layers = layers;
    const scale = () => this.#canvasPxPerScreenPx();
    this.curves = new HandDrawn(overlays.curves, scale);
    this.lines = new ConnectLines(overlays.lines, scale);
    this.editor = new SplineEditor(this.curves);
    const linesCanvas = overlays.lines;
    this.onPainted = onPainted;
    this.onGuide = () => {}; // told what to do next whenever that changes
    this.paintColourName = "black";
    this.tool = "background";
    this.paintColour = "#000000";
    this.brushScreenPx = 20;
    this.painted = new Set();
    this.onPick = null;
    this.last = null;
    linesCanvas.addEventListener("pointerdown", (event) => this.#down(event));
    linesCanvas.addEventListener("pointermove", (event) => this.#move(event));
    linesCanvas.addEventListener("pointerup", () => this.#up());
    linesCanvas.addEventListener("pointerleave", () => {
      this.#up();
      this.curves.hover(null, false);
      if (this.tool === "edit-splines") this.editor.hover(null);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      this.curves.cancel();
      this.lines.cancel();
      this.#showGuide();
    });
  }

  /** Everything drawn by hand, as the server wants it: lines, edges and shapes in picture pixels. */
  get drawing() {
    return { connections: this.lines.connections, edges: this.curves.edges, shapes: this.curves.shapes };
  }

  /** Draws the lines and curves again, as thin and sharp on screen as before: after zooming, say.
   * Their canvases follow the size on screen, not the picture's, and draw in picture pixels. */
  redrawOverlays() {
    const { width, height } = this.picture;
    const screenPxPerPicturePx = devicePixelRatio / this.#canvasPxPerScreenPx();
    const sharpness = Math.min(screenPxPerPicturePx, SHARPEST_OVERLAY_PX / Math.max(width, height));
    for (const canvas of [this.curves.canvas, this.lines.canvas]) {
      canvas.width = Math.round(width * sharpness);
      canvas.height = Math.round(height * sharpness);
      canvas.getContext("2d").setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
    }
    this.curves.draw();
    this.lines.draw();
  }

  load(image) {
    for (const canvas of [this.picture, this.lines.canvas, this.curves.canvas, ...Object.values(this.layers)]) {
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
    }
    this.picture.getContext("2d").drawImage(image, 0, 0);
    this.clear();
  }

  /** Clears the named layers, and the lines and curves too if drawing; everything by default. */
  clear(layers = Object.keys(this.layers), drawing = true) {
    for (const name of layers) {
      const canvas = this.layers[name];
      canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
      this.painted.delete(name);
    }
    if (!drawing) return;
    this.lines.set([]);
    this.curves.set([], []);
  }

  /** Paint saved in a project: the layers as PNG data URLs (null if unpainted), and the drawing. */
  async restore(layers, { connections = [], edges = [], shapes = [] }) {
    for (const [name, dataUrl] of Object.entries(layers)) {
      if (!dataUrl || !this.layers[name]) continue;
      this.layers[name].getContext("2d").drawImage(await loadedImage(dataUrl), 0, 0);
      this.painted.add(name);
    }
    this.lines.set(connections);
    this.curves.set(edges, shapes);
  }

  setTool(tool) {
    this.tool = tool;
    this.lines.cancel();
    this.curves.cancel();
    if (tool === "edit-splines") this.editor.start();
    else this.editor.stop();
    this.#showGuide();
  }

  setPaintColour(hex, name) {
    this.paintColour = hex;
    this.paintColourName = name || hex;
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
      if (this.lines.click(point)) this.onPainted();
      this.#showGuide();
    } else if (this.tool === "spline") {
      if (this.curves.click(point, this.paintColour, !event.altKey)) this.onPainted();
      this.#showGuide();
    } else if (this.tool === "edit-splines") {
      if (this.editor.grab(point)) event.target.setPointerCapture(event.pointerId);
    } else {
      event.target.setPointerCapture(event.pointerId);
      this.last = point;
      this.#stroke(point, point);
    }
  }

  #move(event) {
    const point = this.#point(event);
    if (this.tool === "spline" && !this.onPick) this.curves.hover(point, !event.altKey);
    if (this.tool === "edit-splines" && !this.onPick) {
      this.editor.drag(point, !event.altKey);
      this.stack.classList.toggle("on-handle", this.editor.hover(point));
    }
    if (!this.last) return;
    this.#stroke(this.last, point);
    this.last = point;
  }

  #up() {
    if (this.editor.release()) this.onPainted();
    if (!this.last) return;
    this.last = null;
    this.onPainted(this.tool);
  }

  #stroke(from, to) {
    const eraser = ERASERS[this.tool];
    const erasing = Boolean(eraser);
    const width = this.brushScreenPx * this.#canvasPxPerScreenPx();
    if (eraser?.drawing && (this.lines.eraseNear(to, width / 2) | this.curves.eraseNear(to, width / 2))) {
      this.onPainted();
    }
    const layers = erasing ? eraser.layers : [BRUSHES[this.tool].layer];
    for (const layer of layers) {
      const context = this.layers[layer].getContext("2d");
      context.globalCompositeOperation = erasing ? "destination-out" : "source-over";
      context.strokeStyle = erasing ? "#000000" : (BRUSHES[this.tool].colour ?? this.paintColour);
      context.lineWidth = width;
      context.lineCap = "round";
      context.lineJoin = "round";
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
      context.stroke();
      if (!erasing) this.painted.add(layer);
    }
  }

  /** The guide for the drawing tools, and none for the brushes. */
  #showGuide() {
    if (this.tool === "connect") this.onGuide(this.lines.guide());
    else if (this.tool === "spline") this.onGuide(this.curves.guide(this.paintColourName));
    else if (this.tool === "edit-splines") this.onGuide(this.editor.guide());
    else this.onGuide("");
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
