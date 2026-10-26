import assert from "node:assert/strict";
import { test } from "node:test";

import { handTools } from "../../src/keychain/web/static/handtools.js";

test("the brush's size shows for the brushes and for marking with the brush, never for shapes or cut", () => {
  const painter = { mask: { method: "brush" } };
  const tools = handTools(painter);
  const brushing = () => Object.keys(tools).filter((name) => tools[name].brushing?.());

  assert.deepEqual(brushing(), ["paint", "smooth", "detailed", "erase-details", "erase-paint", "background", "keep", "erase-mask"]);
  painter.mask.method = "circle";
  assert.deepEqual(brushing(), ["paint", "smooth", "detailed", "erase-details", "erase-paint"]);
});
