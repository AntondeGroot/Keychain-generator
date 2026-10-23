// The spline tool: a click adds a point to the spline being drawn; pressing a point of a finished
// spline and dragging moves it, and letting go unmoved is a click there. Alt held stops snapping.

import { SplineEditor } from "./splineedit.js";

export class SplineTool {
  /** paintColour: a function, the colour the spline paints in; onPainted hears each change. */
  constructor(curves, stack, paintColour, onPainted) {
    this.curves = curves;
    this.editor = new SplineEditor(curves);
    this.stack = stack;
    this.paintColour = paintColour;
    this.onPainted = onPainted;
    this.pressed = null; // a point pressed: { point, snapping }
  }

  /** True when a point was grabbed, so the pointer should stay with the picture while dragging. */
  down(point, snapping) {
    if (this.editor.grab(point)) {
      this.pressed = { point, snapping }; // a click if it is let go unmoved
      return true;
    }
    this.#click(point, snapping);
    return false;
  }

  move(point, snapping) {
    if (this.pressed) {
      this.editor.drag(point, snapping);
    } else {
      this.curves.hover(point, snapping);
      this.stack.classList.toggle("on-handle", this.editor.hover(point));
    }
  }

  /** A point let go: moved, or only clicked, which adds a point there as any click. */
  up() {
    if (!this.pressed) return;
    const { point, snapping } = this.pressed;
    this.pressed = null;
    if (this.editor.release()) this.onPainted();
    else this.#click(point, snapping);
  }

  /** Shows the finished splines' points to grab while the tool is in hand. */
  start() {
    this.editor.start();
  }

  stop() {
    this.editor.stop();
  }

  leave() {
    this.editor.hover(null);
  }

  #click(point, snapping) {
    if (this.curves.click(point, this.paintColour(), snapping)) this.onPainted();
    this.editor.hover(point); // none while drawing; the finished one's when it is done
  }
}
