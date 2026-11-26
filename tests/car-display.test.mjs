import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as jsx from "react/jsx-runtime";
function load(path, imports = {}) {
  const loadedModule = { exports: {} };
  const source = ts.transpileModule(fs.readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  vm.runInNewContext(source, {
    module: loadedModule,
    exports: loadedModule.exports,
    URLSearchParams,
    require: (name) => imports[name],
  });
  return loadedModule.exports;
}
const titles = load("../src/lib/car-title.ts");
const format = load("../src/lib/format.ts");
const { electricRange } = load("../src/lib/electric-range.ts");
const { specPower, powerRows } = load("../src/lib/power.ts");
const powerFixtures = JSON.parse(
  fs.readFileSync(new URL("./fixtures/electrified-power.json", import.meta.url), "utf8"),
);

test("power rows use explicit Che168 motor, engine and system fields", () => {
  for (const entry of powerFixtures) {
    assert.deepEqual({ ...specPower(JSON.stringify(entry.params_json)) }, {
      engineHp: entry.engine_hp,
      motorHp: entry.motor_hp,
      totalHp: entry.total_hp,
    }, entry.spec_id);
  }

  const displayed = (entry) => Object.fromEntries(
    powerRows(entry.params_json, entry.fuel, entry.engine_hp)
      .filter(({ value }) => value)
      .map(({ label, value }) => [label, value]),
  );
  const [erev, phev, hev, ev, missingTotal] = powerFixtures;
  assert.deepEqual(displayed(erev), { "Мощность электромоторов": "326 л.с." });
  assert.deepEqual(displayed(phev), { "Суммарная мощность": "408 л.с.", ДВС: "252 л.с.", Электромотор: "163 л.с." });
  assert.deepEqual(displayed(hev), { "Суммарная мощность": "218 л.с.", ДВС: "178 л.с.", Электромотор: "120 л.с." });
  assert.deepEqual(displayed(ev), { "Мощность электромоторов": "218 л.с." });
  assert.deepEqual(displayed(missingTotal), { ДВС: "139 л.с.", Электромотор: "218 л.с." });
  assert.equal(specPower(ev.params_json.slice(1)).motorHp, 218);
  assert.equal(powerRows("bad json", "гибрид EREV", 131)[0].value, null);
  assert.deepEqual({ ...powerRows(null, "Бензин", 150)[0] }, { label: "Мощность", value: "150 л.с." });
});

const params = (...entries) => [["基本参数", entries]];
const dolphin = {
  listing_id: "60613575",
  brand_ru: "BYD",
  model: "海豚 2021款 405km 时尚版",
  year: 2022,
  brand_id: 3,
  brand_name: "BYD",
  brand_slug: "byd",
  logo_path: "/brands/byd.svg",
  model_name: "Dolphin",
  model_slug: "dolphin",
  trim: null,
  mileage_km: 66000,
  price_cny: 55800,
  city_display: "Чанша",
  photos: null,
  images: null,
  local_photo: null,
};
test("catalog card uses mapped model and registration year, including photo alt", () => {
  const Card = load("../src/app/catalog/used/CatalogCard.tsx", {
    "react/jsx-runtime": jsx,
    "next/link": { default: (props) => React.createElement("a", props) },
    "@/lib/car-title": titles,
    "@/lib/format": format,
  }).default;
  const markup = renderToStaticMarkup(
    React.createElement(Card, { car: { ...dolphin, local_photo: "/photos/test.jpg" }, eager: true }),
  );
  assert.match(markup, /BYD Dolphin 2022/);
  assert.match(markup, /alt="BYD Dolphin 2022"/);
  assert.doesNotMatch(markup, /2021|405km|海豚/);
  assert.match(markup, /¥\s55\s800/);
  assert.match(markup, /loading="eager" decoding="async"/);
  const lazy = renderToStaticMarkup(
    React.createElement(Card, { car: { ...dolphin, local_photo: "/photos/test.jpg" }, eager: false }),
  );
  assert.match(lazy, /loading="lazy" decoding="async"/);
});
test("home search shares body codes and turns on all ruble controls together", () => {
  const filters = load("../src/lib/catalog-filters.ts");
  const Search = load("../src/components/home/HeroSearch.tsx", {
    "react/jsx-runtime": jsx,
    "next/navigation": { useRouter: () => ({}) },
    "next/link": {
      default: ({ href, className, children }) => React.createElement("a", { href, className }, children),
    },
    "@/lib/catalog-filters": filters,
    "@/lib/format": format,
  }).default;
  const render = (priceAvailable) =>
    renderToStaticMarkup(React.createElement(Search, { total: 10, priceAvailable }));
  const hidden = render(false);
  assert.match(hidden, /<form[^>]* action="\/catalog\/used"/);
  for (const [code, label] of Object.entries(filters.BODY_NAMES)) {
    assert.ok(hidden.includes(`<option value="${code}">${label}</option>`));
  }
  assert.match(hidden, /href="\/catalog\/used\?body=suv"/);
  assert.doesNotMatch(hidden, /name="priceTo"|До [23] млн|\/catalog\/new/);
  const shown = render(true);
  assert.match(shown, /name="priceTo"/);
  for (const millions of [2, 3])
    assert.ok(shown.includes(`href="/catalog/used?priceTo=${millions * 1_000_000}"`));
});
test("range is read from model specs, with duplicate sections deduplicated", () => {
  const spec = params(["NEDC纯电续航里程(km)", "405"], ["NEDC纯电续航里程(km)", "405"]);
  assert.equal(electricRange(JSON.stringify(spec), "Электро"), "405 км (NEDC)");
});
test("different measurement cycles stay separate and normalized units are accepted", () => {
  assert.equal(
    electricRange(
      params(["CLTC纯电续航里程（km）", "420"], ["WLTC纯电续航里程(km)", "350"]),
      "Электро",
    ),
    "420 км (CLTC); 350 км (WLTC)",
  );
});
test("hybrid totals and real-world tests never become EV rated range", () => {
  assert.equal(
    electricRange(params(["NEDC综合续航(km)", "1200"], ["实测续航里程(km)", "300"]), "Электро"),
    null,
  );
  assert.equal(electricRange(params(["CLTC纯电续航里程(km)", "100"]), "Гибрид"), null);
  assert.equal(electricRange(params(["CLTC纯电续航里程(km)", "100"]), "Бензин"), null);
});
test("missing, malformed, conflicting and nonnumeric data does not invent range", () => {
  for (const raw of [
    null,
    "{",
    {},
    params(["NEDC纯电续航里程(km)", "-"], ["CLTC纯电续航里程(km)", "0"]),
    params(["NEDC纯电续航里程(km)", "405"], ["NEDC纯电续航里程(km)", "500"]),
  ]) {
    assert.equal(electricRange(raw, "Электро"), null);
  }
  assert.equal(
    electricRange(params(["纯电续航里程(km)", 405]), "Электро"),
    "405 км (цикл не указан)",
  );
});
