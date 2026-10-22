// The editable list of filament colours: a swatch, a name, a paint and a remove button per colour.
// Colours found in the picture can be found again; ones added or changed by hand stay.
// A colour can be a shade of another instead of a filament: a dark or light red, printed in red.

const NAME_PATTERN = "[a-z0-9_\\-]*"; // names end up in file names, so only these characters

export class ColourList {
  constructor(list, onChange, onPaint) {
    this.list = list;
    this.onChange = onChange;
    this.onPaint = onPaint;
    this.colours = [];
  }

  /** Colours found in the picture, or as saved in a project: as get() gives them. */
  set(colours) {
    this.colours = colours.map(({ name, hex, found = false, shade }) => ({
      name,
      hex,
      found,
      shade: shade ? { tone: shade.tone, of: colours[shade.of]?.hex } : null,
    }));
    this.#render();
  }

  /** The colours found again: these replace the ones found before, the ones by hand stay. */
  refound(colours) {
    const found = colours.map(({ name, hex }) => ({ name, hex, found: true, shade: null }));
    this.colours = [...this.colours.filter((colour) => !colour.found), ...found];
    this.#render();
  }

  byHand() {
    return this.colours.filter(({ found }) => !found).map(({ name, hex }) => ({ name, hex }));
  }

  add(hex, name = "") {
    this.colours.push({ name, hex, found: false, shade: null });
    this.#render();
    this.onChange();
  }

  /** A shade names the colour it is of by its place in the list; one whose colour is gone is
   * a colour of its own again. */
  get() {
    return this.colours.map(({ name, hex, found, shade }) => {
      const colour = found ? { name, hex, found } : { name, hex };
      const of = shade ? this.colours.findIndex((other) => other.hex === shade.of && !other.shade) : -1;
      return of >= 0 ? { ...colour, shade: { of, tone: shade.tone } } : colour;
    });
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
    row.append(swatch, name, this.#shadeChoice(colour, index), paint, remove);
    return row;
  }

  /** Its own filament, or a darker or lighter shade of another colour that is one. */
  #shadeChoice(colour, index) {
    const filaments = this.colours.filter((other) => other !== colour && !other.shade);
    const chosen = colour.shade ? `${colour.shade.tone} ${colour.shade.of}` : "";
    const option = (label, value) => new Option(label, value, false, value === chosen);
    const shades = filaments.flatMap(({ name, hex }) =>
      ["dark", "light"].map((tone) => option(`${tone} ${name || hex}`, `${tone} ${hex}`)),
    );
    const select = document.createElement("select");
    select.append(option("own filament", ""), ...shades);
    select.disabled = this.colours.some((other) => other.shade?.of === colour.hex); // others are its shades
    select.setAttribute("aria-label", `Colour ${index + 1} is printed as`);
    select.addEventListener("change", () => {
      const [tone, of] = select.value.split(" ");
      this.#update(index, { shade: select.value ? { tone, of } : null });
    });
    return select;
  }

  /** A shade follows its colour when that colour changes. The rows are drawn again, as the
   * shade choices name the colours and leave out shades. */
  #update(index, change) {
    const before = this.colours[index].hex;
    if (change.hex) for (const other of this.colours) if (other.shade?.of === before) other.shade.of = change.hex;
    Object.assign(this.colours[index], change, { found: false });
    this.#render();
    this.onChange();
  }

  #remove(index) {
    this.colours.splice(index, 1);
    this.#render();
    this.onChange();
  }
}
