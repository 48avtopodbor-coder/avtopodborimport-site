"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BODY_NAMES, MAX_PRICE_RUB, catalogHref, parseFilters } from "@/lib/catalog-filters";
import { formatCarCount } from "@/lib/format";

const BRANDS = [
  "Haval",
  "Geely",
  "Chery",
  "Changan",
  "BYD",
  "Li Auto",
  "Tank",
  "Exeed",
  "Zeekr",
  "Mercedes-Benz",
  "Hyundai",
  "Kia",
  "Toyota",
  "BMW",
  "Audi",
  "Volkswagen",
  "Skoda",
  "Mazda",
];

const controlClass =
  "w-full min-w-0 bg-graphite-700 text-white font-body text-sm rounded-xl px-4 py-3";
const quickFilterClass =
  "bg-graphite-800 hover:bg-graphite-700 text-gray-400 hover:text-white font-body text-xs px-4 py-2 rounded-full border border-white/5 transition-all";

export default function HeroSearch({
  total,
  priceAvailable,
}: {
  total: number | null;
  priceAvailable: boolean;
}) {
  const router = useRouter();

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const budget = String(data.get("priceTo") ?? "");
    router.push(
      catalogHref(
        parseFilters({
          brand: String(data.get("brand") ?? ""),
          body: String(data.get("body") ?? ""),
          priceTo: priceAvailable && budget ? String(Number(budget)) : undefined,
        }),
      ),
    );
  };

  return (
    <section className="relative overflow-hidden bg-graphite-900 pt-12 pb-16">
      {/* Фоновый акцент */}
      <div className="absolute inset-0 bg-gradient-to-br from-orange-500/5 via-transparent to-transparent pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Заголовок */}
        <div className="text-center mb-10">
          <p className="text-orange-500 font-heading text-xs uppercase tracking-widest mb-3">
            Авто из Китая под ключ
          </p>
          <h1 className="font-heading font-bold text-3xl sm:text-4xl lg:text-5xl text-white leading-tight mb-4">
            Найди свой автомобиль
          </h1>
          <p className="text-gray-400 font-body text-lg max-w-xl mx-auto">
            {total === null ? "Автомобили" : formatCarCount(total)} с пробегом из Китая. Цена уже с
            доставкой и растаможкой.
          </p>
        </div>

        {/* Поисковая форма */}
        <div className="max-w-3xl mx-auto">
          <form
            action="/catalog/used"
            onSubmit={handleSearch}
            className={`grid grid-cols-1 gap-2 rounded-2xl bg-graphite-800 p-2 ${
              priceAvailable
                ? "sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)_minmax(0,0.85fr)_auto]"
                : "sm:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)_auto]"
            }`}
          >
            <select name="brand" aria-label="Марка" className={`${controlClass} cursor-pointer`}>
              <option value="">Любая марка</option>
              {BRANDS.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>

            <select name="body" aria-label="Кузов" className={`${controlClass} cursor-pointer`}>
              <option value="">Любой кузов</option>
              {Object.entries(BODY_NAMES).map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>

            {priceAvailable && (
              <input
                name="priceTo"
                type="number"
                inputMode="numeric"
                min={0}
                max={MAX_PRICE_RUB}
                aria-label="Бюджет, ₽"
                placeholder="Бюджет, ₽"
                className={`${controlClass} placeholder:text-gray-500`}
              />
            )}

            <button
              type="submit"
              className="bg-orange-500 hover:bg-orange-600 text-white font-body font-bold text-sm px-8 py-3 rounded-xl transition-colors whitespace-nowrap"
            >
              Найти авто
            </button>
          </form>

          {/* Быстрые фильтры */}
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {priceAvailable &&
              [2, 3].map((millions) => (
                <Link
                  key={millions}
                  href={`/catalog/used?priceTo=${millions * 1_000_000}`}
                  prefetch={false}
                  className={quickFilterClass}
                >
                  До {millions} млн ₽
                </Link>
              ))}
            <Link href="/catalog/used?body=suv" prefetch={false} className={quickFilterClass}>
              Кроссоверы
            </Link>
            {["Haval", "Geely", "BYD"].map((name) => (
              <Link
                key={name}
                href={catalogHref(parseFilters({ brand: name }))}
                prefetch={false}
                className={quickFilterClass}
              >
                {name}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
