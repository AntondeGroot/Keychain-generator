// Dimensions on the mask's shapes: where their values show, and what those values read.

import assert from "node:assert/strict";
import { test } from "node:test";

import { inMm, labelNear } from "../../src/keychain/web/static/dimensions.js";

test("a click finds the dimension whose value it is on, only for sizes dimensioned, and further off when zoomed out", () => {
  const rect = { rect: { x: 10, y: 20, width: 40, height: 30, radii: [0, 0, 0, 0] }, dims: ["width", "height"] };
  const circle = { circle: { centre: [100, 50], radius: 10 } }; // its diameter not dimensioned
  const steps = [rect, circle];
  assert.deepEqual(labelNear(steps, [30, -8], 1), { step: rect, name: "width" }); // above the top, twice the line's offset
  assert.deepEqual(labelNear(steps, [85, 35], 1), { step: rect, name: "height" }); // right of the side
  assert.equal(labelNear(steps, [100, 26], 1), null); // where the circle's diameter would show
  // Zoomed out to two picture pixels a screen pixel, the value stands off further, at (30, -36),
  // and a click reaches twice as far: 24 above it is still on it.
  assert.equal(labelNear(steps, [30, -36], 1), null);
  assert.deepEqual(labelNear(steps, [30, -60], 2), { step: rect, name: "width" });
});

test("a dimension's value is its size in mm, to one decimal", () => {
  const rect = { rect: { x: 10, y: 20, width: 40, height: 30, radii: [0, 0, 0, 0] } };
  const circle = { circle: { centre: [100, 50], radius: 10 } };
  const PIXEL_MM = 0.256;
  assert.equal(inMm({ step: rect, name: "width" }, PIXEL_MM), "10.2"); // 10.24 mm
  assert.equal(inMm({ step: rect, name: "height" }, PIXEL_MM), "7.7"); // 7.68 mm, rounded up
  assert.equal(inMm({ step: circle, name: "diameter" }, PIXEL_MM), "5.1"); // twice the radius: 5.12 mm
});
