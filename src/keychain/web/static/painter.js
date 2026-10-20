// Painting a rough mask over the picture: red for background, green for what to keep.
// The mask canvas has the picture's own size, so the server can lay it over pixel for pixel.

const PAINT = { background: "#ff0000", keep: "#00ff00" };

export class Painter {
  constructor(stack, pictureCanvas, maskCanvas, onPainted) {
    this.stack = stack;
    this.picture = pictureCanvas;
    this.mask = maskCanvas;
    this.onPainted = onPainted;
    this.tool = "background";
    this.brushScreenPx = 20;
    this.painted = false;
    this.onPick = null;
    this.last = null;
    maskCanvas.addEventListener("pointerdown", (event) => this.#down(event));
    maskCanvas.addEventListener("pointermove", (event) => this.#move(event));
    maskCanvas.addEventListener("pointerup", () => this.#up());
    maskCanvas.addEventListener("pointerleave", () => this.#up());
  }

  load(image) {
    for (const canvas of [this.picture, this.mask]) {
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
    }
    this.picture.getContext("2d").drawImage(image, 0, 0);
    this.clear();
  }

  clear() {
    this.mask.getContext("2d").clearRect(0, 0, this.mask.width, this.mask.height);
    this.painted = false;
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

  /** The mask as a PNG data URL, or null when nothing was painted. */
  maskDataUrl() {
    return this.painted ? this.mask.toDataURL("image/png") : null;
  }

  #down(event) {
    const point = this.#point(event);
    if (this.onPick) {
      this.onPick(this.#colourAt(point));
      return;
    }
    this.mask.setPointerCapture(event.pointerId);
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
    this.painted = true;
    this.onPainted();
  }

  #stroke(from, to) {
    const context = this.mask.getContext("2d");
    const erasing = this.tool === "erase";
    context.globalCompositeOperation = erasing ? "destination-out" : "source-over";
    context.strokeStyle = erasing ? "#000000" : PAINT[this.tool];
    context.lineWidth = this.brushScreenPx * this.#canvasPxPerScreenPx();
    context.lineCap = "round";
    context.lineJoin = "round";
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.stroke();
  }

  #point(event) {
    const scale = this.#canvasPxPerScreenPx();
    return { x: event.offsetX * scale, y: event.offsetY * scale };
  }

  #canvasPxPerScreenPx() {
    return this.mask.width / this.mask.clientWidth;
  }

  #colourAt({ x, y }) {
    const [red, green, blue] = this.picture.getContext("2d").getImageData(x, y, 1, 1).data;
    return "#" + [red, green, blue].map((value) => value.toString(16).padStart(2, "0")).join("");
  }
}
