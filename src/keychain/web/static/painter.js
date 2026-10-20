// Painting rough masks over the picture, on two layers so an area can be both kept and detailed:
// "mask" for background (red) and keep (green), "detail" for smooth (blue) and detailed (yellow).
// The layers have the picture's own size, so the server can lay them over pixel for pixel.

const BRUSHES = {
  background: { layer: "mask", colour: "#ff0000" },
  keep: { layer: "mask", colour: "#00ff00" },
  smooth: { layer: "detail", colour: "#0000ff" },
  detailed: { layer: "detail", colour: "#ffff00" },
};
const ALL_LAYERS = ["mask", "detail"];

export class Painter {
  /** layers: the canvases by layer name; the last one is on top and receives the pointer. */
  constructor(stack, pictureCanvas, layers, onPainted) {
    this.stack = stack;
    this.picture = pictureCanvas;
    this.layers = layers;
    this.onPainted = onPainted;
    this.tool = "background";
    this.brushScreenPx = 20;
    this.painted = new Set();
    this.onPick = null;
    this.last = null;
    const top = Object.values(layers).at(-1);
    top.addEventListener("pointerdown", (event) => this.#down(event));
    top.addEventListener("pointermove", (event) => this.#move(event));
    top.addEventListener("pointerup", () => this.#up());
    top.addEventListener("pointerleave", () => this.#up());
  }

  load(image) {
    for (const canvas of [this.picture, ...Object.values(this.layers)]) {
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
  }

  setTool(tool) {
    this.tool = tool;
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
      return;
    }
    event.target.setPointerCapture(event.pointerId);
    this.last = point;
    this.#stroke(point, point);
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

  #stroke(from, to) {
    const erasing = this.tool === "erase";
    const layers = erasing ? ALL_LAYERS : [BRUSHES[this.tool].layer];
    for (const layer of layers) {
      const context = this.layers[layer].getContext("2d");
      context.globalCompositeOperation = erasing ? "destination-out" : "source-over";
      context.strokeStyle = erasing ? "#000000" : BRUSHES[this.tool].colour;
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

  #point(event) {
    const scale = this.#canvasPxPerScreenPx();
    return { x: event.offsetX * scale, y: event.offsetY * scale };
  }

  #canvasPxPerScreenPx() {
    return this.picture.width / this.picture.clientWidth;
  }

  #colourAt({ x, y }) {
    const [red, green, blue] = this.picture.getContext("2d").getImageData(x, y, 1, 1).data;
    return "#" + [red, green, blue].map((value) => value.toString(16).padStart(2, "0")).join("");
  }
}
