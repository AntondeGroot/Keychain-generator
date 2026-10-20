// The keychain preview from the server. In placing mode, a click reports the spot in mm.

export class Preview {
  constructor(container, onPlace) {
    this.container = container;
    this.onPlace = onPlace;
    this.placing = false;
    container.addEventListener("click", (event) => this.#click(event));
  }

  show(svgText) {
    // The SVG comes from our own server, built from numbers and checked colour names.
    this.container.innerHTML = svgText;
  }

  setPlacing(placing) {
    this.placing = placing;
    this.container.classList.toggle("placing", placing);
  }

  #click(event) {
    const svg = this.container.querySelector("svg");
    if (!this.placing || !svg) return;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    this.onPlace([point.x, -point.y]); // SVG's y points down, the keychain's up
  }
}
