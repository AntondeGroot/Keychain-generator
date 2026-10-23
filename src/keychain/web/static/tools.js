// The buttons that say what dragging over the picture does: a drawing tool, painting with a
// colour, or picking a colour from the picture. Pressing a chosen one again puts it away. How
// background and keep are marked, with the brush or a shape, is chosen apart.

const PAINTING = ["paint", "spline"]; // the tools that paint in the paint colour
const MASK_TOOLS = ["background", "keep", "erase-mask"];

import { setStatus } from "./server.js";

export class ToolButtons {
  /** onPick hears the colour picked from the picture. */
  constructor(painter, pickButton, onPick) {
    this.painter = painter;
    this.pickButton = pickButton;
    this.onPick = onPick;
    pickButton.addEventListener("click", () => this.#togglePicking());
    for (const button of document.querySelectorAll(".tool")) button.addEventListener("click", () => this.choose(button));
    for (const button of document.querySelectorAll(".method")) button.addEventListener("click", () => this.#markWith(button));
  }

  /** Chooses the tool, or puts it away when it was already chosen: then dragging over the
   * picture does nothing, so it cannot be painted on by accident. */
  choose(button) {
    const chosen = button.getAttribute("aria-pressed") === "true" ? null : button;
    for (const tool of document.querySelectorAll(".tool")) tool.setAttribute("aria-pressed", String(tool === chosen));
    this.painter.setTool(chosen?.dataset.tool ?? null);
  }

  /** The colour the brush and the spline paint in. Choosing one by hand picks up the brush,
   * unless a tool that paints is in hand already. */
  paintIn(hex, name, byHand) {
    this.painter.setPaintColour(hex, name);
    if (byHand && !PAINTING.includes(this.painter.tool)) this.choose(document.querySelector('.tool[data-tool="paint"]'));
  }

  /** Choosing how to mark takes up the background tool, unless one of the mask's tools is in hand. */
  #markWith(button) {
    for (const method of document.querySelectorAll(".method")) method.setAttribute("aria-pressed", String(method === button));
    this.painter.setMaskMethod(button.dataset.method);
    if (!MASK_TOOLS.includes(this.painter.tool)) this.choose(document.querySelector('.tool[data-tool="background"]'));
  }

  #togglePicking() {
    const picking = this.pickButton.getAttribute("aria-pressed") !== "true";
    this.pickButton.setAttribute("aria-pressed", String(picking));
    this.painter.pickColours(picking ? (hex) => this.#picked(hex) : null);
    if (picking) setStatus("Click on the picture to add the colour there.");
  }

  #picked(hex) {
    this.onPick(hex);
    this.#togglePicking();
  }
}
