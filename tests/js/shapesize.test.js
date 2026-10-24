// The sizes of the shape chosen on the mask, typed in mm.

import assert from "node:assert/strict";
import { test } from "node:test";

import { ShapeSize } from "../../src/keychain/web/static/shapesize.js";

const PIXEL_MM = 0.5;

globalThis.document = { activeElement: null }; // no field has the focus, so every one shows its size

/** A field for one size, which hears a value typed as the page's would. */
function field(size) {
  const listeners = [];
  const label = { hidden: false };
  return {
    dataset: { size },
    value: "",
    closest: () => label,
    addEventListener: (_, listener) => listeners.push(listener),
    type(value) {
      this.value = value;
      for (const listener of listeners) listener();
    },
  };
}

test("with the fillet a radius typed rounds every corner chosen, and the corners chosen after it", () => {
  const radius = field("radius");
  const box = { hidden: true, querySelectorAll: () => [field("width"), field("height"), radius] };
  const sizes = new ShapeSize(box, () => {});
  sizes.setScale(PIXEL_MM);
  sizes.setFilleting(true);
  const step = { rect: { x: 0, y: 0, width: 40, height: 30, radii: [0, 0, 0, 0] } };
  const corners = (...numbers) => numbers.map((corner) => ({ step, corner }));

  sizes.fillet(corners(0, 1), corners(0, 1));
  assert.deepEqual(step.rect.radii, [4, 4, 0, 0]); // 2 mm, until another radius is typed
  radius.type("3");
  assert.deepEqual(step.rect.radii, [6, 6, 0, 0]);
  sizes.fillet(corners(0, 1, 2), corners(2));
  assert.deepEqual(step.rect.radii, [6, 6, 6, 0]);
  assert.equal(radius.value, "3.0");
});
