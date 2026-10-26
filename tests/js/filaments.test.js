import assert from "node:assert/strict";
import { test } from "node:test";

import { filamentsOf } from "../../src/keychain/web/static/filaments.js";

test("a dark or light shade is printed in a filament already loaded, so it needs none of its own", () => {
  const colours = [
    { name: "black", hex: "#000000" },
    { name: "red", hex: "#e03838" },
    { name: "darkred", hex: "#8b1a1a", shade: { of: 1, tone: "dark" } },
    { name: "pink", hex: "#f4a0a0", shade: { of: 1, tone: "light" } },
  ];

  assert.deepEqual(filamentsOf(colours, null), [
    { name: "black", hex: "#000000" },
    { name: "red", hex: "#e03838" },
  ]);
});

test("two colours alike are one filament, whatever the case their hex is written in", () => {
  const colours = [
    { name: "white", hex: "#FFFFFF" },
    { name: "snow", hex: "#ffffff" },
    { name: "black", hex: "#000000" },
  ];

  assert.deepEqual(filamentsOf(colours, null), [
    { name: "white", hex: "#ffffff" },
    { name: "black", hex: "#000000" },
  ]);
});

test("a rim in a colour of its own is one more filament, unless that colour is loaded already", () => {
  const colours = [
    { name: "black", hex: "#000000" },
    { name: "red", hex: "#e03838" },
  ];

  assert.deepEqual(filamentsOf(colours, "#2E7D32"), [...colours, { name: "rim", hex: "#2e7d32" }]);
  assert.deepEqual(filamentsOf(colours, "#E03838"), colours);
  assert.deepEqual(filamentsOf(colours, "red"), colours); // one of the picture's colours, by name
});
