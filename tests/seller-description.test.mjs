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

test("сохраняет следы окраски и среднюю оценку состояния в частом шаблоне", () => {
  const original =
    "外观：漆面保养良好，车身结构无修复，无重大事故。内饰：干净整洁。安全指示灯正常，气囊等被动安全项正常，车辆内电子器件使用良好，车内静态动态设备完善。驾驶：车辆点火、起步、提速、过弯、减速、制动均无问题，加速迅猛，动力输出平稳舒适,无怠速抖动。整体：整体车况一般。车体骨架结构无变形扭曲、无火烧泡水痕迹。车身有喷漆痕迹，整体漆面良好，排除大事故车辆。视野宽阔，练手选择，空间宽敞明亮通风性好，适合家庭代步车。";
  const result = sellerDescription(original);
  assert.equal(result.dictionary, true);
  assert.match(result.text, /следы окраски/);
  assert.match(result.text, /как среднее/);
});
