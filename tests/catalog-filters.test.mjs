import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";
function load(path, imports = {}) {
  const module = { exports: {} };
  const source = ts.transpileModule(fs.readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  vm.runInNewContext(
    source,
    { module, exports: module.exports, URLSearchParams, Date, require: (name) => imports[name] },
    { filename: path },
  );
  return module.exports;
}
const filters = load("../src/lib/catalog-filters.ts");
const data = load("../src/lib/catalog-data.ts", {
  "./catalog-filters": filters,
  "@/lib/db": {},
  "next/cache": { unstable_cache: (f) => f },
});
test("unsafe and malformed URL values do not become SQL or negative pagination", () => {
  const f = filters.parseFilters({
    brand: "'; DROP TABLE cars;--",
    page: "-4",
    sort: "__proto__",
    yearFrom: "no",
    body: "suv,not-a-body,constructor",
    mileageTo: "100000000000",
  });
  assert.equal(f.sort, "newest");
  assert.equal(f.brand, "");
  assert.equal(f.page, 1);
  assert.equal(f.yearFrom, undefined);
  assert.equal(f.mileageTo, undefined);
  assert.equal(f.bodies.join(","), "suv");
});
test("multi-model URLs and repeated no-JS fields share one state", () => {
  const f = filters.parseFilters({
    brand: "Mercedes-Benz",
    model: ["glc,e-class", "glc"],
    body: "suv,wagon",
    sort: "price_asc",
    page: "2",
  });
  const roundtrip = filters.parseFilters(Object.fromEntries(filters.filterParams(f)));
  assert.equal(roundtrip.brand, "mercedes-benz");
  assert.equal(roundtrip.models.join(","), "glc,e-class");
  assert.equal(roundtrip.page, 2);
});
test("inverted ranges are ignored and orphan models are cleared", () => {
  const f = filters.parseFilters({ model: "glc", yearFrom: "2023", yearTo: "2021" });
  assert.equal(f.models.length, 0);
  assert.equal(f.yearFrom, undefined);
  assert.equal(f.yearTo, undefined);
});
test("brand counts exclude brand and models, model counts exclude only models", () => {
  const f = filters.parseFilters({
    brand: "mazda",
    model: "3,cx-30",
    body: "suv",
    yearFrom: "2021",
    priceTo: "3000000",
  });
  const brands = data.catalogWhere(f, "brand"),
    models = data.catalogWhere(f, "model"),
    list = data.catalogWhere(f);
  assert.ok(!brands.sql.includes("b.slug="));
  assert.ok(!brands.sql.includes("model_slug="));
  assert.ok(brands.sql.includes("body_slug="));
  assert.ok(models.sql.includes("b.slug="));
  assert.ok(!models.sql.includes("model_slug="));
  assert.ok(list.sql.includes("c.price_rub<="));
  assert.ok(!list.sql.includes("c.price_cny<="));
  assert.equal(list.values.at(-1), 3000000);
  assert.ok(!list.sql.includes("mazda"));
});
