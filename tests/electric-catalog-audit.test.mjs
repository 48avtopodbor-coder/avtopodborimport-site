import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";
import { auditElectricRows } from "../scripts/electric_catalog_audit.mjs";
function load(path) {
  const loadedModule = { exports: {} };
  const source = ts.transpileModule(fs.readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  vm.runInNewContext(source, { module: loadedModule, exports: loadedModule.exports });
  return loadedModule.exports;
}
const helpers = {
  ...load("../src/lib/car-title.ts"),
  ...load("../src/lib/electric-range.ts"),
  ...load("../src/lib/format.ts"),
};
const car = {
  listing_id: "1",
  brand_ru: "BYD",
  brand_id: 1,
  brand_name: "BYD",
  model: "海豚 2021款 405km 时尚版",
  model_name: "Dolphin",
  model_slug: "dolphin",
  year: 2022,
  car_fuel: "электро",
  spec_fuel: "электро",
  params_json: JSON.stringify([
    [
      "基本参数",
      [
        ["车型名称", "海豚 2021款 405km 时尚版"],
        ["NEDC纯电续航里程(km)", "405"],
      ],
    ],
  ]),
};
test("audit uses frontend helpers and counts a valid range once per car", () => {
  const r = auditElectricRows([car, { ...car, listing_id: "2" }], helpers);
  assert.equal(r.cars, 2);
  assert.equal(r.named, 2);
  assert.equal(r.with_range, 2);
  assert.equal(r.models, 1);
  assert.equal(r.cycles.NEDC, 2);
  assert.equal(r.errors, 0);
  assert.equal(r.warnings, 0);
});
test("unmapped model is caught even when legacy fallback produces a title", () => {
  const r = auditElectricRows([{ ...car, model_name: null, model_slug: null }], helpers);
  assert.ok(r.issues.some((x) => x.code === "missing_mapped_name"));
});
test("numeric Zeekr model is valid; import-marker punctuation is harmless", () => {
  const r = auditElectricRows(
    [
      {
        ...car,
        brand_name: "Zeekr",
        model_name: "001",
        model_slug: "001",
        model: "极氪001 2022款",
        params_json: [
          [
            "基本参数",
            [
              ["车型名称", "极氪001 2022款"],
              ["CLTC纯电续航里程(km)", "732"],
            ],
          ],
        ],
      },
      {
        ...car,
        model: "奥迪e-tron进口 2021款",
        params_json: [
          [
            "基本参数",
            [
              ["车型名称", "奥迪e-tron(进口) 2021款"],
              ["NEDC纯电续航里程(km)", "465"],
            ],
          ],
        ],
      },
    ],
    helpers,
  );
  assert.equal(r.errors, 0);
  assert.equal(r.warnings, 0);
});
test("conflicting cycle values and fuel disagreement are explicit audit errors", () => {
  const r = auditElectricRows(
    [
      {
        ...car,
        spec_fuel: "гибрид PHEV",
        params_json: [
          [
            "基本参数",
            [
              ["NEDC纯电续航里程(km)", "405"],
              ["NEDC纯电续航里程(km)", "500"],
            ],
          ],
        ],
      },
    ],
    helpers,
  );
  assert.ok(r.issues.some((x) => x.code === "conflicting_cycle_values"));
  assert.ok(r.issues.some((x) => x.code === "fuel_mismatch"));
  assert.ok(r.issues.some((x) => x.code === "missing_range"));
});
test("stale specification titles are reviewable, without changing source data", () => {
  const original = {
    ...car,
    model: "ID.4 CROZZ 2024款 PURE+",
    params_json: [
      [
        "基本参数",
        [
          ["车型名称", "ID.4 CROZZ 2022款 长续航PURE+版"],
          ["CLTC纯电续航里程(km)", "600"],
        ],
      ],
    ],
  };
  const r = auditElectricRows([original], helpers);
  assert.equal(r.errors, 0);
  assert.equal(r.warnings, 1);
  assert.equal(r.issues[0].code, "spec_title_mismatch");
  assert.equal(original.model, "ID.4 CROZZ 2024款 PURE+");
});
