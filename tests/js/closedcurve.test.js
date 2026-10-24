// Closed curves given as samples: what is inside them, and how far a point is from their line.

import assert from "node:assert/strict";
import { test } from "node:test";

import { distanceToCurve, insideCurve } from "../../src/keychain/web/static/closedcurve.js";

/** A 10 by 10 square with its top right quarter, from (4, 4), cut out of it: an L. */
const L_SHAPE = [
  [0, 0],
  [10, 0],
  [10, 4],
  [4, 4],
  [4, 10],
  [0, 10],
];

test("a point is inside a curve that bends in on itself only where the curve encloses it", () => {
  assert.equal(insideCurve(L_SHAPE, [2, 7]), true); // in the upright of the L
  assert.equal(insideCurve(L_SHAPE, [7, 2]), true); // in its foot
  assert.equal(insideCurve(L_SHAPE, [7, 7]), false); // in the corner cut out
  assert.equal(insideCurve(L_SHAPE, [-2, 2]), false); // left of it, where a ray to the right crosses it twice
});

test("a point's distance from a curve is to its nearest edge, or to a corner where it is beyond the ends of the edges", () => {
  assert.equal(distanceToCurve(L_SHAPE, [2, 5]), 2); // inside, nearest the left edge
  assert.equal(distanceToCurve(L_SHAPE, [7, 7]), 3); // in the corner cut out, as far from both edges round it
  assert.equal(distanceToCurve(L_SHAPE, [13, -4]), 5); // beyond the top right corner, 3 across and 4 up from it
});
