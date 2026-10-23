// Moving the points of the splines already drawn, with the spline tool in hand: the points of
// the spline under the pointer show as handles, and dragging one moves it. Where splines meet in
// one point, they move together, so they keep meeting. Dropped near another spline, a point
// lands exactly on it, as when drawing; Alt places it freely.

const GRAB_SCREEN_PX = 8; // a press this close to a point takes hold of it
const SAME_PX = 0.01; // points this close together are one, where splines meet

export class SplineEditor {
  /** curves: the HandDrawn splines, which draw the handles. */
  constructor(curves) {
    this.curves = curves;
    this.held = null; // the [x, y] points being dragged, the same spot on one or more splines
    this.moved = false;
  }

  start() {
    this.curves.handles = { curves: [], near: null };
  }

  stop() {
    this.held = null;
    this.curves.handles = null;
    this.curves.draw();
  }

  /** Shows the points of the splines under the pointer, none while a spline is being drawn or
   * the pointer is away; true when a point is under it, to take hold of. */
  hover(point) {
    const drawing = Boolean(this.curves.current);
    const near = point && !drawing ? this.#nearest(point) : null;
    const under = near ? this.#curvesWith([near]) : [point && !drawing && this.curves.curveNear(point)];
    this.#show(under.filter(Boolean), near);
    return Boolean(near);
  }

  /** Takes hold of the point under the pointer; true when there was one. */
  grab(point) {
    const near = this.curves.current ? null : this.#nearest(point);
    if (!near) return false;
    this.held = this.#points().filter((other) => apart(other, near) <= SAME_PX);
    this.moved = false;
    return true;
  }

  drag(point, snapping) {
    if (!this.held) return;
    const moving = this.#curvesWith(this.held);
    const [x, y] = (snapping && this.curves.onCurve(point, new Set(moving))) || [point.x, point.y];
    for (const held of this.held) [held[0], held[1]] = [x, y];
    this.moved = true;
    Object.assign(this.curves.handles, { curves: moving, near: this.held[0] });
    this.curves.draw();
  }

  /** Lets go of the point; true when it moved, false when it was only clicked. */
  release() {
    const moved = this.moved;
    this.held = null;
    this.moved = false;
    return moved;
  }

  /** Draws the handles again only when other ones show: hovering moves nothing. */
  #show(curves, near) {
    const handles = this.curves.handles;
    if (!handles) return;
    const same = near === handles.near && curves.length === handles.curves.length;
    if (same && curves.every((points, index) => points === handles.curves[index])) return;
    Object.assign(handles, { curves, near });
    this.curves.draw();
  }

  /** The point of a spline nearest to the pointer, within reach; null when none is. */
  #nearest(point) {
    const at = [point.x, point.y];
    const within = this.#points().filter((other) => apart(other, at) <= GRAB_SCREEN_PX * this.curves.scale());
    return within.reduce((best, other) => (best && apart(best, at) <= apart(other, at) ? best : other), null);
  }

  #curvesWith(points) {
    return this.#curves().filter((curve) => points.some((point) => curve.includes(point)));
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
