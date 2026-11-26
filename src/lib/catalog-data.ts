import pool from "@/lib/db";
import type { CarTitleData } from "./car-title";
import { unstable_cache } from "next/cache";
import { BODY_NAMES, type CatalogFilters } from "./catalog-filters";
import { CATALOG_VISIBLE_SQL } from "./catalog-age";

export interface Facet {
  slug: string;
  name: string;
  count: number;
  logo?: string | null;
}
export interface Facets {
  total: number;
  brands: Facet[];
  models: Facet[];
  bodies: Facet[];
  ranges: {
    year: [number | null, number | null];
    price: [number, number];
    mileage: [number, number];
  };
  priceAvailable: boolean;
}
export interface CatalogCar extends CarTitleData {
  listing_id: string;
  mileage_km: number;
  price_cny: number;
  fuel: string | null;
  spec_fuel: string | null;
  gearbox: string | null;
  color: string | null;
  city: string;
  city_display: string;
  photos: string | null;
  images: string | null;
  local_photo: string | null;
}
const FROM = `FROM cars c LEFT JOIN brands b ON b.id=c.brand_id OR (c.brand_id IS NULL AND b.name=c.brand_ru)
 LEFT JOIN catalog_spec_bodies cb ON cb.spec_id=c.spec_id LEFT JOIN specs s ON s.spec_id=c.spec_id`;
export const getCatalogSummary = unstable_cache(
  async () => {
    const { rows } = await pool.query<{ total: number; priceAvailable: boolean }>(
      `SELECT count(*)::int AS total, (count(c.price_rub) > 0) AS "priceAvailable"
       FROM cars c WHERE ${CATALOG_VISIBLE_SQL}`,
    );
    return rows[0];
  },
  ["catalog-summary-v1"],
  { revalidate: 300 },
);
export function catalogWhere(f: CatalogFilters, omit?: "brand" | "model" | "body" | "ranges") {
  const clauses = [CATALOG_VISIBLE_SQL];
  const values: (string | string[] | number)[] = [];
  const bind = (v: string | string[] | number) => {
    values.push(v);
    return `$${values.length}`;
  };
  if (f.brand && omit !== "brand") clauses.push(`b.slug=${bind(f.brand)}`);
  if (f.models.length && omit !== "brand" && omit !== "model")
    clauses.push(`c.model_slug=ANY(${bind(f.models)}::text[])`);
  if (f.bodies.length && omit !== "body")
    clauses.push(`cb.body_slug=ANY(${bind(f.bodies)}::text[])`);
  if (omit !== "ranges")
    for (const [key, column, operator] of [
      ["yearFrom", "c.year", ">="],
      ["yearTo", "c.year", "<="],
      ["priceFrom", "c.price_rub", ">="],
      ["priceTo", "c.price_rub", "<="],
      ["mileageFrom", "c.mileage_km", ">="],
      ["mileageTo", "c.mileage_km", "<="],
    ] as const)
      if (f[key] !== undefined) clauses.push(`${column}${operator}${bind(f[key]!)}`);
  if (f.fuel) clauses.push(`lower(COALESCE(c.fuel,s.fuel))=lower(${bind(f.fuel)})`);
  return { sql: clauses.join(" AND "), values };
}
export const brandRegistry = unstable_cache(
  async () =>
    (await pool.query<{ slug: string; name: string }>("SELECT slug,name FROM brands")).rows,
  ["catalog-brand-registry"],
  { revalidate: 300 },
);
export async function normalizeCatalogFilters(f: CatalogFilters) {
  const brands = await brandRegistry();
  if (f.brand && !brands.some((b) => b.slug === f.brand)) return { ...f, brand: "", models: [] };
  return f;
}
async function facetsUncached(f: CatalogFilters): Promise<Facets> {
  const all = catalogWhere(f),
    brand = catalogWhere(f, "brand"),
    model = catalogWhere(f, "model"),
    body = catalogWhere(f, "body"),
    range = catalogWhere(f, "ranges");
  const results = await Promise.all([
    pool.query(`SELECT count(*)::int AS total ${FROM} WHERE ${all.sql}`, all.values),
    pool.query(
      `SELECT b.slug,b.name,b.logo_path AS logo,count(*)::int AS count ${FROM} WHERE ${brand.sql} AND b.slug IS NOT NULL GROUP BY b.id ORDER BY count DESC,b.name`,
      brand.values,
    ),
    f.brand
      ? pool.query(
          `SELECT c.model_slug AS slug,max(c.model_name) AS name,count(*)::int AS count ${FROM} WHERE ${model.sql} AND c.model_slug IS NOT NULL GROUP BY c.model_slug ORDER BY count DESC,name`,
          model.values,
        )
      : Promise.resolve({ rows: [] }),
    pool.query(
      `SELECT cb.body_slug AS slug,count(*)::int AS count ${FROM} WHERE ${body.sql} AND cb.body_slug IS NOT NULL GROUP BY cb.body_slug ORDER BY count DESC`,
      body.values,
    ),
    pool.query(
      `SELECT min(c.year) AS y1,max(c.year) AS y2,min(c.price_rub) AS p1,max(c.price_rub) AS p2,min(c.mileage_km) AS m1,max(c.mileage_km) AS m2 ${FROM} WHERE ${range.sql}`,
      range.values,
    ),
    getCatalogSummary(),
  ]);
  const r = results[4].rows[0];
  return {
    total: results[0].rows[0].total,
    brands: results[1].rows as Facet[],
    models: results[2].rows as Facet[],
    bodies: results[3].rows.map((b) => ({ ...b, name: BODY_NAMES[b.slug] || b.slug })),
    ranges: {
      year: [r.y1 ?? null, r.y2 ?? null],
      price: [Number(r.p1 || 0), Number(r.p2 || 0)],
      mileage: [Number(r.m1 || 0), Number(r.m2 || 0)],
    },
    priceAvailable: results[5].priceAvailable,
  };
}
export const getCatalogFacets = unstable_cache(facetsUncached, ["catalog-facets-v4"], {
  revalidate: 300,
});
const ORDERS = {
  newest: "c.scraped_at DESC NULLS LAST",
  price_asc: "c.price_cny ASC",
  price_desc: "c.price_cny DESC",
  mileage_asc: "c.mileage_km ASC NULLS LAST",
  year_desc: "c.year DESC NULLS LAST",
};
// Rank models inside each brand, then interleave brands. The full matching set
// is ranked before LIMIT/OFFSET, so pagination is stable and does not repeat cars.
export function catalogListQuery(f: CatalogFilters, limit: number, offset: number) {
  const where = catalogWhere(f);
  const select = `c.listing_id,c.brand_ru,c.model,c.year,c.brand_id,c.model_name,c.model_slug,c.trim,b.name AS brand_name,b.slug AS brand_slug,b.logo_path,c.mileage_km,c.price_cny,c.fuel,s.fuel AS spec_fuel,COALESCE(c.gearbox,s.gearbox) AS gearbox,c.color,c.city,COALESCE(ct.city_ru,c.city) AS city_display,c.photos,c.images,c.local_photo`;
  const pagination = `LIMIT $${where.values.length + 1} OFFSET $${where.values.length + 2}`;
  const matched = `${select} ${FROM} LEFT JOIN city_translations ct ON ct.city_cn=c.city WHERE ${where.sql}`;
  const sql =
    f.sort === "diverse"
      ? `WITH matched AS (
        SELECT c.listing_id,c.scraped_at AS added_at,
          COALESCE(b.slug,c.brand_ru,'') AS brand_key,
          COALESCE(NULLIF(c.model_slug,''),NULLIF(c.model_name,''),c.model,'') AS model_key
        ${FROM} LEFT JOIN city_translations ct ON ct.city_cn=c.city WHERE ${where.sql}
      ), model_ranks AS (
        SELECT *,row_number() OVER (PARTITION BY brand_key,model_key ORDER BY added_at DESC NULLS LAST,listing_id DESC) AS model_position FROM matched
      ), brand_ranks AS (
        SELECT *,row_number() OVER (PARTITION BY brand_key ORDER BY model_position,added_at DESC NULLS LAST,listing_id DESC) AS brand_position FROM model_ranks
      ) , picked AS (
        SELECT listing_id,brand_position,model_position,added_at
        FROM brand_ranks ORDER BY brand_position,model_position,added_at DESC NULLS LAST,listing_id DESC ${pagination}
      ) SELECT ${select} ${FROM}
        LEFT JOIN city_translations ct ON ct.city_cn=c.city
        JOIN picked p ON p.listing_id=c.listing_id
        ORDER BY p.brand_position,p.model_position,p.added_at DESC NULLS LAST,c.listing_id DESC`
      : `SELECT ${matched} ORDER BY ${ORDERS[f.sort]},c.listing_id DESC ${pagination}`;
  return { sql, values: [...where.values, limit, offset] };
}
export async function getCatalogList(f: CatalogFilters) {
  const where = catalogWhere(f),
    pageSize = 24;
  const count = await pool.query(
    `SELECT count(*)::int AS total ${FROM} WHERE ${where.sql}`,
    where.values,
  );
  const total: number = count.rows[0].total;
  const page = Math.min(f.page, Math.max(1, Math.ceil(total / pageSize)));
  const query = catalogListQuery(f, pageSize, (page - 1) * pageSize);
  const cars = await pool.query<CatalogCar>(query.sql, query.values);
  return { items: cars.rows, total, page, pageSize };
}
