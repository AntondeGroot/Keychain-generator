// Splines drawn by hand through clicked points.

import assert from "node:assert/strict";
import { test } from "node:test";

import { spline } from "../../src/keychain/web/static/handdrawn.js";

const SAMPLES_PER_SPAN = 24; // as on the server, so the page shows the curve that gets made
const CLICKED = [
  [0, 0],
  [30, 10],
  [40, 40],
  [10, 30],
];

/** Every sample that starts a span, from one clicked point to the next, and the last one. */
function throughPoints(samples) {
  return samples.filter((_, index) => index % SAMPLES_PER_SPAN === 0);
}

test("a spline runs through every point clicked, open from the first to the last, closed back round to the first", () => {
  assert.deepEqual(throughPoints(spline(CLICKED, false)), CLICKED);
  assert.deepEqual(throughPoints(spline(CLICKED, true)), [...CLICKED, CLICKED[0]]);
});
