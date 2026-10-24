// The rectangle and circle shapes of the mask: their handles, sizes and corner radii.

import assert from "node:assert/strict";
import { test } from "node:test";

import { handles, resize } from "../../src/keychain/web/static/shapekinds.js";

const TOP_RIGHT = 1;
const BOTTOM_RIGHT = 2; // its opposite corner, the top left, stays put while it is dragged

/** A rectangle 40 wide and 30 high with its top left at (10, 20), its width dimensioned. */
function widthDimensioned() {
  return { rect: { x: 10, y: 20, width: 40, height: 30, radii: [0, 0, 0, 0] }, dims: ["width"] };
}

test("a corner dragged keeps a dimensioned width, on whichever side of the opposite corner the pointer is", () => {
  const right = widthDimensioned();
  handles(right)[BOTTOM_RIGHT].drag([90, 60]);
  assert.deepEqual(right.rect, { x: 10, y: 20, width: 40, height: 40, radii: [0, 0, 0, 0] });

  const left = widthDimensioned();
  handles(left)[BOTTOM_RIGHT].drag([5, 60]);
  assert.deepEqual(left.rect, { x: -30, y: 20, width: 40, height: 40, radii: [0, 0, 0, 0] });
});

test("a corner radius is never more than half the shorter side, set for all four corners or for one", () => {
  const step = widthDimensioned(); // 30 high, so no radius above 15
  resize(step, "radius", 50);
  assert.deepEqual(step.rect.radii, [15, 15, 15, 15]);

  resize(step, "radius", 5, TOP_RIGHT);
  assert.deepEqual(step.rect.radii, [15, 5, 15, 15]);
  resize(step, "radius", 20, TOP_RIGHT);
  assert.deepEqual(step.rect.radii, [15, 15, 15, 15]);
});
