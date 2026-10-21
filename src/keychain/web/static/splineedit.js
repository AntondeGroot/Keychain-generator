// Moving the points of the splines already drawn: every point shows as a handle, and dragging one
// moves it. Where splines meet in one point, they move together, so they keep meeting. Dropped
// near another spline, a point lands exactly on it, as when drawing; Alt places it freely.

const GRAB_SCREEN_PX = 8; // a press this close to a point takes hold of it
const SAME_PX = 0.01; // points this close together are one, where splines meet

export class SplineEditor {
  /** curves: the HandDrawn splines, which draw the handles while editing. */
  constructor(curves) {
    this.curves = curves;
    this.held = null; // the [x, y] points being dragged, the same spot on one or more splines
    this.moved = false;
  }

  start() {
    this.curves.handles = { near: null };
    this.curves.draw();
  }

  stop() {
    this.held = null;
    this.curves.handles = null;
    this.curves.draw();
  }

  guide() {
    return "Edit splines: drag a point to move it. Where splines meet, their points move together. Drop a point on another spline to join it there; hold Alt to place it freely.";
  }

  /** Lights up the point under the pointer; true when there is one to take hold of. */
  hover(point) {
    const near = point && this.#nearest(point);
    if (near !== this.curves.handles.near) {
      this.curves.handles.near = near;
      this.curves.draw();
    }
    return Boolean(near);
  }

  /** Takes hold of the point under the pointer; true when there was one. */
  grab(point) {
    const near = this.#nearest(point);
    if (!near) return false;
    this.held = this.#points().filter((other) => apart(other, near) <= SAME_PX);
    this.moved = false;
    return true;
  }

  drag(point, snapping) {
    if (!this.held) return;
    const moving = new Set(this.#curves().filter((points) => this.held.some((held) => points.includes(held))));
    const [x, y] = (snapping && this.curves.onCurve(point, moving)) || [point.x, point.y];
    for (const held of this.held) [held[0], held[1]] = [x, y];
    this.curves.handles.near = this.held[0];
    this.moved = true;
    this.curves.draw();
  }

  /** Lets go of the point; true when it moved. */
  release() {
    const moved = this.moved;
    this.held = null;
    this.moved = false;
    return moved;
  }

  /** The point of a spline nearest to the pointer, within reach; null when none is. */
  #nearest(point) {
    const at = [point.x, point.y];
    const within = this.#points().filter((other) => apart(other, at) <= GRAB_SCREEN_PX * this.curves.scale());
    return within.reduce((best, other) => (best && apart(best, at) <= apart(other, at) ? best : other), null);
  }

  #curves() {
    return [...this.curves.edges, ...this.curves.shapes.map(({ points }) => points)];
  }

  #points() {
    return this.#curves().flat();
  }
}

function apart([x1, y1], [x2, y2]) {
  return Math.hypot(x1 - x2, y1 - y2);
}
