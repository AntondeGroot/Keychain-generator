// The layers painted with a brush, in the picture's own size so the server can lay them over
// pixel for pixel: "paint" with a filament colour, "mask" for background (red) and keep (green),
// "detail" for smooth (blue) and detailed (yellow). Each section has its eraser.

import { loadedImage } from "./project.js";

/** What each eraser takes off: its layers, and the connect lines or the curves drawn over them. */
export const ERASERS = {
  "erase-mask": { layers: ["mask"] },
  "erase-details": { layers: ["detail"], lines: true },
  "erase-paint": { layers: ["paint"], curves: true },
};

const BRUSHES = {
  background: { layer: "mask", colour: "#ff0000" },
  keep: { layer: "mask", colour: "#00ff00" },
  smooth: { layer: "detail", colour: "#0000ff" },
  detailed: { layer: "detail", colour: "#ffff00" },
  paint: { layer: "paint", colour: null }, // in the paint colour
};

export class PaintLayers {
  /** canvases: the painting canvases by name. */
  constructor(canvases) {
    this.canvases = canvases;
    this.painted = new Set();
  }

  get names() {
    return Object.keys(this.canvases);
  }

  clear(names) {
    for (const name of names) {
      const canvas = this.canvases[name];
      canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
      this.painted.delete(name);
    }
  }

  /** Layers saved in a project, as PNG data URLs; null if unpainted. */
  async restore(dataUrls) {
    for (const [name, dataUrl] of Object.entries(dataUrls)) {
      if (!dataUrl || !this.canvases[name]) continue;
      this.canvases[name].getContext("2d").drawImage(await loadedImage(dataUrl), 0, 0);
      this.painted.add(name);
    }
  }

  /** One layer as a PNG data URL, or null when nothing was painted on it. */
  dataUrl(name) {
    return this.painted.has(name) ? this.canvases[name].toDataURL("image/png") : null;
  }

  /** A stroke of the brush or eraser named, width wide in picture pixels. */
  stroke(tool, from, to, width, paintColour) {
    const eraser = ERASERS[tool];
    for (const name of eraser ? eraser.layers : [BRUSHES[tool].layer]) {
      const context = this.canvases[name].getContext("2d");
      context.globalCompositeOperation = eraser ? "destination-out" : "source-over";
      context.strokeStyle = eraser ? "#000000" : (BRUSHES[tool].colour ?? paintColour);
      context.lineWidth = width;
      context.lineCap = "round";
      context.lineJoin = "round";
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
      context.stroke();
      if (!eraser) this.painted.add(name);
    }
  }
}
