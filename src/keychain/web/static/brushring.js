// The brush's size under the pointer: a ring as wide as the brush paints, following the pointer
// over the picture while a brush is in hand. The brush's size is in screen pixels, so it is too.

export class BrushRing {
  constructor(stack) {
    this.ring = Object.assign(document.createElement("div"), { className: "brush-ring", hidden: true });
    stack.append(this.ring);
  }

  /** Centred on the point, in screen pixels over the picture, that wide across; null hides it. */
  show(at, diameter) {
    this.ring.hidden = !at;
    if (!at) return;
    Object.assign(this.ring.style, { left: `${at.x}px`, top: `${at.y}px`, width: `${diameter}px`, height: `${diameter}px` });
  }
}
