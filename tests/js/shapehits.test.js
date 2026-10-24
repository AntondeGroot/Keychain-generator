// What the pointer is on among the mask's shapes.

import assert from "node:assert/strict";
import { test } from "node:test";

import { edgeNear } from "../../src/keychain/web/static/shapehits.js";

const REACH = 2;

test("an edge gives a circle's rim its diameter, a rectangle's top or bottom its width, a side its height, the topmost first", () => {
  const rect = { rect: { x: 10, y: 20, width: 40, height: 30, radii: [0, 0, 0, 0] } };
  const circle = { circle: { centre: [50, 50], radius: 10 } }; // drawn later, over the rectangle's bottom right
  const steps = [rect, circle];
  const hit = (x, y) => edgeNear(steps, [x, y], REACH);
  assert.deepEqual(hit(30, 21), { step: rect, name: "width" }); // top
  assert.deepEqual(hit(30, 50), { step: rect, name: "width" }); // bottom
  assert.deepEqual(hit(9, 35), { step: rect, name: "height" }); // left
  assert.deepEqual(hit(50, 30), { step: rect, name: "height" }); // right
  assert.deepEqual(hit(40, 50), { step: circle, name: "diameter" }); // where the rim crosses the bottom
  assert.equal(hit(30, 35), null); // inside, away from every edge
});
