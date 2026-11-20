import Link from "next/link";
import pool from "@/lib/db";
import { firstDisplayValue } from "@/lib/format";
import ArrivalPhoto from "./ArrivalPhoto";

interface Car {
  listing_id: string;
  brand_ru: string;
  model: string;
  year: number | null;
  mileage_km: number | null;
  price_cny: number;
  fuel: string | null;
  spec_fuel: string | null;
  city_display: string | null;
  photos: string | null;
  images: string | null;
  local_photo: string | null;
}

function firstPhoto(car: Car): string | null {
  if (car.local_photo) return car.local_photo;
  for (const value of [car.photos, car.images]) {
    if (!value) continue;
    try {
      const photos = JSON.parse(value);
      if (Array.isArray(photos) && typeof photos[0] === "string" && photos[0]) {
        return `/api/img?url=${encodeURIComponent(photos[0])}`;
      }
    } catch {
      continue;
    }
  }
  return null;
}

export default async function LatestArrivals() {
  let cars: Car[] = [];
  let total: number | null = null;
  try {
    const [carsResult, countResult] = await Promise.all([
      pool.query<Car>(
        `SELECT c.listing_id, c.brand_ru, c.model, c.year, c.mileage_km, c.price_cny,
                c.fuel, s.fuel AS spec_fuel, COALESCE(ct.city_ru, c.city) AS city_display,
                c.photos, c.images, c.local_photo
         FROM cars c
         LEFT JOIN specs s ON s.spec_id = c.spec_id
         LEFT JOIN city_translations ct ON ct.city_cn = c.city
         WHERE c.is_active = 1 AND c.price_cny > 0
         ORDER BY c.scraped_at DESC NULLS LAST, c.listing_id DESC
         LIMIT 4`,
      ),
      pool.query<{ count: string }>(
        "SELECT COUNT(*) FROM cars WHERE is_active = 1 AND price_cny > 0",
      ),
    ]);
    cars = carsResult.rows;
    total = Number(countResult.rows[0].count);
  } catch (error) {
    console.error("Не удалось загрузить свежие объявления", error);
  }

  const catalogLabel =
    total === null ? "Все автомобили" : `Все ${total.toLocaleString("ru-RU")} авто`;

  return (
    <section className="bg-graphite-900 py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-end justify-between mb-8">
          <div>
            <p className="text-orange-500 font-heading text-xs uppercase tracking-widest mb-2">
              Свежие поступления
            </p>
            <h2 className="font-heading font-bold text-2xl sm:text-3xl text-white">
              Только добавленные
            </h2>
          </div>
          <Link
            href="/catalog/used"
            className="hidden sm:flex items-center gap-2 text-gray-400 hover:text-orange-500 font-body text-sm transition-colors"
          >
            {catalogLabel} <span aria-hidden="true">→</span>
          </Link>
        </div>

        {cars.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {cars.map((car) => {
              const photo = firstPhoto(car);
              const fuel = firstDisplayValue(car.fuel, car.spec_fuel);
              const model = car.model
                ?.replace(/[一-鿿㐀-䶿]+/g, " ")
                .replace(/\s+/g, " ")
                .trim();
              const details = [
                car.year,
                car.mileage_km != null
                  ? `${new Intl.NumberFormat("ru-RU").format(car.mileage_km)} км`
                  : null,
                car.city_display,
              ].filter((value) => value != null && value !== "");
              return (
                <Link
                  key={car.listing_id}
                  href={`/car/${encodeURIComponent(car.listing_id)}`}
                  className="group min-w-0 bg-graphite-800 rounded-xl overflow-hidden border border-white/5 hover:border-orange-500/20 transition-all duration-200"
                >
                  <div className="aspect-[4/3] bg-graphite-700 relative overflow-hidden">
                    <ArrivalPhoto src={photo} alt={`${car.brand_ru} ${model || ""}`} />
                    {fuel && (
                      <div className="absolute top-2 left-2">
                        <span className="bg-graphite-900/80 text-gray-300 font-body text-xs px-2 py-1 rounded-full backdrop-blur">
                          {fuel}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="p-4">
                    <div className="font-heading font-bold text-sm text-white mb-1 [overflow-wrap:anywhere]">
                      {car.brand_ru} {model}
                    </div>
                    <div className="text-gray-400 font-body text-xs mb-3 [overflow-wrap:anywhere]">
                      {details.join(" · ")}
                    </div>
                    <div className="border-t border-white/5 pt-3">
                      <div className="text-gray-500 font-body text-xs mb-0.5">Цена в Китае</div>
                      <div className="font-heading font-bold text-orange-500 text-base">
                        ¥{new Intl.NumberFormat("ru-RU").format(car.price_cny)}
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <p className="text-gray-400 font-body text-sm">
            {total === null
              ? "Не удалось загрузить объявления. Попробуйте позже."
              : "Пока нет объявлений."}
          </p>
        )}
        <div className="text-center mt-8 sm:hidden">
          <Link
            href="/catalog/used"
            className="inline-flex items-center gap-2 bg-graphite-800 text-white font-body font-semibold text-sm px-6 py-3 rounded-xl border border-white/5 hover:border-orange-500/30 transition-all"
          >
            {catalogLabel}
          </Link>
        </div>
      </div>
    </section>
  );
}
