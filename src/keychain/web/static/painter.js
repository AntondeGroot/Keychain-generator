// Painting over the picture, on layers so an area can be both kept and detailed. On top:
// connect lines (click A, then B, to join an area up) and splines through clicked points, open
// as edges or closed as shapes. The erasers take off the connect lines and the curves as well as
// paint. Areas drawn round text turn it on the back.

import { HandDrawn } from "./handdrawn.js";
import { ConnectLines } from "./lines.js";
import { sizeOverlays } from "./overlays.js";
import { ERASERS, PaintLayers } from "./paintlayers.js";
import { SplineTool } from "./splinetool.js";
import { TurnedText } from "./turnedtext.js";

export class Painter {
  /** layers: the painting canvases by name; overlays: the canvases for the curves, the areas
   * round text and, on top and receiving the pointer, the connect lines. onPainted is told the
   * brush after a stroke. */
  constructor(stack, pictureCanvas, layers, overlays, onPainted) {
    this.stack = stack;
    this.picture = pictureCanvas;
    this.layers = new PaintLayers(layers);
    const scale = () => this.#canvasPxPerScreenPx();
    this.curves = new HandDrawn(overlays.curves, scale);
    this.lines = new ConnectLines(overlays.lines, scale);
    this.spline = new SplineTool(this.curves, stack, () => this.paintColour, () => this.onPainted());
    this.turned = new TurnedText(overlays.turned, scale);
    const linesCanvas = overlays.lines;
    this.onPainted = onPainted;
    this.onGuide = () => {}; // told what to do next whenever that changes
    this.paintColourName = "black";
    this.tool = "background";
    this.paintColour = "#000000";
    this.brushScreenPx = 20;
    this.onPick = null;
    this.last = null;
    linesCanvas.addEventListener("pointerdown", (event) => this.#down(event));
    linesCanvas.addEventListener("pointermove", (event) => this.#move(event));
    linesCanvas.addEventListener("pointerup", () => this.#up());
    linesCanvas.addEventListener("pointerleave", () => {
      this.#up();
      this.curves.hover(null, false);
      this.turned.hover(null);
      if (this.tool === "spline") this.spline.leave();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      this.curves.cancel();
      this.lines.cancel();
      this.turned.cancel();
      this.#showGuide();
    });
  }

  /** Everything drawn by hand, as the server wants it: lines, edges, shapes and areas round text
   * to turn, in picture pixels. */
  get drawing() {
    const { connections } = this.lines;
    return { connections, edges: this.curves.edges, shapes: this.curves.shapes, turned: this.turned.areas };
  }

  /** Draws the lines and curves again, as thin and sharp on screen as before: after zooming, say. */
  redrawOverlays() {
    sizeOverlays(this.#overlays(), this.picture, this.#canvasPxPerScreenPx());
    this.curves.draw();
    this.turned.draw();
    this.lines.draw();
  }

  load(image) {
    for (const canvas of [this.picture, ...this.#overlays(), ...Object.values(this.layers.canvases)]) {
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
    }
    this.picture.getContext("2d").drawImage(image, 0, 0);
    this.clear(this.layers.names, { lines: true, curves: true, turned: true });
  }

  /** Clears the named layers, and the connect lines, the curves and the boxes when asked. */
  clear(layers, { lines = false, curves = false, turned = false } = {}) {
    this.layers.clear(layers);
    if (lines) this.lines.set([]);
    if (curves) this.curves.set([], []);
    if (turned) this.turned.set([]);
  }

  /** Paint saved in a project: the layers as PNG data URLs (null if unpainted), and the drawing. */
  async restore(layers, { connections = [], edges = [], shapes = [], turned = [] }) {
    await this.layers.restore(layers);
    this.lines.set(connections);
    this.curves.set(edges, shapes);
    this.turned.set(turned);
  }

  /** A brush or a drawing tool by name, or null for none. */
  setTool(tool) {
    this.tool = tool;
    this.stack.classList.toggle("no-tool", tool === null);
    this.lines.cancel();
    this.curves.cancel();
    this.turned.cancel();
    if (tool === "spline") this.spline.start();
    else this.spline.stop();
    this.stack.classList.remove("on-handle");
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
    return this.layers.dataUrl(layer);
  }

  #down(event) {
    const point = this.#point(event);
    if (this.onPick) {
      this.onPick(this.#colourAt(point));
    } else if (this.tool === "connect") {
      if (this.lines.click(point)) this.onPainted();
      this.#showGuide();
    } else if (this.tool === "spline") {
      if (this.spline.down(point, !event.altKey)) event.target.setPointerCapture(event.pointerId);
      this.#showGuide();
    } else if (this.tool === "turn-text") {
      if (this.turned.click(point)) this.onPainted();
      this.#showGuide();
    } else if (this.tool) {
      event.target.setPointerCapture(event.pointerId);
      this.last = point;
      this.#stroke(point, point);
    }
  }

  #move(event) {
    const point = this.#point(event);
    if (this.tool === "spline" && !this.onPick) this.spline.move(point, !event.altKey);
    if (this.tool === "turn-text") this.turned.hover(point);
    if (!this.last) return;
    this.#stroke(this.last, point);
    this.last = point;
  }

  #up() {
    if (this.tool === "spline") {
      this.spline.up();
      this.#showGuide();
    }
    if (!this.last) return;
    this.last = null;
    this.onPainted(this.tool);
  }

  #stroke(from, to) {
    const eraser = ERASERS[this.tool];
    const width = this.brushScreenPx * this.#canvasPxPerScreenPx();
    const erasedLines = eraser?.lines && this.lines.eraseNear(to, width / 2);
    const erasedCurves = eraser?.curves && this.curves.eraseNear(to, width / 2);
    if (erasedLines || erasedCurves) this.onPainted();
    this.layers.stroke(this.tool, from, to, width, this.paintColour);
  }

  /** The guide for the drawing tools, and none for the brushes. */
  #showGuide() {
    if (this.tool === "connect") this.onGuide(this.lines.guide());
    else if (this.tool === "spline") this.onGuide(this.curves.guide(this.paintColourName));
    else if (this.tool === "turn-text") this.onGuide(this.turned.guide());
    else this.onGuide("");
  }

  #overlays() {
    return [this.curves.canvas, this.turned.canvas, this.lines.canvas];
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
