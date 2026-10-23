// The box to type a dimension in, on the picture where the dimension's value shows: Enter sets
// it; Esc, or clicking away, leaves it as it was.

export class DimensionInput {
  /** canvasPxPerScreenPx: a function, as the scale changes when the page is resized. */
  constructor(input, canvasPxPerScreenPx) {
    this.input = input;
    this.scale = canvasPxPerScreenPx;
    this.onSet = null;
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") this.#set();
      else if (event.key === "Escape") this.close();
    });
    input.addEventListener("blur", () => this.close());
  }

  /** Opens the box at the point, in picture pixels, with the value in mm; onSet hears the mm typed. */
  open([x, y], mm, onSet) {
    const scale = this.scale();
    Object.assign(this.input.style, { left: `${x / scale}px`, top: `${y / scale}px` });
    this.input.value = mm;
    this.input.hidden = false;
    this.onSet = onSet;
    setTimeout(() => this.input.select()); // after the click that opened it, which would take the focus away
  }

  close() {
    this.input.hidden = true;
    this.onSet = null;
  }

  #set() {
    const mm = Number(this.input.value);
    if (this.input.value !== "" && mm > 0) this.onSet?.(mm);
    this.close();
  }
}
