// The editable list of filament colours: a swatch, a name, a paint and a remove button per colour.

const NAME_PATTERN = "[a-z0-9_\\-]*"; // names end up in file names, so only these characters

export class ColourList {
  constructor(list, onChange, onPaint) {
    this.list = list;
    this.onChange = onChange;
    this.onPaint = onPaint;
    this.colours = [];
  }

  set(colours) {
    this.colours = colours.map(({ name, hex }) => ({ name, hex }));
    this.#render();
  }

  add(hex, name = "") {
    this.colours.push({ name, hex });
    this.#render();
    this.onChange();
  }

  get() {
    return this.colours.map(({ name, hex }) => ({ name, hex }));
  }

  /** The names as the server will use them: the typed name, or empty for an automatic one. */
  names() {
    return this.colours.map(({ name }) => name).filter((name) => name);
  }

  #render() {
    this.list.replaceChildren(...this.colours.map((colour, index) => this.#row(colour, index)));
  }

  #row(colour, index) {
    const swatch = Object.assign(document.createElement("input"), { type: "color", value: colour.hex });
    swatch.setAttribute("aria-label", `Colour ${index + 1}`);
    swatch.addEventListener("change", () => this.#update(index, { hex: swatch.value }));

    const name = Object.assign(document.createElement("input"), {
      type: "text",
      value: colour.name,
      placeholder: "name, e.g. skin",
      pattern: NAME_PATTERN,
    });
    name.setAttribute("aria-label", `Name of colour ${index + 1}`);
    name.addEventListener("change", () => this.#update(index, { name: name.value.trim().toLowerCase() }));

    const paint = Object.assign(document.createElement("button"), { type: "button", textContent: "Paint" });
    paint.className = "tool";
    paint.dataset.tool = "paint";
    paint.setAttribute("aria-pressed", "false");
    paint.setAttribute("aria-label", `Paint with colour ${index + 1}`);
    paint.addEventListener("click", () => this.onPaint(paint, this.colours[index].hex));

    const remove = Object.assign(document.createElement("button"), { type: "button", textContent: "×" });
    remove.setAttribute("aria-label", `Remove colour ${index + 1}`);
    remove.addEventListener("click", () => this.#remove(index));

    const row = document.createElement("li");
    row.append(swatch, name, paint, remove);
    return row;
  }

  #update(index, change) {
    Object.assign(this.colours[index], change);
    this.onChange();
  }

  #remove(index) {
    this.colours.splice(index, 1);
    this.#render();
    this.onChange();
  }
}
