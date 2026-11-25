import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";
function load(path) {
  const loadedModule = { exports: {} };
  vm.runInNewContext(
    ts.transpileModule(fs.readFileSync(new URL(path, import.meta.url), "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    { module: loadedModule, exports: loadedModule.exports, URL },
  );
  return loadedModule.exports;
}
const { originalListingUrl } = load("../src/lib/original-listing.ts");
test("keeps the original listing and opens only the clean HTTPS address", () => {
  assert.equal(
    originalListingUrl(
      "http://www.che168.com/dealer/494346/60289695.html?tracking=1#pic",
      "60289695",
    ),
    "https://www.che168.com/dealer/494346/60289695.html",
  );
});
test("rejects wrong listing, external hosts, credentials and script URLs", () => {
  for (const raw of [
    null,
    "javascript:alert(1)",
    "https://che168.com.evil.test/dealer/1/60289695.html",
    "https://user@www.che168.com/dealer/1/60289695.html",
    "https://www.che168.com/dealer/1/999.html",
    "broken",
  ])
    assert.equal(originalListingUrl(raw, "60289695"), null);
});
