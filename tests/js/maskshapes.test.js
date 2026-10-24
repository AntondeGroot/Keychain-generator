// The mask's shapes as the pointer works on them: chosen, filleted and dimensioned.

import assert from "node:assert/strict";
import { test } from "node:test";

import { MaskShapes } from "../../src/keychain/web/static/maskshapes.js";

const ONE_TO_ONE = () => 1; // canvas pixels per screen pixel, so a click reaches 8 picture pixels

/** A canvas whose drawing goes nowhere: the shapes are hidden, so it is only ever cleared. */
const NO_CANVAS = { width: 0, height: 0, getContext: () => new Proxy({}, { get: () => () => {} }) };

/** The shapes, with one rectangle 40 by 30 at (10, 20), and the fillet's choices as corner numbers. */
function oneRectangle() {
  const rect = { action: "keep", rect: { x: 10, y: 20, width: 40, height: 30, radii: [0, 0, 0, 0] } };
  const heard = [];
  const corners = (chosen) => chosen.map(({ corner }) => corner); // the only rectangle there is
  const on = { fillet: (chosen, added) => heard.push({ chosen: corners(chosen), added: corners(added) }) };
  const shapes = new MaskShapes(NO_CANVAS, ONE_TO_ONE, { steps: [rect] }, on);
  const click = (x, y) => shapes.down({ x, y }, "keep", "fillet");
  return { click, heard };
}

test("with the fillet a corner clicked is chosen and no longer, its outline chooses all four, and away none", () => {
  const { click, heard } = oneRectangle();
  click(50, 20); // the top right corner
  click(30, 50); // the bottom edge, away from the corners
  click(50, 20);
  click(200, 200);
  assert.deepEqual(heard, [
    { chosen: [1], added: [1] },
    { chosen: [1, 0, 2, 3], added: [0, 2, 3] },
    { chosen: [0, 2, 3], added: [] },
    { chosen: [], added: [] },
  ]);
});
