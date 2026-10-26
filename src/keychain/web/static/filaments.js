// How many filaments the keychain needs, which is what a printer has to load: a dark or light
// shade is printed in a filament already there, so only a colour of its own counts.

const OTHER_RIM = "#"; // a rim colour that is not one of the picture's is given as its hex

/** The filaments to load: each colour that is not a shade of another, and the rim's colour when it
 * is one of its own; each once, however often it is listed. */
export function filamentsOf(colours, rim) {
  const own = colours.filter(({ shade }) => !shade).map(({ name, hex }) => ({ name, hex: hex.toLowerCase() }));
  if (rim?.startsWith(OTHER_RIM)) own.push({ name: "rim", hex: rim.toLowerCase() });
  return own.filter((colour, index) => own.findIndex(({ hex }) => hex === colour.hex) === index);
}

/** The count over the colour list, with a dot of each filament and how many shades they print. */
export function showFilaments(box, colours, rim) {
  const filaments = filamentsOf(colours, rim);
  const shades = colours.filter(({ shade }) => shade).length;
  const dots = filaments.map(({ name, hex }) => {
    const dot = Object.assign(document.createElement("span"), { className: "dot", title: name || hex });
    dot.style.setProperty("--swatch", hex);
    return dot;
  });
  const count = Object.assign(document.createElement("strong"), { textContent: plural(filaments.length, "filament") });
  const extra = shades ? [Object.assign(document.createElement("small"), { textContent: `+ ${plural(shades, "shade")}` })] : [];
  box.replaceChildren(count, ...dots, ...extra);
  box.hidden = !filaments.length;
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}
