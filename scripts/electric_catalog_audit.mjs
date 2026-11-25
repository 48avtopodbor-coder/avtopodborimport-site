#!/usr/bin/env node
// Read-only catalog audit. Runtime uses the exact title/range helpers used by Next.js.
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

const cjk = /[\u3400-\u9fff\uf900-\ufaff]/u;
const normalizeTitle = (text) =>
  String(text ?? "")
    .normalize("NFKC")
    .replace(/[\s()]+/gu, "");
function specEntries(raw) {
  try {
    const data = typeof raw === "string" ? JSON.parse(raw) : raw;
    if (!Array.isArray(data)) return [];
    return data.flatMap((section) =>
      Array.isArray(section) && Array.isArray(section[1])
        ? section[1].filter((entry) => Array.isArray(entry) && typeof entry[0] === "string")
        : [],
    );
  } catch {
    return [];
  }
}
export function auditElectricRows(rows, helpers) {
  const issues = [];
  const groups = new Map();
  const cycles = {};
  let named = 0,
    withRange = 0;
  for (const car of rows) {
    const issue = (code, detail, severity = "error") =>
      issues.push({ listing_id: car.listing_id, code, severity, detail });
    const fuel = helpers.firstDisplayValue(car.car_fuel, car.spec_fuel);
    const name = helpers.formatCarFullName(car);
    if (!car.brand_id || !car.brand_name || !car.model_name || !car.model_slug || cjk.test(name))
      issue("missing_mapped_name", name);
    else named++;
    if (/\d\s*km\b/iu.test(car.model_name ?? "")) issue("range_in_model_name", car.model_name);
    if (
      car.car_fuel &&
      car.spec_fuel &&
      car.car_fuel.trim().toLowerCase() !== car.spec_fuel.trim().toLowerCase()
    )
      issue("fuel_mismatch", `${car.car_fuel} / ${car.spec_fuel}`);
    const range = helpers.electricRange(car.params_json, fuel);
    if (!range) issue("missing_range", "Нет однозначного запаса хода, который можно показать");
    else withRange++;
    const entries = specEntries(car.params_json);
    const sourceNames = [
      ...new Set(entries.filter(([key]) => key === "车型名称").map(([, value]) => String(value))),
    ];
    if (sourceNames.some((source) => normalizeTitle(source) !== normalizeTitle(car.model)))
      issue("spec_title_mismatch", { listing: car.model, specs: sourceNames }, "warning");
    const values = new Map();
    for (const [key, raw] of entries) {
      const match = /^(NEDC|CLTC|WLTC|WLTP)?纯电续航里程\(km\)$/iu.exec(
        key.normalize("NFKC").replace(/\s+/gu, ""),
      );
      if (!match) continue;
      const cycle = match[1]?.toUpperCase() ?? "unspecified";
      const value = String(raw ?? "")
        .normalize("NFKC")
        .trim();
      if (
        !/^\d+(?:\.\d+)?$/u.test(value) ||
        Number(value) <= 0 ||
        !Number.isFinite(Number(value))
      ) {
        issue("invalid_range_value", { cycle, value });
        continue;
      }
      const set = values.get(cycle) ?? new Set();
      set.add(Number(value));
      values.set(cycle, set);
      if (Number(value) > 2000) issue("range_outlier", { cycle, value }, "warning");
    }
    for (const [cycle, set] of values) {
      cycles[cycle] = (cycles[cycle] ?? 0) + 1;
      if (set.size > 1) issue("conflicting_cycle_values", { cycle, values: [...set] });
      if (cycle === "unspecified")
        issue("unspecified_cycle", "В источнике не указан цикл измерения", "warning");
    }
    const titleKm = [
      ...String(car.model ?? "").matchAll(/(?<![\d.])(\d+(?:\.\d+)?)\s*km\b/giu),
    ].map((m) => Number(m[1]));
    if (titleKm.length && !titleKm.some((km) => [...values.values()].some((set) => set.has(km))))
      issue("title_range_mismatch", { titleKm, displayed: range }, "warning");
    const key = `${car.brand_name}\0${car.model_slug}`;
    const group = groups.get(key) ?? { brand: car.brand_name, model: car.model_name, cars: 0 };
    group.cars++;
    groups.set(key, group);
  }
  return {
    checked_at: new Date().toISOString(),
    cars: rows.length,
    models: groups.size,
    named,
    with_range: withRange,
    cycles,
    errors: issues.filter((i) => i.severity === "error").length,
    warnings: issues.filter((i) => i.severity === "warning").length,
    groups: [...groups.values()],
    issues,
  };
}
async function main() {
  const [titles, ranges, format] = await Promise.all([
    import(new URL("../src/lib/car-title.ts", import.meta.url)),
    import(new URL("../src/lib/electric-range.ts", import.meta.url)),
    import(new URL("../src/lib/format.ts", import.meta.url)),
  ]);
  const input = process.argv.indexOf("--input");
  let rows;
  if (input >= 0) rows = JSON.parse(await fs.readFile(process.argv[input + 1], "utf8"));
  else {
    const { default: pg } = await import("pg");
    const client = new pg.Client({ connectionString: process.env.DATABASE_URL });
    await client.connect();
    try {
      await client.query("BEGIN READ ONLY");
      await client.query("SET LOCAL statement_timeout = '30s'");
      rows = (
        await client.query(
          `SELECT c.listing_id,c.brand_ru,c.model,c.year,c.brand_id,c.model_name,c.model_slug,c.trim,b.name AS brand_name,b.slug AS brand_slug,b.logo_path,c.fuel AS car_fuel,s.fuel AS spec_fuel,s.params_json FROM cars c LEFT JOIN brands b ON b.id=c.brand_id LEFT JOIN specs s ON s.spec_id=c.spec_id WHERE c.is_active=1 AND c.price_cny>0 AND (c.fuel='электро' OR s.fuel='электро' OR s.params_json LIKE '%纯电动%' OR c.details_json LIKE '%纯电动%') ORDER BY c.brand_ru,c.model_name,c.listing_id`,
        )
      ).rows;
      await client.query("COMMIT");
    } finally {
      await client.end();
    }
  }
  const report = auditElectricRows(rows, { ...titles, ...ranges, ...format });
  console.log(JSON.stringify(report, null, 2));
  if (report.errors) process.exitCode = 2;
}
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) await main();
