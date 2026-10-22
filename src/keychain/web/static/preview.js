// The keychain preview from the server. In placing mode, a ring of the keychain's size follows
// the pointer to show where it would end up, and a click reports the spot in mm.

const SVG = "http://www.w3.org/2000/svg";

export class Preview {
  constructor(container, onPlace) {
    this.container = container;
    this.onPlace = onPlace;
    this.placing = false;
    this.ring = null; // radii in mm of the hole and of the ring around it, from the server
    container.addEventListener("click", (event) => this.#click(event));
    container.addEventListener("pointermove", (event) => this.#follow(event));
    container.addEventListener("pointerleave", () => this.#ghost()?.setAttribute("visibility", "hidden"));
  }

  show(svgText, ring) {
    // The SVG comes from our own server, built from numbers and checked colour names.
    this.container.innerHTML = svgText;
    this.ring = ring;
  }

  setPlacing(placing) {
    this.placing = placing;
    this.container.classList.toggle("placing", placing);
    if (!placing) this.#ghost()?.setAttribute("visibility", "hidden");
  }

  #click(event) {
    const point = this.#inMm(event);
    if (this.placing && point) this.onPlace(point);
  }

  #follow(event) {
    const point = this.#inMm(event);
    if (!this.placing || !point || !this.ring) return;
    const ghost = this.#ghost() ?? this.#newGhost();
    ghost.setAttribute("transform", `translate(${point[0]} ${-point[1]})`);
    ghost.setAttribute("visibility", "visible");
  }

  /** Where the pointer is on the keychain, in mm; SVG's y points down, the keychain's up. */
  #inMm(event) {
    const svg = this.container.querySelector("svg");
    if (!svg) return null;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return [point.x, -point.y];
  }

  #ghost() {
    return this.container.querySelector("#ring-ghost");
  }

  /** The ring with its hole, around (0, 0), moved under the pointer from then on. */
  #newGhost() {
    const ghost = document.createElementNS(SVG, "g");
    ghost.id = "ring-ghost";
    for (const [radius, part] of [[this.ring.outer_mm, "ring"], [this.ring.hole_mm, "hole"]]) {
      const circle = document.createElementNS(SVG, "circle");
      circle.setAttribute("r", radius);
      circle.setAttribute("class", part);
      ghost.append(circle);
    }
    this.container.querySelector("svg").append(ghost);
    return ghost;
  }
}
