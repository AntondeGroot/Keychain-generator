// The rim's colour: ink, one of the picture's colours by name, or any other colour, such as green.
// The swatch beside the list always shows the rim's colour; picking another one there chooses it.

const OTHER = "other"; // the choice for a colour that is not one of the picture's

export class RimChoice {
  constructor(select, swatch, onChange) {
    this.select = select;
    this.swatch = swatch;
    this.colours = [];
    this.otherHex = swatch.value;
    select.addEventListener("change", () => {
      this.#showColour();
      onChange();
    });
    swatch.addEventListener("change", () => {
      this.otherHex = swatch.value;
      this.select.value = OTHER;
      onChange();
    });
  }

  /** The choices follow the colours, keeping the one chosen. */
  follow(colours) {
    this.colours = colours;
    const chosen = this.select.value;
    const names = colours.map(({ name }) => name).filter((name) => name);
    const choices = names.map((name) => new Option(name, name, false, name === chosen));
    const other = new Option("other colour", OTHER, false, chosen === OTHER);
    this.select.replaceChildren(new Option("ink (darkest)", ""), ...choices, other);
    this.#showColour();
  }

  /** A colour's name, a colour like "#2e7d32" for another one, or null for ink. */
  value() {
    const chosen = this.select.value;
    return chosen === OTHER ? this.otherHex : chosen || null;
  }

  set(colour) {
    const other = Boolean(colour?.startsWith("#"));
    if (other) this.otherHex = colour;
    this.select.value = other ? OTHER : (colour ?? "");
    this.#showColour();
  }

  #showColour() {
    const chosen = this.select.value;
    const named = this.colours.find(({ name }) => name === chosen);
    if (chosen === OTHER) this.swatch.value = this.otherHex;
    else if (named) this.swatch.value = named.hex;
    else if (this.colours.length) this.swatch.value = darkest(this.colours).hex;
  }
}

/** The ink, as the server chooses it: the colour with the least light. */
function darkest(colours) {
  return colours.reduce((dark, colour) => (luminance(colour.hex) < luminance(dark.hex) ? colour : dark));
}

function luminance(hex) {
  const [red, green, blue] = [1, 3, 5].map((start) => {
    const channel = parseInt(hex.slice(start, start + 2), 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}
