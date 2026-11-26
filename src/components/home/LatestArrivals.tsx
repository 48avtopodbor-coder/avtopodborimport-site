import Link from "next/link";
import { formatCarFullName, type CarTitleData } from "@/lib/car-title";
import pool from "@/lib/db";
import { CATALOG_VISIBLE_SQL } from "@/lib/catalog-age";
import { firstDisplayValue, formatCarCount } from "@/lib/format";
import ArrivalPhoto from "./ArrivalPhoto";

interface Car extends CarTitleData {
  listing_id: string;
  mileage_km: number | null;
  price_cny: number;
  fuel: string | null;
  spec_fuel: string | null;
  city_display: string | null;
  local_photo: string;
}

export default async function LatestArrivals({ total }: { total: number | null }) {
  let cars: Car[] | null = null;
  try {
    const carsResult = await pool.query<Car>(
      `WITH latest_by_brand AS (
           SELECT DISTINCT ON (lower(trim(brand_ru))) *
           FROM cars c
           WHERE ${CATALOG_VISIBLE_SQL}
             AND NULLIF(trim(brand_ru), '') IS NOT NULL
             AND NULLIF(trim(local_photo), '') IS NOT NULL
           ORDER BY lower(trim(brand_ru)), scraped_at DESC NULLS LAST, listing_id DESC
         )
         SELECT c.listing_id, c.brand_ru, c.model, c.year, c.brand_id, c.model_name, c.model_slug, c.trim,
                b.name AS brand_name, b.slug AS brand_slug, b.logo_path, c.mileage_km, c.price_cny,
                c.fuel, s.fuel AS spec_fuel, COALESCE(ct.city_ru, c.city) AS city_display,
                c.local_photo
         FROM latest_by_brand c
         LEFT JOIN brands b ON b.id = c.brand_id
         LEFT JOIN specs s ON s.spec_id = c.spec_id
         LEFT JOIN city_translations ct ON ct.city_cn = c.city
         ORDER BY c.scraped_at DESC NULLS LAST, c.listing_id DESC
         LIMIT 4`,
    );
    cars = carsResult.rows;
  } catch (error) {
    console.error("Не удалось загрузить свежие объявления", error);
  }

  const catalogLabel =
    total === null
      ? "Все автомобили"
      : `${total > 1 ? "Все" : "Смотреть"} ${formatCarCount(total)}`;

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

        {cars && cars.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 empty:before:col-span-full empty:before:font-body empty:before:text-sm empty:before:text-gray-400 empty:before:content-['Пока_нет_объявлений_с_доступными_фото.']">
            {cars.map((car) => {
              const fuel = firstDisplayValue(car.fuel, car.spec_fuel);
              const name = formatCarFullName(car);
              const details = [
                car.year,
                car.mileage_km != null
                  ? `${new Intl.NumberFormat("ru-RU").format(car.mileage_km)} км`
                  : null,
                car.city_display,
              ].filter((value) => value != null && value !== "");
              return (
                <ArrivalPhoto
                  key={car.listing_id}
                  href={`/car/${encodeURIComponent(car.listing_id)}`}
                  src={car.local_photo}
                  alt={name}
                  fuel={fuel}
                >
                  <div className="p-4">
                    <div className="font-heading font-bold text-sm text-white mb-1 [overflow-wrap:anywhere]">
                      {name}
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
                </ArrivalPhoto>
              );
            })}
          </div>
        ) : (
          <p className="text-gray-400 font-body text-sm">
            {cars === null
              ? "Не удалось загрузить объявления. Попробуйте позже."
              : "Пока нет подходящих объявлений с фото."}
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
