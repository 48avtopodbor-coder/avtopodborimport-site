export const BODY_NAMES: Record<string, string> = {
  suv: "Кроссовер / внедорожник",
  sedan: "Седан",
  hatchback: "Хэтчбек",
  wagon: "Универсал",
  mpv: "Минивэн",
  coupe: "Купе",
  convertible: "Кабриолет",
  pickup: "Пикап",
  van: "Фургон / микроавтобус",
};
export const MAX_PRICE_RUB = 10_000_000_000;

export const SORT_NAMES = {
  diverse: "Разные марки и модели",
  newest: "Сначала новые",
  price_asc: "Сначала дешевле",
  price_desc: "Сначала дороже",
  mileage_asc: "Меньше пробег",
  year_desc: "Новее год",
} as const;
export type Sort = keyof typeof SORT_NAMES;
export interface CatalogFilters {
  brand: string;
  models: string[];
  bodies: string[];
  yearFrom?: number;
  yearTo?: number;
  priceFrom?: number;
  priceTo?: number;
  mileageFrom?: number;
  mileageTo?: number;
  sort: Sort;
  page: number;
  fuel?: string;
}
export type QueryInput = Record<string, string | string[] | undefined>;
export function parseFilters(input: QueryInput): CatalogFilters {
  const value = (key: string) => {
    const v = input[key];
    return Array.isArray(v) ? v[0] || "" : v || "";
  };
  const slug = (v: string) => /^[a-z0-9][a-z0-9-]{0,79}$/.test(v);
  const list = (key: string) =>
    [
      ...new Set(
        (Array.isArray(input[key]) ? input[key].join(",") : value(key)).split(",").filter(slug),
      ),
    ].slice(0, 20);
  const number = (key: string, min: number, max: number) => {
    const v = value(key);
    if (!/^\d{1,11}$/.test(v)) return undefined;
    const n = Number(v);
    return Number.isSafeInteger(n) && n >= min && n <= max ? n : undefined;
  };
  const brandValue = value("brand").trim().toLowerCase().replace(/\s+/g, "-");
  const brand = slug(brandValue) ? brandValue : "";
  const sort = Object.hasOwn(SORT_NAMES, value("sort")) ? (value("sort") as Sort) : "diverse";
  const requestedPage = value("page");
  const result: CatalogFilters = {
    brand,
    models: brand ? list("model") : [],
    bodies: list("body").filter((v) => Object.hasOwn(BODY_NAMES, v)),
    yearFrom: number("yearFrom", 1900, new Date().getFullYear() + 1),
    yearTo: number("yearTo", 1900, new Date().getFullYear() + 1),
    priceFrom: number("priceFrom", 0, MAX_PRICE_RUB),
    priceTo: number("priceTo", 0, MAX_PRICE_RUB),
    mileageFrom: number("mileageFrom", 0, 3000000),
    mileageTo: number("mileageTo", 0, 3000000),
    sort,
    page: /^\d+$/.test(requestedPage)
      ? Math.max(1, Math.min(Number(requestedPage), Number.MAX_SAFE_INTEGER))
      : 1,
    fuel: value("fuel").length <= 40 ? value("fuel") || undefined : undefined,
  };
  for (const [from, to] of [
    ["yearFrom", "yearTo"],
    ["priceFrom", "priceTo"],
    ["mileageFrom", "mileageTo"],
  ] as const) {
    if (result[from] !== undefined && result[to] !== undefined && result[from]! > result[to]!) {
      result[from] = undefined;
      result[to] = undefined;
    }
  }
  return result;
}
export function filterParams(f: CatalogFilters, includePage = true) {
  const p = new URLSearchParams();
  if (f.brand) p.set("brand", f.brand);
  if (f.models.length) p.set("model", f.models.join(","));
  if (f.bodies.length) p.set("body", f.bodies.join(","));
  for (const key of [
    "yearFrom",
    "yearTo",
    "priceFrom",
    "priceTo",
    "mileageFrom",
    "mileageTo",
  ] as const)
    if (f[key] !== undefined) p.set(key, String(f[key]));
  if (f.sort !== "diverse") p.set("sort", f.sort);
  if (f.fuel) p.set("fuel", f.fuel);
  if (includePage && f.page > 1) p.set("page", String(f.page));
  return p;
}
export function catalogHref(f: CatalogFilters) {
  const q = filterParams(f).toString();
  return "/catalog/used" + (q ? "?" + q : "");
}
export function activeFilterCount(f: CatalogFilters) {
  return (
    Number(Boolean(f.brand)) +
    f.models.length +
    f.bodies.length +
    Number(f.yearFrom !== undefined || f.yearTo !== undefined) +
    Number(f.priceFrom !== undefined || f.priceTo !== undefined) +
    Number(f.mileageFrom !== undefined || f.mileageTo !== undefined) +
    Number(Boolean(f.fuel))
  );
}
export function emptyFilters(): CatalogFilters {
  return { brand: "", models: [], bodies: [], sort: "diverse", page: 1 };
}
