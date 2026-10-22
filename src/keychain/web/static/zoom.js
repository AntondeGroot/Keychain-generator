// Zooming into the picture to draw in detail: shift and scroll zooms in around the pointer, the
// scale above the picture sets it directly. The view keeps the picture's shape and scrolls when
// zoomed in. The canvases only change size on screen, so points still land in picture pixels.

const SMALLEST = 1;
const LARGEST = 8;
const WHEEL_SENSITIVITY = 0.002; // a notch of the wheel (100) zooms by about a fifth

export class PictureZoom {
  /** viewport: the scrolling frame; content: what grows inside it; onZoom(level) on every change. */
  constructor(viewport, content, onZoom) {
    this.viewport = viewport;
    this.content = content;
    this.onZoom = onZoom;
    this.level = SMALLEST;
    viewport.addEventListener("wheel", (event) => this.#wheel(event), { passive: false });
  }

  /** A new picture: the view takes its shape, back at 100%. */
  fit(width, height) {
    this.viewport.style.aspectRatio = `${width} / ${height}`;
    this.viewport.style.setProperty("--ratio", String(width / height)); // to fit the room in height too
    this.set(SMALLEST);
  }

  /** Zooms to the level, keeping the spot under `around` (screen coordinates) in place; the middle
   * of the view by default. */
  set(level, around = null) {
    const clamped = Math.min(LARGEST, Math.max(SMALLEST, level));
    const box = this.viewport.getBoundingClientRect();
    const atX = around ? around.x - box.left : box.width / 2;
    const atY = around ? around.y - box.top : box.height / 2;
    const ratio = clamped / this.level;
    const x = (this.viewport.scrollLeft + atX) * ratio - atX;
    const y = (this.viewport.scrollTop + atY) * ratio - atY;
    this.level = clamped;
    this.content.style.width = `${clamped * 100}%`;
    this.viewport.scrollLeft = x;
    this.viewport.scrollTop = y;
    this.onZoom(clamped);
  }

  #wheel(event) {
    if (!event.shiftKey) return;
    event.preventDefault();
    const delta = event.deltaY || event.deltaX; // some browsers turn shift and scroll sideways
    this.set(this.level * Math.exp(-delta * WHEEL_SENSITIVITY), { x: event.clientX, y: event.clientY });
  }
}
