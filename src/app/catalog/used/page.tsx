import Link from "next/link";
import type { Metadata } from "next";
import { parseFilters, catalogHref, type QueryInput } from "@/lib/catalog-filters";
import {
  getCatalogFacets,
  getCatalogList,
  normalizeCatalogFilters,
  brandRegistry,
} from "@/lib/catalog-data";
import CatalogFilters from "./CatalogFilters";
import CatalogCard from "./CatalogCard";
type Props = { searchParams: Promise<QueryInput> };
export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const filters = await normalizeCatalogFilters(parseFilters(await searchParams));
  const brands = await brandRegistry();
  const brand = brands.find((b) => b.slug === filters.brand);
  const title = brand
    ? `${brand.name} с пробегом из Китая — купить под ключ`
    : "Авто с пробегом из Китая — AVTOPODBOR IMPORT";
  const canonical =
    "https://avtopodborimport.ru/catalog/used" +
    (brand ? "?" + new URLSearchParams({ brand: brand.slug }) : "");
  return {
    title,
    description: brand
      ? `Каталог ${brand.name} с пробегом из Китая. Характеристики, фотографии и подбор автомобиля с доставкой.`
      : "Каталог автомобилей с пробегом из Китая: марки, модели, характеристики и фотографии.",
    alternates: { canonical },
  };
}
export default async function UsedCatalogPage({ searchParams }: Props) {
  const filters = await normalizeCatalogFilters(parseFilters(await searchParams));
  const [list, facets] = await Promise.all([getCatalogList(filters), getCatalogFacets(filters)]);
  const current = { ...filters, page: list.page };
  const pages = Math.ceil(list.total / list.pageSize);
  return (
    <>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="mb-5">
          <h1 className="font-heading text-2xl font-bold text-white">Авто с пробегом из Китая</h1>
          <p className="mt-1 min-h-5 font-body text-sm tabular-nums text-gray-400">
            {list.total.toLocaleString("ru")} автомобилей
          </p>
        </div>
        <CatalogFilters filters={current} initialFacets={facets} />
        <noscript>
          <form
            action="/catalog/used"
            className="mb-6 flex flex-wrap gap-3 rounded-xl bg-graphite-800 p-4 text-sm text-white"
          >
            <label>
              Марка
              <select
                name="brand"
                defaultValue={filters.brand}
                className="ml-2 min-h-11 bg-graphite-900"
              >
                <option value="">Все марки</option>
                {facets.brands.map((b) => (
                  <option key={b.slug} value={b.slug}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>
            {filters.brand && (
              <label>
                Модели
                <select
                  multiple
                  name="model"
                  defaultValue={filters.models}
                  className="ml-2 bg-graphite-900"
                >
                  {facets.models.map((m) => (
                    <option key={m.slug} value={m.slug}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Год от
              <input
                name="yearFrom"
                type="number"
                defaultValue={filters.yearFrom}
                className="ml-2 min-h-11 w-24 bg-graphite-900"
              />
            </label>
            <label>
              Пробег до
              <input
                name="mileageTo"
                type="number"
                defaultValue={filters.mileageTo}
                className="ml-2 min-h-11 w-28 bg-graphite-900"
              />
            </label>
            <button className="min-h-11 rounded-lg bg-orange-500 px-4 text-black">
              Применить фильтры
            </button>
          </form>
        </noscript>
        {list.total === 0 ? (
          <section className="rounded-xl bg-graphite-800 p-8 text-center">
            <h2 className="font-heading text-xl font-bold text-white">Ничего не нашли</h2>
            <p className="mt-3 text-gray-400">Попробуйте ослабить условия поиска.</p>
            <Link
              href="/catalog/used"
              className="mt-5 inline-flex min-h-11 items-center rounded-lg bg-orange-500 px-5 font-semibold text-black"
            >
              Сбросить фильтры
            </Link>
          </section>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {list.items.map((car) => (
              <CatalogCard key={car.listing_id} car={car} />
            ))}
          </div>
        )}
        {pages > 1 && (
          <nav
            aria-label="Страницы каталога"
            className="mt-8 flex min-h-11 items-center justify-center gap-3 font-body text-sm text-gray-200"
          >
            {list.page > 1 && (
              <Link
                rel="prev"
                href={catalogHref({ ...current, page: list.page - 1 })}
                className="inline-flex min-h-11 items-center rounded-lg bg-graphite-800 px-4"
              >
                ← Назад
              </Link>
            )}
            <span className="tabular-nums">
              {list.page} / {pages}
            </span>
            {list.page < pages && (
              <Link
                rel="next"
                href={catalogHref({ ...current, page: list.page + 1 })}
                className="inline-flex min-h-11 items-center rounded-lg bg-graphite-800 px-4"
              >
                Вперёд →
              </Link>
            )}
          </nav>
        )}
      </main>
    </>
  );
}
