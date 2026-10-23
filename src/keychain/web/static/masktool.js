// Marking background and keep, or erasing them: the action is the tool in hand, and the method
// says how it is applied: painting with the brush, or drawing a spline, a circle or a rectangle
// round an area. The shape last drawn or clicked shows its sizes, to type exactly.

import { MaskHistory } from "./maskhistory.js";
import { MaskShapes } from "./maskshapes.js";
import { ShapeSize } from "./shapesize.js";

/** The mask's tools by name, and what each does. */
export const MASK_ACTIONS = { background: "background", keep: "keep", "erase-mask": "erase" };

export class MaskTool {
  /** onChanged hears each change to the mask once it is made. */
  constructor(maskCanvas, shapesCanvas, canvasPxPerScreenPx, onChanged) {
    this.history = new MaskHistory(maskCanvas);
    this.shapes = new MaskShapes(shapesCanvas, canvasPxPerScreenPx, this.history, (step) => this.sizes.show(step));
    this.sizes = new ShapeSize(document.getElementById("shape-size"), () => this.#resized());
    this.onChanged = onChanged;
    this.method = "brush";
    this.stroking = false;
  }

  /** As a project keeps it, to give back to restore. */
  get saved() {
    return this.history.saved;
  }

  async restore(saved) {
    await this.history.restore(saved);
    this.shapes.choose(null);
  }

  clear() {
    this.history.clear();
    this.shapes.choose(null);
  }

  /** The mask as a PNG data URL, or null when nothing was marked. */
  dataUrl() {
    return this.history.dataUrl();
  }

  /** How big a picture pixel is on the keychain, from the preview, for the sizes in mm. */
  setPixelMm(pixelMm) {
    this.sizes.setScale(pixelMm);
  }

  guide(action) {
    return this.method === "brush" ? "" : this.shapes.guide(action, this.method);
  }

  /** Puts the shapes' outlines away while none of the mask's tools is in hand. */
  inHand(inHand) {
    this.shapes.show(inHand);
  }

  setMethod(method) {
    this.method = method;
    this.shapes.cancel();
  }

  /** True when the pointer should stay with the picture until let go: painting or dragging. */
  down(point, action, brushWidth) {
    if (this.method !== "brush") {
      if (this.shapes.down(point, action, this.method)) this.onChanged();
      return this.shapes.holding;
    }
    this.history.add({ action, stroke: { width: brushWidth, points: [[point.x, point.y]] } });
    this.stroking = true;
    return true;
  }

  move(point) {
    if (this.stroking) this.history.extendStroke([point.x, point.y]);
    else if (this.method !== "brush") this.shapes.move(point);
  }

  /** action: what a shape dragged out marks. */
  up(action) {
    const changed = this.shapes.up(action) || this.stroking;
    this.stroking = false;
    if (changed) this.onChanged();
  }

  leave(action) {
    this.up(action);
    this.shapes.move(null);
  }

  /** Delete takes off the shape under the pointer. */
  remove() {
    if (this.method !== "brush" && this.shapes.removeUnderPointer()) this.onChanged();
  }

  cancel() {
    this.shapes.cancel();
  }

  /** A size typed: the mask is drawn again with the shape at its new size. */
  #resized() {
    this.history.draw();
    this.shapes.draw();
    this.onChanged();
  }
}
