import fs from "node:fs";
import path from "node:path";
import { Pool } from "pg";

type BrandRow = { slug: string; logo_path: string | null };
const root = path.resolve(import.meta.dirname, "..");

async function brands(): Promise<BrandRow[]> {
  if (process.env.DATABASE_URL) {
    const pool = new Pool({ connectionString: process.env.DATABASE_URL });
    try {
      const result = await pool.query<BrandRow>("SELECT slug, logo_path FROM brands ORDER BY slug");
      return result.rows;
    } finally {
      await pool.end();
    }
  }
  const sql = fs.readFileSync(
    path.join(root, "scripts/migrations/20261122_car_titles.sql"),
    "utf8",
  );
  return [...sql.matchAll(/^\s*\('([^']+)', '[^']+', (?:NULL|'[^']+'), (NULL|'[^']+')\),?$/gm)].map(
    ([, slug, logo]) => ({ slug, logo_path: logo === "NULL" ? null : logo.slice(1, -1) }),
  );
}

let errors = 0;
const catalog = await brands();
for (const brand of catalog) {
  if (!brand.logo_path) {
    console.log(`${brand.slug}: logo_path отсутствует`);
    errors++;
    continue;
  }
  const asset = path.resolve(root, "public", brand.logo_path.replace(/^\//, ""));
  if (!asset.startsWith(path.join(root, "public", "brands") + path.sep)) {
    console.log(`${brand.slug}: небезопасный путь ${brand.logo_path}`);
    errors++;
    continue;
  }
  if (!fs.existsSync(asset)) {
    console.log(`${brand.slug}: файл не найден ${brand.logo_path}`);
    errors++;
    continue;
  }
  if (asset.endsWith(".svg")) {
    const svg = fs.readFileSync(asset, "utf8");
    if (
      !svg.includes("viewBox=") ||
      /<script\b|<foreignObject\b|(?:xlink:)?href\s*=\s*["']https?:/i.test(svg) ||
      Buffer.byteLength(svg) > 50_000
    ) {
      console.log(`${brand.slug}: SVG не проходит проверку безопасности или размера`);
      errors++;
    }
  }
}
console.log(`Проверено логотипов: ${catalog.length}, ошибок: ${errors}`);
process.exitCode = errors ? 1 : 0;
