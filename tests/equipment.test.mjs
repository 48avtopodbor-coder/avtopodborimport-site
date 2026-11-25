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
    require: (key) => imports[key],
  });
  return loadedModule.exports;
}
const translations = load("../src/lib/equipment-translations.ts");
const equipment = load("../src/lib/equipment.ts", { "./equipment-translations": translations });
const { modelEquipment } = equipment;
const CarEquipment = load("../src/components/car/CarEquipment.tsx", {
  "react/jsx-runtime": jsx,
  "@/lib/equipment": equipment,
}).default;
const fixture = JSON.parse(
  fs.readFileSync(new URL("./fixtures/equipment-mazda.json", import.meta.url), "utf8"),
);

test("all Mazda equipment fields survive with Russian labels and detailed values", () => {
  const groups = modelEquipment(fixture);
  const items = groups.flatMap((g) => g.items);
  assert.equal(
    items.length,
    fixture.reduce((n, [, rows]) => n + rows.length, 0),
  );
  assert.ok(items.every((item) => !item.translationPending));
  assert.ok(
    items.some(
      (item) =>
        item.label === "Контроль давления в шинах" &&
        item.values[0].text === "предупреждение о снижении давления",
    ),
  );
  assert.ok(items.some((item) => item.label === "Активные жалюзи решётки радиатора"));
  const markup = renderToStaticMarkup(React.createElement(CarEquipment, { groups }));
  assert.match(markup, /8.8″/);
  assert.match(markup, /поддержка CarPlay/);
  assert.match(markup, /Показать оригинальные данные комплектации/);
});

test("front and rear presence remain independent, including absent and optional items", () => {
  const [group] = modelEquipment([
    [
      "被动安全",
      [
        ["前/后排侧气囊", "前● / 后○"],
        ["前/后驻车雷达", "前- / 后●"],
      ],
    ],
  ]);
  assert.equal(
    JSON.stringify(group.items[0].values.map((v) => [v.text, v.status])),
    JSON.stringify([
      ["Спереди", "standard"],
      ["Сзади", "optional"],
    ]),
  );
  assert.equal(
    JSON.stringify(group.items[1].values.map((v) => [v.text, v.status])),
    JSON.stringify([
      ["Спереди", "absent"],
      ["Сзади", "standard"],
    ]),
  );
});

test("mixed standard and optional variants never become one blanket installed claim", () => {
  const [group] = modelEquipment([["主动安全", [["胎压监测功能", "●胎压报警\n○胎压显示"]]]]);
  assert.equal(group.items[0].values[0].status, "standard");
  assert.equal(group.items[0].values[1].status, "optional");
  assert.equal(group.items[0].values[1].text, "отображение давления");
});

test("unknown equipment and values remain visible, numeric values do not imply installation", () => {
  const [group] = modelEquipment([
    [
      "新配置",
      [
        ["新增装备", "●未知功能"],
        ["摄像头数量", 5],
      ],
    ],
  ]);
  assert.equal(group.sourceTitle, "新配置");
  assert.equal(group.items[0].translationPending, true);
  assert.equal(group.items[0].sourceValue, "●未知功能");
  assert.equal(group.items[1].values[0].status, "unspecified");
  const markup = renderToStaticMarkup(React.createElement(CarEquipment, { groups: [group] }));
  assert.match(markup, /新增装备/);
  assert.match(markup, /Перевод значения уточняется/);
});

test("shared model registration dates never replace listing data; identical duplicates are removed", () => {
  const groups = modelEquipment([
    ["牌照信息", [["首次上牌时间", "2021-07-17"]]],
    ["发动机", [["排量(mL)", "1998"]]],
    ["被动安全", [["ABS防抱死", "●"]]],
    [
      "主动安全",
      [
        ["ABS防抱死", "●"],
        ["胎压监测功能", "●胎压报警"],
      ],
    ],
  ]);
  assert.equal(groups.length, 2);
  assert.equal(groups.flatMap((g) => g.items).length, 2);
  assert.ok(!JSON.stringify(groups).includes("2021-07-17"));
});

test("malformed input is ignored safely without discarding valid neighbours", () => {
  for (const raw of [null, undefined, {}, "{", 123]) assert.equal(modelEquipment(raw).length, 0);
  const result = modelEquipment(
    JSON.stringify([null, ["主动安全", [null, ["ABS防抱死", "●"], ["invalid", {}]]]]),
  );
  assert.equal(result[0].items.length, 1);
});
