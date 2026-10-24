// The back of the keychain as seen from behind, while text is turned on it. Where each turned
// text lands shows dashed, and dragging it moves the text, such as to sit right on a speech
// bubble that is not symmetric. The server makes the back again once it is let go. Fields under
// it turn and size each text.

import { TurnFields } from "./turnfields.js";

export class BackPreview {
  /** figure: shown only while text is turned, with elements of class preview and turn-fields
   * inside. onChange hears which area changed, and how: { move } in picture pixels, or
   * { degrees, scale }. */
  constructor(figure, onChange) {
    this.figure = figure;
    this.container = figure.querySelector(".preview");
    this.onChange = onChange;
    this.fields = new TurnFields(figure.querySelector(".turn-fields"), onChange);
    this.pixelMm = 1;
    this.held = null; // { path, from, by }: the area being dragged, in the back's own mm
    this.container.addEventListener("pointerdown", (event) => this.#grab(event));
    this.container.addEventListener("pointermove", (event) => this.#drag(event));
    this.container.addEventListener("pointerup", () => this.#letGo());
  }

  /** svgText: null when no text is turned; pixelMm: how wide a picture pixel is printed; areas:
   * the areas round text, with how far each turns and how large it is. */
  show(svgText, pixelMm, areas) {
    // The SVG comes from our own server, built from numbers and checked colour names.
    this.container.innerHTML = svgText ?? "";
    this.figure.hidden = !svgText;
    this.pixelMm = pixelMm;
    this.fields.show(svgText ? areas : []);
  }

  #grab(event) {
    const path = event.target.closest("[data-turn]");
    if (!path) return;
    event.preventDefault(); // dragging, not selecting the scale's text
    this.container.setPointerCapture(event.pointerId);
    this.held = { path, from: this.#inMm(event), by: [0, 0] };
  }

  #drag(event) {
    if (!this.held) return;
    const [x, y] = this.#inMm(event);
    this.held.by = [x - this.held.from[0], y - this.held.from[1]];
    this.held.path.setAttribute("transform", `translate(${this.held.by.join(" ")})`);
  }

  /** Seen from behind, right is left on the picture; down is down on both. */
  #letGo() {
    if (!this.held) return;
    const { path, by } = this.held;
    this.held = null;
    if (by[0] || by[1]) this.onChange(Number(path.dataset.turn), { move: [-by[0] / this.pixelMm, by[1] / this.pixelMm] });
  }

  #inMm(event) {
    const svg = this.container.querySelector("svg");
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return [point.x, point.y];
  }
}
