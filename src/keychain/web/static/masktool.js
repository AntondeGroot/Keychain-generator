// Marking background and keep, or erasing them: the action is the tool in hand, and the method
// says how it is applied, painting with the brush or drawing a shape round an area.

import { MaskHistory } from "./maskhistory.js";
import { MaskShapes } from "./maskshapes.js";

/** The mask's tools by name, and what each does. */
export const MASK_ACTIONS = { background: "background", keep: "keep", "erase-mask": "erase" };

export class MaskTool {
  /** onChanged hears each change to the mask once it is made. */
  constructor(maskCanvas, shapesCanvas, canvasPxPerScreenPx, onChanged) {
    this.history = new MaskHistory(maskCanvas);
    this.shapes = new MaskShapes(shapesCanvas, canvasPxPerScreenPx, this.history);
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
    this.shapes.draw();
  }

  clear() {
    this.history.clear();
    this.shapes.cancel();
  }

  /** The mask as a PNG data URL, or null when nothing was marked. */
  dataUrl() {
    return this.history.dataUrl();
  }

  guide(action) {
    return this.method === "shape" ? this.shapes.guide(action) : "";
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
    if (this.method === "shape") {
      if (this.shapes.down(point, action)) this.onChanged();
      return Boolean(this.shapes.held);
    }
    this.history.add({ action, stroke: { width: brushWidth, points: [[point.x, point.y]] } });
    this.stroking = true;
    return true;
  }

  move(point) {
    if (this.stroking) this.history.extendStroke([point.x, point.y]);
    else if (this.method === "shape") this.shapes.move(point);
  }

  up() {
    const changed = this.stroking || this.shapes.up();
    this.stroking = false;
    if (changed) this.onChanged();
  }

  leave() {
    this.up();
    this.shapes.move(null);
  }

  /** Delete takes off the shape under the pointer. */
  remove() {
    if (this.method === "shape" && this.shapes.removeUnderPointer()) this.onChanged();
  }

  cancel() {
    this.shapes.cancel();
  }
}
