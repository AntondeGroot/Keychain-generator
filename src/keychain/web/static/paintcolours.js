// The colour to paint in, by brush or spline: one swatch per colour, the chosen one pressed.
// A colour removed from the list gives way to the first one left.

export class PaintColours {
  /** onChoose hears the colour chosen, by its hex and name. */
  constructor(list, onChoose) {
    this.list = list;
    this.onChoose = onChoose;
    this.colours = [];
    this.chosen = null;
  }

  /** The swatches follow the colours, keeping the one chosen. */
  follow(colours) {
    this.colours = colours;
    const chosen = colours.find(({ hex }) => hex === this.chosen) ?? colours[0];
    this.list.replaceChildren(...colours.map((colour) => this.#swatch(colour)));
    if (chosen) this.#choose(chosen, false);
  }

  #swatch({ name, hex }) {
    const button = Object.assign(document.createElement("button"), { type: "button", textContent: name || hex });
    button.dataset.hex = hex;
    button.style.setProperty("--swatch", hex);
    button.setAttribute("aria-label", `Paint in ${name || hex}`);
    button.addEventListener("click", () => this.#choose({ name, hex }, true));
    return button;
  }

  #choose({ name, hex }, byHand) {
    this.chosen = hex;
    for (const button of this.list.children) button.setAttribute("aria-pressed", String(button.dataset.hex === hex));
    this.onChoose(hex, name, byHand);
  }
}
