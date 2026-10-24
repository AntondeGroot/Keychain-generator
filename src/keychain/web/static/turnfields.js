// How far each text on the back is turned and how large it is, to fit where the back has less
// room for it than the front: a row of fields per area round text, in the order they were drawn.

const PERCENT = 100;

export class TurnFields {
  /** box: where the rows go; onChange hears which area changed, and its { degrees, scale }. */
  constructor(box, onChange) {
    this.box = box;
    this.onChange = onChange;
  }

  /** A row per area, each with its turn and size; a field being typed in keeps what it has. */
  show(areas) {
    if (this.box.children.length !== areas.length) {
      this.box.replaceChildren(...areas.map((_, index) => this.#row(index, areas.length)));
    }
    areas.forEach(({ degrees, scale }, index) => {
      const [turn, size] = this.box.children[index].querySelectorAll("input");
      if (document.activeElement !== turn) turn.value = String(degrees);
      if (document.activeElement !== size) size.value = String(Math.round(scale * PERCENT));
    });
  }

  #row(index, count) {
    const row = document.createElement("div");
    row.className = "row";
    const name = count > 1 ? `Text ${index + 1}` : "Text";
    const turn = field(row, `${name}: turn`, "°", { step: 1 });
    const size = field(row, "size", "%", { min: 10, max: 400, step: 1 });
    const changed = () => {
      if (turn.value === "" || !(Number(size.value) > 0)) return;
      this.onChange(index, { degrees: Number(turn.value), scale: Number(size.value) / PERCENT });
    };
    for (const input of [turn, size]) input.addEventListener("change", changed);
    return row;
  }
}

function field(row, text, unit, attributes) {
  const label = document.createElement("label");
  const input = Object.assign(document.createElement("input"), { type: "number", ...attributes });
  label.append(`${text} `, input, ` ${unit}`);
  row.append(label);
  return input;
}
