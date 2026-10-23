// The sizes of the circle or rectangle chosen on the mask, in mm, to type exactly: a circle's
// diameter; a rectangle's width, height and corner radius. With the fillet in hand, the radius
// the corners chosen have, to round them all at once, and that corners get when chosen. The
// shapes are kept in picture pixels, so the fields wait for the first preview to know how big a
// pixel is.

import { resize, sharedRadius, sizesOf } from "./shapekinds.js";

const DECIMALS = 1;
const FILLET_MM = 2; // the radius a corner gets when filleted, until another is typed

export class ShapeSize {
  /** box holds a label per size, each with an input whose data-size names it; onResize hears
   * each size typed. */
  constructor(box, onResize) {
    this.box = box;
    this.onResize = onResize;
    this.inputs = [...box.querySelectorAll("[data-size]")];
    this.step = null;
    this.corners = []; // the rectangle corners chosen with the fillet, each { step, corner }
    this.filleting = false;
    this.filletMm = FILLET_MM;
    this.pixelMm = null;
    for (const input of this.inputs) input.addEventListener("change", () => this.#typed(input));
  }

  setScale(pixelMm) {
    this.pixelMm = pixelMm;
    this.#fill();
  }

  /** While the fillet is in hand, the radius it rounds corners by shows, to type another. */
  setFilleting(filleting) {
    this.filleting = filleting;
    this.#fill();
  }

  /** The shape whose sizes to show, or null for none. */
  show(step) {
    this.step = step;
    this.corners = [];
    this.#fill();
  }

  /** The corners chosen with the fillet, to round all at once; those just added are rounded by
   * the fillet's radius. */
  fillet(corners, added) {
    this.step = null;
    this.corners = corners;
    if (this.pixelMm && added.length > 0) this.#round(added, this.filletMm);
    this.#fill();
  }

  #round(corners, mm) {
    for (const { step, corner } of corners) resize(step, "radius", mm / this.pixelMm, corner);
    this.onResize();
  }

  #sizes() {
    if (this.step) return sizesOf(this.step);
    if (!this.filleting || !this.pixelMm) return {};
    return { radius: this.corners.length > 0 ? sharedRadius(this.corners) : this.filletMm / this.pixelMm };
  }

  #fill() {
    const sizes = this.#sizes();
    this.box.hidden = !this.pixelMm || Object.keys(sizes).length === 0;
    for (const input of this.inputs) {
      const size = sizes[input.dataset.size];
      input.closest("label").hidden = size === undefined;
      if (size === undefined || document.activeElement === input) continue;
      input.value = size === null ? "" : (size * this.pixelMm).toFixed(DECIMALS); // empty where corners differ
    }
  }

  /** A size typed; with the fillet, a radius for all the corners chosen, and for those to come. */
  #typed(input) {
    const mm = Number(input.value);
    if (input.value === "" || !(mm >= 0)) return this.#fill();
    if (this.step) {
      resize(this.step, input.dataset.size, mm / this.pixelMm);
      this.onResize();
    } else if (this.filleting) {
      this.filletMm = mm;
      if (this.corners.length > 0) this.#round(this.corners, mm);
    }
    this.#fill();
  }
}
