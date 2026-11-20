import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const directory = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(directory, "../src/lib/seller-description.ts"), "utf8");
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;
const compiled = { exports: {} };
new Function("module", "exports", javascript)(compiled, compiled.exports);
const { sellerDescription } = compiled.exports;

test("сохраняет предупреждение о неподтверждённом пробеге", () => {
  const result = sellerDescription("原漆，不保实表");
  assert.equal(result.dictionary, true);
  assert.match(result.text, /пробега продавец не гарантирует/);
});

test("не теряет сведения о ДТП и изменённом пробеге", () => {
  const result = sellerDescription("此车为事故车 调表车");
  assert.match(result.text, /после ДТП/);
  assert.match(result.text, /пробега изменены/);
});

test("переводит набор знакомых фраз только целиком", () => {
  assert.equal(sellerDescription("原漆，无事故，无火烧").dictionary, true);
  assert.equal(sellerDescription("原漆，无事故，发动机损坏").translated, false);
  assert.equal(sellerDescription("无事故，但已维修").translated, false);
});

test("оставляет неизвестный оригинал целым", () => {
  const original = "【车况】\n右后门喷漆";
  assert.deepEqual(sellerDescription(original), {
    text: original,
    translated: false,
    dictionary: false,
  });
  assert.equal(sellerDescription(null), null);
  assert.equal(sellerDescription("   "), null);
  assert.equal(sellerDescription("__proto__").text, "__proto__");
});
