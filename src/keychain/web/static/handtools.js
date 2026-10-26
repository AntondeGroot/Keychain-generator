// The tools that can be in hand over the picture, by name, all answering the pointer alike:
// down (true to keep the pointer until let go), move, up, leave, the guide to show, and cancel
// for Esc. pickUp and putDown are told when the tool is chosen and put away; remove for Delete;
// brushing says whether it paints with the brush, so the brush's size shows under the pointer.

import { MASK_ACTIONS } from "./masktool.js";
import { ERASERS } from "./paintlayers.js";

const BRUSHES = ["paint", "smooth", "detailed", "erase-details", "erase-paint"];

/** The tools by name, working on the painter's layers and drawings. */
export function handTools(painter) {
  const tools = {
    connect: {
      down: (point) => painter.lines.click(point) && painter.onPainted(),
      guide: () => painter.lines.guide(),
      cancel: () => painter.lines.cancel(),
    },
    spline: {
      down: (point, event) => painter.spline.down(point, !event.altKey),
      move: (point, event) => painter.spline.move(point, !event.altKey),
      up: () => painter.spline.up(),
      leave: () => {
        painter.curves.hover(null, false);
        painter.spline.leave();
      },
      guide: () => painter.curves.guide(painter.paintColourName),
      cancel: () => painter.curves.cancel(),
      pickUp: () => painter.spline.start(),
      putDown: () => painter.spline.stop(),
    },
    "turn-text": {
      down: (point) => painter.turned.click(point) && painter.onPainted(),
      move: (point) => painter.turned.hover(point),
      leave: () => painter.turned.hover(null),
      guide: () => painter.turned.guide(),
      cancel: () => painter.turned.cancel(),
    },
  };
  for (const name of BRUSHES) tools[name] = new Brush(painter, name);
  for (const [name, action] of Object.entries(MASK_ACTIONS)) tools[name] = maskTool(painter, name, action);
  return tools;
}

/** Background, keep or erase on the mask, with the brush or a shape. */
function maskTool(painter, name, action) {
  const { mask } = painter;
  return {
    down: (point) => mask.down(point, action, painter.brushWidth()),
    move: (point) => mask.move(point),
    up: () => mask.up(action),
    leave: () => mask.leave(action),
    guide: () => mask.guide(action),
    cancel: () => mask.cancel(),
    remove: () => mask.remove(),
    brushing: () => mask.method === "brush" && action !== "cut",
    pickUp: () => mask.inHand(true),
    putDown: () => mask.inHand(false),
  };
}

/** Paint, details or their erasers, which take off connect lines or curves along the way. */
class Brush {
  constructor(painter, name) {
    this.painter = painter;
    this.name = name;
    this.last = null;
  }

  down(point) {
    this.last = point;
    this.#stroke(point, point);
    return true;
  }

  move(point) {
    if (!this.last) return;
    this.#stroke(this.last, point);
    this.last = point;
  }

  up() {
    if (!this.last) return;
    this.last = null;
    this.painter.onPainted(this.name);
  }

  leave() {
    this.up();
  }

  guide() {
    return "";
  }

  brushing() {
    return true;
  }

  cancel() {}

  #stroke(from, to) {
    const { painter } = this;
    const eraser = ERASERS[this.name];
    const width = painter.brushWidth();
    const erasedLines = eraser?.lines && painter.lines.eraseNear(to, width / 2);
    const erasedCurves = eraser?.curves && painter.curves.eraseNear(to, width / 2);
    if (erasedLines || erasedCurves) painter.onPainted();
    painter.layers.stroke(this.name, from, to, width, painter.paintColour);
  }
}
