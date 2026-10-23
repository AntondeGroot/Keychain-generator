// Painting over the picture, on layers so an area can be both kept and detailed. On top:
// connect lines (click A, then B, to join an area up) and splines through clicked points, open
// as edges or closed as shapes. The erasers take off the connect lines and the curves as well as
// paint. Background and keep are marked with the brush or with shapes. Areas drawn round text
// turn it on the back. The pointer goes to the tool in hand (handtools.js).

import { HandDrawn } from "./handdrawn.js";
import { handTools } from "./handtools.js";
import { ConnectLines } from "./lines.js";
import { MaskTool } from "./masktool.js";
import { sizeOverlays } from "./overlays.js";
import { PaintLayers } from "./paintlayers.js";
import { SplineTool } from "./splinetool.js";
import { TurnedText } from "./turnedtext.js";

export class Painter {
  /** layers: the painting canvases by name, the mask among them; overlays: the canvases for the
   * curves, the areas round text, the mask's shapes and, on top and receiving the pointer, the
   * connect lines. onPainted is told the tool after each change, or "background" when the part
   * of the mask marked background changed, whichever tool changed it. */
  constructor(stack, pictureCanvas, layers, overlays, onPainted) {
    this.stack = stack;
    this.picture = pictureCanvas;
    const { mask, ...painted } = layers;
    this.layers = new PaintLayers(painted);
    const scale = () => this.#canvasPxPerScreenPx();
    this.mask = new MaskTool(mask, overlays.maskShapes, scale, (background) => this.onPainted(background ? "background" : this.tool));
    this.curves = new HandDrawn(overlays.curves, scale);
    this.lines = new ConnectLines(overlays.lines, scale);
    this.spline = new SplineTool(this.curves, stack, () => this.paintColour, () => this.onPainted());
    this.turned = new TurnedText(overlays.turned, scale);
    this.tools = handTools(this);
    this.onPainted = onPainted;
    this.onGuide = () => {}; // told what to do next whenever that changes
    this.paintColourName = "black";
    this.tool = null;
    this.paintColour = "#000000";
    this.brushScreenPx = 20;
    this.onPick = null;
    this.#listen(overlays.lines);
    this.setTool("background");
  }

  /** Everything drawn by hand, as the server wants it: lines, edges, shapes and areas round text
   * to turn, in picture pixels; and the steps the mask was made in, to edit it again. */
  get drawing() {
    const { connections } = this.lines;
    const { edges, shapes } = this.curves;
    return { connections, edges, shapes, turned: this.turned.areas, mask_steps: this.mask.saved };
  }

  /** Draws the lines and curves again, as thin and sharp on screen as before: after zooming, say. */
  redrawOverlays() {
    sizeOverlays(this.#overlays(), this.picture, this.#canvasPxPerScreenPx());
    this.curves.draw();
    this.turned.draw();
    this.mask.shapes.draw();
    this.lines.draw();
  }

  load(image) {
    const canvases = [this.picture, this.mask.history.canvas, ...this.#overlays(), ...Object.values(this.layers.canvases)];
    for (const canvas of canvases) {
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
    }
    this.picture.getContext("2d").drawImage(image, 0, 0);
    this.clear(["mask", ...this.layers.names], { lines: true, curves: true, turned: true });
  }

  /** Clears the named layers, and the connect lines, the curves and the boxes when asked. */
  clear(layers, { lines = false, curves = false, turned = false } = {}) {
    if (layers.includes("mask")) this.mask.clear();
    this.layers.clear(layers.filter((name) => name !== "mask"));
    if (lines) this.lines.set([]);
    if (curves) this.curves.set([], []);
    if (turned) this.turned.set([]);
  }

  /** Paint saved in a project: the layers as PNG data URLs (null if unpainted), and the drawing.
   * A project saved before the mask's steps were kept starts from its painted mask. */
  async restore({ mask, ...layers }, { connections = [], edges = [], shapes = [], turned = [], mask_steps }) {
    await this.layers.restore(layers);
    await this.mask.restore(mask_steps ?? { base: mask });
    this.lines.set(connections);
    this.curves.set(edges, shapes);
    this.turned.set(turned);
  }

  /** A tool by name (handtools.js), or null for none. */
  setTool(tool) {
    this.#inHand()?.putDown?.();
    this.#inHand()?.cancel();
    this.tool = tool;
    this.stack.classList.toggle("no-tool", tool === null);
    this.stack.classList.remove("on-handle");
    this.#inHand()?.pickUp?.();
    this.#showGuide();
  }

  /** How background and keep are marked: "brush" or "shape". */
  setMaskMethod(method) {
    this.mask.setMethod(method);
    this.#showGuide();
  }

  setPaintColour(hex, name) {
    this.paintColour = hex;
    this.paintColourName = name || hex;
  }

  setBrushSize(screenPx) {
    this.brushScreenPx = screenPx;
  }

  /** The brush's width in picture pixels. */
  brushWidth() {
    return this.brushScreenPx * this.#canvasPxPerScreenPx();
  }

  /** While set, a click reports the picture's colour there instead of painting. */
  pickColours(onPick) {
    this.onPick = onPick;
    this.stack.classList.toggle("picking", onPick !== null);
  }

  /** One layer as a PNG data URL, or null when nothing was painted on it. */
  dataUrl(layer) {
    return layer === "mask" ? this.mask.dataUrl() : this.layers.dataUrl(layer);
  }

  /** The pointer over the picture goes to the tool in hand; Esc and Delete as well. */
  #listen(canvas) {
    canvas.addEventListener("pointerdown", (event) => this.#down(event));
    canvas.addEventListener("pointermove", (event) => this.#move(event));
    canvas.addEventListener("pointerup", () => this.#up());
    canvas.addEventListener("pointerleave", () => this.#inHand()?.leave?.());
    document.addEventListener("keydown", (event) => {
      if (event.target.closest?.("input, select, textarea")) return; // typing a number, say
      if (event.key === "Escape") this.#inHand()?.cancel();
      else if (event.key === "Delete" || event.key === "Backspace") this.#inHand()?.remove?.();
      else return;
      this.#showGuide();
    });
  }

  #down(event) {
    const point = this.#point(event);
    if (this.onPick) return this.onPick(this.#colourAt(point));
    if (this.#inHand()?.down(point, event) === true) event.target.setPointerCapture(event.pointerId);
    this.#showGuide();
  }

  #move(event) {
    if (!this.onPick) this.#inHand()?.move?.(this.#point(event), event);
  }

  #up() {
    this.#inHand()?.up?.();
    this.#showGuide();
  }

  #inHand() {
    return this.tools[this.tool] ?? null;
  }

  /** What to do next with the tool in hand; nothing for the brushes. */
  #showGuide() {
    this.onGuide(this.#inHand()?.guide() ?? "");
  }

  #overlays() {
    return [this.curves.canvas, this.turned.canvas, this.mask.shapes.canvas, this.lines.canvas];
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
