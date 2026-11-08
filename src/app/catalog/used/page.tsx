import pool from "@/lib/db";
import Link from "next/link";
import Image from "next/image";

interface Car {
  listing_id: string;
  brand_ru: string;
  model: string;
  year: number;
  mileage_km: number;
  price_cny: number;
  fuel: string;
  gearbox: string;
  color: string;
  city: string;
  photos: string | null;
  images: string | null;
  local_photo: string | null;
}

function cleanModel(model: string): string {
  return model
    .replace(/[一-鿿㐀-䶿]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function getFirstPhoto(car: Car): string | null {
  try {
    if (car.photos) {
      const arr = JSON.parse(car.photos);
      if (Array.isArray(arr) && arr.length > 0) return arr[0];
    }
    if (car.images) {
      const arr = JSON.parse(car.images);
      if (Array.isArray(arr) && arr.length > 0) return arr[0];
    }
  } catch {}
  return null;
}

function formatPrice(cny: number): string {
  if (!cny) return "—";
  // Примерный курс: 1 CNY ≈ 13.5 RUB, доставка ~300к, таможня ~зависит от объёма
  // Пока показываем только цену в Китае
  return `¥${(cny / 10000).toFixed(1)} вн`;
}

export default async function UsedCatalogPage({
  searchParams,
}: {
  searchParams: Promise<{ brand?: string; fuel?: string; page?: string }>;
}) {
  const sp = await searchParams;
  const page = parseInt(sp.page || "1");
  const limit = 24;
  const offset = (page - 1) * limit;

  const conditions: string[] = ["is_active = 1", "price_cny > 0"];
  const params: (string | number)[] = [];
  let idx = 1;

  if (sp.brand) {
    conditions.push(`brand_ru = $${idx++}`);
    params.push(sp.brand);
  }
  if (sp.fuel) {
    conditions.push(`fuel = $${idx++}`);
    params.push(sp.fuel);
  }

  const where = conditions.join(" AND ");

  const [carsResult, countResult, brandsResult] = await Promise.all([
    pool.query(
      `SELECT listing_id, brand_ru, model, year, mileage_km, price_cny,
              fuel, gearbox, color, city, photos, images, local_photo
       FROM cars WHERE ${where}
       ORDER BY scraped_at DESC
       LIMIT $${idx} OFFSET $${idx + 1}`,
      [...params, limit, offset]
    ),
    pool.query(`SELECT COUNT(*) FROM cars WHERE ${where}`, params),
    pool.query(
      `SELECT brand_ru, COUNT(*) as cnt FROM cars WHERE is_active=1 AND price_cny>0
       GROUP BY brand_ru ORDER BY cnt DESC LIMIT 20`
    ),
  ]);

  const cars: Car[] = carsResult.rows;
  const total = parseInt(countResult.rows[0].count);
  const totalPages = Math.ceil(total / limit);
  const brands = brandsResult.rows;

  return (
    <div className="min-h-screen bg-graphite-900">
      {/* Шапка */}
      <header className="border-b border-white/5 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-8 h-8 bg-orange-500 rounded flex items-center justify-center">
            <span className="font-heading font-bold text-white text-xs">AI</span>
          </div>
          <span className="font-heading font-bold text-white text-sm uppercase tracking-wider">
            AVTOPODBOR IMPORT
          </span>
        </Link>
        <nav className="hidden md:flex gap-6 text-sm font-body">
          <Link href="/catalog/used" className="text-white">С пробегом</Link>
          <Link href="/catalog/new" className="text-gray-400 hover:text-white transition-colors">Новые</Link>
          <Link href="/price" className="text-gray-400 hover:text-white transition-colors">Цена под ключ</Link>
        </nav>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="font-heading font-bold text-2xl text-white mb-1">
            Авто с пробегом из Китая
          </h1>
          <p className="text-gray-400 font-body text-sm">{total.toLocaleString("ru")} автомобилей</p>
        </div>

        <div className="flex gap-8">
          {/* Фильтры */}
          <aside className="hidden lg:block w-56 shrink-0">
            <div className="bg-graphite-800 rounded-xl p-4">
              <h2 className="font-heading font-bold text-white text-sm uppercase tracking-wider mb-3">Марка</h2>
              <div className="space-y-1">
                <Link
                  href="/catalog/used"
                  className={`block text-sm font-body py-1 px-2 rounded transition-colors ${
                    !sp.brand ? "text-orange-400" : "text-gray-400 hover:text-white"
                  }`}
                >
                  Все марки
                </Link>
                {brands.map((b) => (
                  <Link
                    key={b.brand_ru}
                    href={`/catalog/used?brand=${encodeURIComponent(b.brand_ru)}`}
                    className={`flex justify-between text-sm font-body py-1 px-2 rounded transition-colors ${
                      sp.brand === b.brand_ru ? "text-orange-400" : "text-gray-400 hover:text-white"
                    }`}
                  >
                    <span>{b.brand_ru}</span>
                    <span className="text-gray-600">{b.cnt}</span>
                  </Link>
                ))}
              </div>
            </div>
          </aside>

          {/* Карточки */}
          <div className="flex-1">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {cars.map((car) => {
                const remotePhoto = getFirstPhoto(car);
                const photoSrc = car.local_photo
                  ? car.local_photo
                  : remotePhoto
                  ? `/api/img?url=${encodeURIComponent(remotePhoto)}`
                  : null;
                return (
                  <Link
                    key={car.listing_id}
                    href={`/car/${car.listing_id}`}
                    className="bg-graphite-800 rounded-xl overflow-hidden hover:ring-1 hover:ring-orange-500/50 transition-all group"
                  >
                    {/* Фото */}
                    <div className="relative h-44 bg-graphite-700">
                      {photoSrc ? (
                        <img
                          src={photoSrc}
                          alt={`${car.brand_ru} ${car.model}`}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-600">
                          <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      )}
                    </div>

                    {/* Инфо */}
                    <div className="p-3">
                      <div className="font-heading font-bold text-white text-sm mb-1">
                        {car.brand_ru} {cleanModel(car.model)}
                      </div>
                      <div className="flex gap-3 text-xs text-gray-400 font-body mb-2">
                        <span>{car.year}</span>
                        <span>{car.mileage_km ? `${(car.mileage_km / 1000).toFixed(0)} тыс. км` : "—"}</span>
                        <span>{car.fuel || "—"}</span>
                      </div>
                      <div className="text-orange-400 font-heading font-bold text-sm">
                        {formatPrice(car.price_cny)}
                      </div>
                      <div className="text-xs text-gray-500 font-body">{car.city}</div>
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* Пагинация */}
            {totalPages > 1 && (
              <div className="flex gap-2 mt-8 justify-center">
                {page > 1 && (
                  <Link
                    href={`/catalog/used?${new URLSearchParams({ ...sp, page: String(page - 1) })}`}
                    className="px-4 py-2 bg-graphite-800 text-gray-400 rounded-lg font-body text-sm hover:text-white transition-colors"
                  >
                    ← Назад
                  </Link>
                )}
                <span className="px-4 py-2 text-gray-500 font-body text-sm">
                  {page} / {totalPages}
                </span>
                {page < totalPages && (
                  <Link
                    href={`/catalog/used?${new URLSearchParams({ ...sp, page: String(page + 1) })}`}
                    className="px-4 py-2 bg-graphite-800 text-gray-400 rounded-lg font-body text-sm hover:text-white transition-colors"
                  >
                    Вперёд →
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
