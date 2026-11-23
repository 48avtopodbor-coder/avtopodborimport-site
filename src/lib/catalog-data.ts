import pool from "@/lib/db";
import { unstable_cache } from "next/cache";
import { BODY_NAMES, type CatalogFilters } from "./catalog-filters";

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
  ranges: { year: [number, number]; price: [number, number]; mileage: [number, number] };
  priceAvailable: boolean;
}
export interface CatalogCar {
  listing_id: string;
  brand_ru: string;
  model: string;
  year: number;
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
export function catalogWhere(f: CatalogFilters, omit?: "brand" | "model" | "body" | "ranges") {
  const clauses = ["c.is_active=1", "c.price_cny>0"];
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
    pool.query(
      "SELECT EXISTS(SELECT 1 FROM cars WHERE is_active=1 AND price_cny>0 AND price_rub IS NOT NULL) AS available",
    ),
  ]);
  const r = results[4].rows[0];
  return {
    total: results[0].rows[0].total,
    brands: results[1].rows as Facet[],
    models: results[2].rows as Facet[],
    bodies: results[3].rows.map((b) => ({ ...b, name: BODY_NAMES[b.slug] || b.slug })),
    ranges: {
      year: [Number(r.y1 || 2021), Number(r.y2 || 2023)],
      price: [Number(r.p1 || 0), Number(r.p2 || 0)],
      mileage: [Number(r.m1 || 0), Number(r.m2 || 0)],
    },
    priceAvailable: results[5].rows[0].available,
  };
}
export const getCatalogFacets = unstable_cache(facetsUncached, ["catalog-facets-v1"], {
  revalidate: 300,
});
const ORDERS = {
  newest: "c.scraped_at DESC NULLS LAST",
  price_asc: "c.price_cny ASC",
  price_desc: "c.price_cny DESC",
  mileage_asc: "c.mileage_km ASC NULLS LAST",
  year_desc: "c.year DESC NULLS LAST",
};
export async function getCatalogList(f: CatalogFilters) {
  const where = catalogWhere(f),
    pageSize = 24;
  const count = await pool.query(
    `SELECT count(*)::int AS total ${FROM} WHERE ${where.sql}`,
    where.values,
  );
  const total: number = count.rows[0].total;
  const page = Math.min(f.page, Math.max(1, Math.ceil(total / pageSize)));
  const cars = await pool.query<CatalogCar>(
    `SELECT c.listing_id,c.brand_ru,c.model,c.year,c.mileage_km,c.price_cny,c.fuel,s.fuel AS spec_fuel,COALESCE(c.gearbox,s.gearbox) AS gearbox,c.color,c.city,COALESCE(ct.city_ru,c.city) AS city_display,c.photos,c.images,c.local_photo ${FROM} LEFT JOIN city_translations ct ON ct.city_cn=c.city WHERE ${where.sql} ORDER BY ${ORDERS[f.sort]},c.listing_id DESC LIMIT $${where.values.length + 1} OFFSET $${where.values.length + 2}`,
    [...where.values, pageSize, (page - 1) * pageSize],
  );
  return { items: cars.rows, total, page, pageSize };
}
