// The picture's size: its width, its height, or both, and then it fits within them. A side that is
// not ticked follows from the picture, and one side always stays ticked.

export class PictureSize {
  /** Each side as { tick, input }, the input holding its millimetres. */
  constructor(sides, onChange) {
    this.sides = sides;
    for (const side of sides) {
      side.tick.addEventListener("change", () => {
        if (!sides.some(({ tick }) => tick.checked)) side.tick.checked = true;
        this.#enableTicked();
        onChange();
      });
    }
  }

  /** The sides as saved: a size for a ticked side, null for one that follows from the picture. */
  set(spec) {
    for (const { tick, input } of this.sides) {
      const mm = spec[input.dataset.spec];
      tick.checked = mm != null;
      if (mm != null) input.value = mm;
    }
    this.#enableTicked();
  }

  #enableTicked() {
    for (const { tick, input } of this.sides) input.disabled = !tick.checked;
  }
}
