// The sizes of the circle or rectangle chosen on the mask, in mm, to type exactly: a circle's
// diameter; a rectangle's width, height and corner radius. The shapes are kept in picture pixels,
// so the fields wait for the first preview to know how big a pixel is.

import { resize, sizesOf } from "./shapekinds.js";

const DECIMALS = 1;

export class ShapeSize {
  /** box holds a label per size, each with an input whose data-size names it; onResize hears
   * each size typed. */
  constructor(box, onResize) {
    this.box = box;
    this.onResize = onResize;
    this.inputs = [...box.querySelectorAll("[data-size]")];
    this.step = null;
    this.pixelMm = null;
    for (const input of this.inputs) input.addEventListener("change", () => this.#typed(input));
  }

  setScale(pixelMm) {
    this.pixelMm = pixelMm;
    this.#fill();
  }

  /** The shape whose sizes to show, or null for none. */
  show(step) {
    this.step = step;
    this.#fill();
  }

  #fill() {
    const sizes = this.step ? sizesOf(this.step) : {};
    this.box.hidden = !this.pixelMm || Object.keys(sizes).length === 0;
    for (const input of this.inputs) {
      const size = sizes[input.dataset.size];
      input.closest("label").hidden = size === undefined;
      if (size !== undefined && document.activeElement !== input) input.value = (size * this.pixelMm).toFixed(DECIMALS);
    }
  }

  #typed(input) {
    const mm = Number(input.value);
    if (!this.step || !(mm >= 0)) return this.#fill();
    resize(this.step, input.dataset.size, mm / this.pixelMm);
    this.onResize();
    this.#fill();
  }
}
