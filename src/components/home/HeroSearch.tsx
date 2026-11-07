"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const BRANDS = [
  "Любая марка", "Haval", "Geely", "Chery", "Changan", "BYD",
  "Li Auto", "Tank", "Exeed", "Zeekr", "Mercedes-Benz",
  "Hyundai", "Kia", "Toyota", "BMW", "Audi", "Volkswagen", "Skoda",
];

const BODY_TYPES = [
  "Любой кузов", "Седан", "Кроссовер", "Внедорожник", "Хэтчбек", "Минивэн",
];

export default function HeroSearch() {
  const router = useRouter();
  const [brand, setBrand] = useState("");
  const [bodyType, setBodyType] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [catalogType, setCatalogType] = useState<"used" | "new">("used");

  const handleSearch = () => {
    const params = new URLSearchParams();
    if (brand) params.set("brand", brand);
    if (bodyType) params.set("body", bodyType);
    if (priceMax) params.set("price_max", priceMax);
    router.push(`/catalog/${catalogType}?${params.toString()}`);
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
            42&nbsp;000+ машин с пробегом из Китая. Цена уже с доставкой и растаможкой.
          </p>
        </div>

        {/* Переключатель каталога */}
        <div className="flex justify-center mb-6">
          <div className="bg-graphite-800 rounded-xl p-1 flex gap-1">
            <button
              onClick={() => setCatalogType("used")}
              className={`px-6 py-2.5 rounded-lg font-body font-semibold text-sm transition-all ${
                catalogType === "used"
                  ? "bg-orange-500 text-white shadow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              С пробегом
            </button>
            <button
              onClick={() => setCatalogType("new")}
              className={`px-6 py-2.5 rounded-lg font-body font-semibold text-sm transition-all ${
                catalogType === "new"
                  ? "bg-orange-500 text-white shadow"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Новые
            </button>
          </div>
        </div>

        {/* Поисковая форма */}
        <div className="max-w-3xl mx-auto">
          <div className="bg-graphite-800 rounded-2xl p-2 flex flex-col sm:flex-row gap-2">
            {/* Марка */}
            <select
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              className="flex-1 bg-graphite-700 text-white font-body text-sm rounded-xl px-4 py-3 outline-none appearance-none cursor-pointer"
            >
              {BRANDS.map((b) => (
                <option key={b} value={b === "Любая марка" ? "" : b}>
                  {b}
                </option>
              ))}
            </select>

            {/* Кузов */}
            <select
              value={bodyType}
              onChange={(e) => setBodyType(e.target.value)}
              className="flex-1 bg-graphite-700 text-white font-body text-sm rounded-xl px-4 py-3 outline-none appearance-none cursor-pointer"
            >
              {BODY_TYPES.map((b) => (
                <option key={b} value={b === "Любой кузов" ? "" : b}>
                  {b}
                </option>
              ))}
            </select>

            {/* Бюджет */}
            <input
              type="number"
              placeholder="Бюджет, ₽"
              value={priceMax}
              onChange={(e) => setPriceMax(e.target.value)}
              className="flex-1 bg-graphite-700 text-white font-body text-sm rounded-xl px-4 py-3 outline-none placeholder:text-gray-500"
            />

            {/* Кнопка поиска */}
            <button
              onClick={handleSearch}
              className="bg-orange-500 hover:bg-orange-600 text-white font-body font-bold text-sm px-8 py-3 rounded-xl transition-colors whitespace-nowrap"
            >
              Найти авто
            </button>
          </div>

          {/* Быстрые фильтры */}
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {["До 2 млн ₽", "До 3 млн ₽", "Кроссоверы", "Haval", "Geely", "BYD"].map((tag) => (
              <button
                key={tag}
                className="bg-graphite-800 hover:bg-graphite-700 text-gray-400 hover:text-white font-body text-xs px-4 py-2 rounded-full border border-white/5 transition-all"
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
