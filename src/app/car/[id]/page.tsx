import pool from "@/lib/db";
import Link from "next/link";
import { notFound } from "next/navigation";

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
  city_display: string;
  distance_km: number | null;
  photos: string | null;
  images: string | null;
  local_photo: string | null;
  scraped_at: string;
}

interface Spec {
  fuel: string | null;
  drive: string | null;
  gearbox: string | null;
  power_hp: number | null;
  engine_ml: number | null;
  params_text: string | null;
  tires: string | null;
}

// Убирает китайские иероглифы, оставляет латиницу, цифры, знаки
function cleanModel(model: string): string {
  return model
    .replace(/[一-鿿㐀-䶿]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function getPhotos(car: Car): string[] {
  const urls: string[] = [];
  try {
    if (car.photos) {
      const arr = JSON.parse(car.photos);
      if (Array.isArray(arr)) urls.push(...arr);
    }
    if (car.images && urls.length === 0) {
      const arr = JSON.parse(car.images);
      if (Array.isArray(arr)) urls.push(...arr);
    }
  } catch {}
  return urls;
}

function formatPrice(cny: number): string {
  if (!cny) return "—";
  return `¥${(cny / 10000).toFixed(1)} вн`;
}

export default async function CarPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const [carResult, specsResult] = await Promise.all([
    pool.query(
      `SELECT c.listing_id, c.brand_ru, c.model, c.year, c.mileage_km, c.price_cny,
              c.fuel, c.gearbox, c.color, c.city,
              COALESCE(ct.city_ru, c.city) as city_display,
              ct.distance_km,
              c.photos, c.images, c.local_photo, c.scraped_at
       FROM cars c
       LEFT JOIN city_translations ct ON ct.city_cn = c.city
       WHERE c.listing_id = $1`,
      [id]
    ),
    // Комплектация связана с машиной через cars.spec_id, а не через номер объявления
    pool.query(
      `SELECT s.fuel, s.drive, s.gearbox, s.power_hp, s.engine_ml, s.params_text, s.tires
       FROM cars c
       JOIN specs s ON s.spec_id = c.spec_id
       WHERE c.listing_id = $1`,
      [id]
    ),
  ]);

  if (carResult.rows.length === 0) notFound();

  const car: Car = carResult.rows[0];
  const spec: Spec | null = specsResult.rows[0] ?? null;
  const remotePhotos = getPhotos(car);

  // Список фото для показа: локальное первым, потом остальные через прокси
  const photoSrcs: string[] = [];
  if (car.local_photo) {
    photoSrcs.push(car.local_photo);
  }
  remotePhotos.forEach((url, i) => {
    // Если локальное есть — первое уже добавлено, пропускаем его дубль
    if (car.local_photo && i === 0) return;
    photoSrcs.push(`/api/img?url=${encodeURIComponent(url)}`);
  });

  const mainPhoto = photoSrcs[0] ?? null;

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
          <Link href="/catalog/used" className="text-gray-400 hover:text-white transition-colors">
            С пробегом
          </Link>
          <Link href="/catalog/new" className="text-gray-400 hover:text-white transition-colors">
            Новые
          </Link>
          <Link href="/price" className="text-gray-400 hover:text-white transition-colors">
            Цена под ключ
          </Link>
        </nav>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Хлебные крошки */}
        <div className="flex items-center gap-2 text-sm font-body text-gray-500 mb-6">
          <Link href="/catalog/used" className="hover:text-gray-300 transition-colors">
            Авто с пробегом
          </Link>
          <span>/</span>
          <span className="text-gray-300">{car.brand_ru} {cleanModel(car.model)}</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Фото */}
          <div>
            <div className="relative aspect-[4/3] bg-graphite-800 rounded-xl overflow-hidden mb-3">
              {mainPhoto ? (
                <img
                  src={mainPhoto}
                  alt={`${car.brand_ru} ${car.model}`}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-600">
                  <svg className="w-20 h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
            </div>

            {/* Миниатюры */}
            {photoSrcs.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-1">
                {photoSrcs.slice(0, 8).map((src, i) => (
                  <div
                    key={i}
                    className="shrink-0 w-20 h-16 bg-graphite-800 rounded-lg overflow-hidden"
                  >
                    <img
                      src={src}
                      alt=""
                      className="w-full h-full object-cover opacity-70 hover:opacity-100 transition-opacity"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Основная информация */}
          <div>
            <h1 className="font-heading font-bold text-2xl text-white mb-1">
              {car.brand_ru} {cleanModel(car.model)}
            </h1>
            <p className="text-gray-400 font-body text-sm mb-6">
              {car.year} · {car.city_display}
              {car.distance_km && (
                <span className="ml-2 text-gray-600">· {car.distance_km.toLocaleString("ru")} км до Хоргоса</span>
              )}
            </p>

            {/* Цена */}
            <div className="bg-graphite-800 rounded-xl p-5 mb-5">
              <div className="text-orange-400 font-heading font-bold text-3xl mb-1">
                {formatPrice(car.price_cny)}
              </div>
              <div className="text-gray-500 font-body text-xs">
                Цена в Китае. Стоимость под ключ — рассчитаем индивидуально.
              </div>
              <Link
                href="/price"
                className="mt-4 inline-block bg-orange-500 hover:bg-orange-600 text-white font-heading font-bold text-sm px-6 py-3 rounded-lg transition-colors"
              >
                Узнать цену под ключ
              </Link>
            </div>

            {/* Ключевые параметры */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Год", value: car.year },
                { label: "Пробег", value: car.mileage_km ? `${(car.mileage_km / 1000).toFixed(0)} тыс. км` : null },
                // Своих данных у машины нет, пока не собрана карточка; тогда берём из комплектации
                { label: "Топливо", value: car.fuel || spec?.fuel },
                { label: "КПП", value: car.gearbox || spec?.gearbox },
                { label: "Цвет", value: car.color },
                { label: "Город", value: car.city_display },
              ]
                .filter(({ value }) => value)
                .map(({ label, value }) => (
                <div key={label} className="bg-graphite-800 rounded-lg p-3">
                  <div className="text-gray-500 font-body text-xs mb-0.5">{label}</div>
                  <div className="text-white font-body text-sm">{value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Технические характеристики */}
        {spec && (
          <div className="mt-10">
            <h2 className="font-heading font-bold text-lg text-white mb-4">
              Технические характеристики
            </h2>
            <div className="bg-graphite-800 rounded-xl overflow-hidden">
              <table className="w-full">
                <tbody>
                  {[
                    { label: "Топливо", value: spec.fuel },
                    { label: "Привод", value: spec.drive },
                    { label: "КПП", value: spec.gearbox },
                    { label: "Мощность", value: spec.power_hp ? `${spec.power_hp} л.с.` : null },
                    { label: "Объём двигателя", value: spec.engine_ml ? `${spec.engine_ml} мл` : null },
                    { label: "Шины", value: spec.tires },
                    { label: "Параметры", value: spec.params_text },
                  ]
                    .filter(({ value }) => value)
                    .map(({ label, value }, i) => (
                      <tr key={label} className={i % 2 === 0 ? "bg-white/0" : "bg-white/[0.02]"}>
                        <td className="px-5 py-3 text-gray-400 font-body text-sm w-1/2 border-b border-white/5">
                          {label}
                        </td>
                        <td className="px-5 py-3 text-white font-body text-sm border-b border-white/5">
                          {value}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Назад */}
        <div className="mt-8">
          <Link
            href="/catalog/used"
            className="text-gray-400 hover:text-white font-body text-sm transition-colors"
          >
            ← Вернуться в каталог
          </Link>
        </div>
      </div>
    </div>
  );
}
