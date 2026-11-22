export interface CarTitleData {
  brand_ru: string;
  model: string;
  year: number;
  brand_id: number | null;
  brand_name: string | null;
  brand_slug: string | null;
  logo_path: string | null;
  model_name: string | null;
  model_slug: string | null;
  trim: string | null;
}

export function legacyCarName(car: Pick<CarTitleData, "brand_ru" | "model">): string {
  const readable = car.model
    .replace(/[一-鿿㐀-䶿]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return `${car.brand_ru} ${readable}`.trim();
}

export function formatCarFullName(car: CarTitleData): string {
  if (!car.brand_id || !car.brand_name || !car.model_name) return legacyCarName(car);
  return [car.brand_name, car.model_name, String(car.year), car.trim].filter(Boolean).join(" ");
}

export function getBrandHref(brandSlug: string): string {
  return `/catalog/used?${new URLSearchParams({ brand: brandSlug })}`;
}

export function getModelHref(brandSlug: string, modelSlug: string): string {
  return `/catalog/used?${new URLSearchParams({ brand: brandSlug, model: modelSlug })}`;
}
