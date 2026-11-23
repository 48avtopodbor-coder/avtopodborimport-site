import pool from "@/lib/db";
import Link from "next/link";
import HeaderPhones from "@/components/layout/HeaderPhones";
import { notFound } from "next/navigation";
import { displayValue, firstDisplayValue } from "@/lib/format";
import CarGallery from "@/components/car/CarGallery";
import { modelEquipment } from "@/lib/equipment";
import { sellerDictionaryRevision } from "@/lib/seller-description";
import CarTitle from "@/components/car/CarTitle";
import { formatCarFullName, type CarTitleData } from "@/lib/car-title";
import type { Metadata } from "next";

interface Car extends CarTitleData {
  listing_id: string;
  mileage_km: number;
  price_cny: number;
  fuel: string;
  gearbox: string;
  color: string;
  city: string;
  city_display: string;
  distance_km: number | null;
  distance_source: string | null;
  description: string | null;
  translated_description: string | null;
  engine_ml: number | null;
  tires: string | null;
  photos: string | null;
  images: string | null;
  local_photo: string | null;
  local_photo_2: string | null;
  local_photo_3: string | null;
  scraped_at: string;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const result = await pool.query<CarTitleData>(
    `SELECT c.brand_ru, c.model, c.year, c.brand_id, c.model_name, c.model_slug, c.trim,
            b.name AS brand_name, b.slug AS brand_slug, b.logo_path
     FROM cars c LEFT JOIN brands b ON b.id = c.brand_id
     WHERE c.listing_id = $1 AND c.is_active = 1`,
    [id],
  );
  if (!result.rows[0]) return {};
  const title = formatCarFullName(result.rows[0]);
  return { title, openGraph: { title } };
}

interface Spec {
  fuel: string | null;
  drive: string | null;
  gearbox: string | null;
  power_hp: number | null;
  engine_ml: number | null;
  params_text: string | null;
  params_json: unknown;
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
      if (Array.isArray(arr))
        urls.push(...arr.filter((url): url is string => typeof url === "string" && url.length > 0));
    }
    if (car.images && urls.length === 0) {
      const arr = JSON.parse(car.images);
      if (Array.isArray(arr))
        urls.push(...arr.filter((url): url is string => typeof url === "string" && url.length > 0));
    }
  } catch {}
  return urls;
}

function formatPrice(cny: number): string {
  if (!cny) return "—";
  return `¥${(cny / 10000).toFixed(1)} вн`;
}

export default async function CarPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const [carResult, specsResult] = await Promise.all([
    pool.query(
      `SELECT c.listing_id, c.brand_ru, c.model, c.year, c.mileage_km, c.price_cny,
              c.brand_id, c.model_name, c.model_slug, c.trim,
              b.name AS brand_name, b.slug AS brand_slug, b.logo_path,
              c.fuel, c.gearbox, c.color, c.city, c.engine_ml, c.tires, c.description,
              tr.translated_text AS translated_description,
              COALESCE(ct.city_ru, c.city) as city_display,
              ct.distance_km, ct.distance_source,
              c.photos, c.images, c.local_photo, c.local_photo_2, c.local_photo_3, c.scraped_at
       FROM cars c
       LEFT JOIN brands b ON b.id = c.brand_id
       LEFT JOIN city_translations ct ON ct.city_cn = c.city
       LEFT JOIN seller_description_translations tr
         ON tr.source_hash = md5(c.description) AND tr.source_text = c.description
         AND (tr.status = 'reviewed'
              OR (tr.status = 'dictionary' AND tr.dictionary_revision = $2))
       WHERE c.listing_id = $1 AND c.is_active = 1`,
      [id, sellerDictionaryRevision],
    ),
    // Комплектация связана с машиной через cars.spec_id, а не через номер объявления
    pool.query(
      `SELECT s.fuel, s.drive, s.gearbox, s.power_hp, s.engine_ml, s.params_text, s.params_json, s.tires
       FROM cars c
       JOIN specs s ON s.spec_id = c.spec_id
       WHERE c.listing_id = $1 AND c.is_active = 1`,
      [id],
    ),
  ]);

  if (carResult.rows.length === 0) notFound();

  const car: Car = carResult.rows[0];
  const spec: Spec | null = specsResult.rows[0] ?? null;
  const equipment = modelEquipment(spec?.params_json);
  const sourceDescription = car.description?.trim();
  const sellerDescription = sourceDescription
    ? {
        text: car.translated_description ?? sourceDescription,
        translated:
          Boolean(car.translated_description) ||
          !/[\u3400-\u9fff\uf900-\ufaff]/u.test(sourceDescription),
        dictionary: Boolean(car.translated_description),
      }
    : null;
  const engineMl = [spec?.engine_ml, car.engine_ml].find(
    (value) => value != null && Number.isFinite(value) && value > 0,
  );
  const tires = firstDisplayValue(spec?.tires, car.tires);
  const remotePhotos = getPhotos(car);

  // Порядок берём из базы. Первые три фото подменяем локальными копиями, если они есть.
  const localPhotos = [car.local_photo, car.local_photo_2, car.local_photo_3];
  const photoSrcs = Array.from(
    { length: Math.max(remotePhotos.length, localPhotos.length) },
    (_, index) => {
      if (localPhotos[index]) return localPhotos[index];
      const remotePhoto = remotePhotos[index];
      return remotePhoto ? `/api/img?url=${encodeURIComponent(remotePhoto)}` : null;
    },
  ).filter((url): url is string => url !== null);

  return (
    <div className="min-h-screen bg-graphite-900">
      {/* Шапка */}
      <header className="border-b border-white/5 px-4 sm:px-6 py-4 flex flex-wrap gap-x-4 gap-y-2 items-center justify-between">
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
        <HeaderPhones className="w-full justify-between sm:w-auto sm:flex-col" />
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Хлебные крошки */}
        <div className="flex items-center gap-2 text-sm font-body text-gray-500 mb-6">
          <Link href="/catalog/used" className="hover:text-gray-300 transition-colors">
            Авто с пробегом
          </Link>
          <span>/</span>
          <span className="text-gray-300">
            {car.brand_ru} {cleanModel(car.model)}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Фото */}
          <CarGallery
            key={car.listing_id}
            photos={photoSrcs}
            alt={`${car.brand_ru} ${cleanModel(car.model)}`}
          />

          {/* Основная информация */}
          <div>
            <CarTitle car={car} />
            <p className="text-gray-400 font-body text-sm mb-6">
              {car.year} · {car.city_display}
              {car.distance_km && (
                <span className="ml-2 text-gray-400">
                  · {car.distance_source ? "≈ " : ""}
                  {car.distance_km.toLocaleString("ru")} км до Хоргоса
                  {car.distance_source && (
                    <>
                      {" "}
                      ·{" "}
                      <a
                        href="https://www.openstreetmap.org/copyright"
                        target="_blank"
                        rel="noreferrer"
                        className="inline-block whitespace-nowrap underline underline-offset-2 hover:text-gray-300"
                        title="Примерный дорожный маршрут от центра города до Хоргоса: OSRM, данные © OpenStreetMap contributors"
                      >
                        © OpenStreetMap
                      </a>
                    </>
                  )}
                </span>
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
                {
                  label: "Пробег",
                  value: car.mileage_km ? `${(car.mileage_km / 1000).toFixed(0)} тыс. км` : null,
                },
                // Своих данных у машины нет, пока не собрана карточка; тогда берём из комплектации
                { label: "Топливо", value: firstDisplayValue(car.fuel, spec?.fuel) },
                { label: "КПП", value: firstDisplayValue(car.gearbox, spec?.gearbox) },
                { label: "Цвет", value: displayValue(car.color) },
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
        {(spec || engineMl || tires) && (
          <div className="mt-10">
            <h2 className="font-heading font-bold text-lg text-white mb-4">
              Технические характеристики
            </h2>
            <div className="bg-graphite-800 rounded-xl overflow-hidden">
              <table className="w-full">
                <tbody>
                  {[
                    { label: "Топливо", value: displayValue(spec?.fuel) },
                    { label: "Привод", value: displayValue(spec?.drive) },
                    { label: "КПП", value: displayValue(spec?.gearbox) },
                    { label: "Мощность", value: spec?.power_hp ? `${spec.power_hp} л.с.` : null },
                    {
                      label: "Объём двигателя",
                      value: engineMl ? `${engineMl} мл` : null,
                    },
                    { label: "Шины", value: tires },
                    // Пока на китайском — скрываем; появится, когда сборщик начнёт переводить
                    { label: "Параметры", value: displayValue(spec?.params_text) },
                  ]
                    .filter(({ value }) => value)
                    .map(({ label, value }, i) => (
                      <tr key={label} className={i % 2 === 0 ? "bg-white/0" : "bg-white/[0.02]"}>
                        <td className="px-5 py-3 text-gray-400 font-body text-sm w-1/2 border-b border-white/5">
                          {label}
                        </td>
                        <td className="px-5 py-3 text-white font-body text-sm border-b border-white/5 [overflow-wrap:anywhere]">
                          {value}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {sellerDescription && (
          <section className="mt-10">
            <h2 className="font-heading font-bold text-lg text-white mb-2">Описание продавца</h2>
            <p className="text-gray-400 font-body text-sm mb-4">
              Информация со слов продавца. Состояние автомобиля уточняйте при осмотре.
              {sellerDescription.dictionary && " Перевод с китайского; оригинал доступен ниже."}
            </p>
            <div className="bg-graphite-800 rounded-xl p-5 text-gray-400 font-body text-sm">
              {sellerDescription.translated ? (
                <p className="text-white leading-relaxed whitespace-pre-line [overflow-wrap:anywhere]">
                  {sellerDescription.text}
                </p>
              ) : (
                <p>Автоматический перевод пока недоступен. Уточните информацию у нас.</p>
              )}
              <details className="group mt-3">
                <summary className="cursor-pointer text-white">
                  <span className="group-open:hidden">Показать оригинал</span>
                  <span className="hidden group-open:inline">Скрыть оригинал</span>
                </summary>
                <p className="mt-3 whitespace-pre-line [overflow-wrap:anywhere]">
                  {car.description}
                </p>
              </details>
            </div>
          </section>
        )}

        {equipment.length > 0 && (
          <section className="mt-10">
            <h2 className="font-heading font-bold text-lg text-white mb-2">Комплектация</h2>
            <p className="text-gray-400 font-body text-sm mb-4">
              Данные модели. Фактическое оснащение автомобиля уточняйте при осмотре.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {equipment.map(({ title, items }) => (
                <div key={title} className="bg-graphite-800 rounded-xl p-5 min-w-0">
                  <h3 className="font-heading font-bold text-white text-sm mb-3">{title}</h3>
                  <ul className="space-y-2">
                    {items.map(({ label, status }) => (
                      <li key={label} className="flex justify-between gap-3 text-sm font-body">
                        <span className="text-gray-400 min-w-0 [overflow-wrap:anywhere]">
                          {label}
                        </span>
                        <span className="text-white shrink-0">{status}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
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
