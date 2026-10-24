// Every module of the page loads, and every name a module imports from another is one that module
// exports: a name misspelt or moved stops the whole page from loading, which the syntax check
// does not see. Loading them all also makes the coverage count every module, not only the ones
// other tests happen to load.

import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";

const STATIC = new URL("../../src/keychain/web/static/", import.meta.url);
const WIRES_THE_PAGE = "main.js"; // looks up the page's elements as it loads, so only a browser runs it
const NAMED_IMPORT = /^import \{([^}]*)\} from "\.\/([^"]+)";/gm;

globalThis.window ??= globalThis; // projectfile.js asks the browser whether it can write files

test("every module loads and imports only names the module it imports from exports", async () => {
  const modules = readdirSync(STATIC).filter((name) => name.endsWith(".js"));
  assert.ok(modules.includes(WIRES_THE_PAGE), `no page modules in ${STATIC.pathname}`);
  for (const name of modules) {
    for (const [, names, from] of readFileSync(new URL(name, STATIC), "utf8").matchAll(NAMED_IMPORT)) {
      const exported = await import(new URL(from, STATIC));
      for (const imported of names.split(",").map((one) => one.trim()).filter(Boolean)) {
        assert.ok(imported in exported, `${name} imports ${imported}, which ${from} does not export`);
      }
    }
    if (name !== WIRES_THE_PAGE) await import(new URL(name, STATIC));
  }
});
