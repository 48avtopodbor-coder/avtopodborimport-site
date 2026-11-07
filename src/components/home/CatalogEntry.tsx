import Link from "next/link";

export default function CatalogEntry() {
  return (
    <section className="bg-graphite-900 py-6 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* С пробегом — основной */}
          <Link
            href="/catalog/used"
            className="group relative overflow-hidden bg-graphite-800 rounded-2xl p-8 border border-white/5 hover:border-orange-500/30 transition-all duration-300"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-orange-500/5 rounded-full -translate-y-1/2 translate-x-1/2 group-hover:bg-orange-500/10 transition-colors" />

            <div className="relative">
              <div className="inline-flex items-center gap-2 bg-orange-500/10 text-orange-500 font-body text-xs font-semibold px-3 py-1 rounded-full mb-4">
                <span className="w-1.5 h-1.5 bg-orange-500 rounded-full animate-pulse" />
                42&nbsp;184 авто в продаже
              </div>

              <h2 className="font-heading font-bold text-2xl text-white mb-2">
                С пробегом
                <br />
                из Китая
              </h2>
              <p className="text-gray-400 font-body text-sm mb-6 max-w-xs">
                Реальные объявления с площадки che168.com. Обновляются каждый час. Цена уже в рублях под ключ.
              </p>

              <div className="flex items-center gap-2 text-orange-500 font-body font-semibold text-sm group-hover:gap-3 transition-all">
                Смотреть каталог
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </div>
            </div>

            {/* Мини-превью марок */}
            <div className="relative mt-6 flex flex-wrap gap-2">
              {["Haval", "Geely", "Chery", "BYD", "Li Auto", "Tank"].map((brand) => (
                <span
                  key={brand}
                  className="bg-graphite-700 text-gray-400 text-xs font-body px-3 py-1 rounded-full"
                >
                  {brand}
                </span>
              ))}
              <span className="bg-graphite-700 text-gray-500 text-xs font-body px-3 py-1 rounded-full">
                +12 марок
              </span>
            </div>
          </Link>

          {/* Новые */}
          <Link
            href="/catalog/new"
            className="group relative overflow-hidden bg-graphite-800 rounded-2xl p-8 border border-white/5 hover:border-orange-500/30 transition-all duration-300"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/2 rounded-full -translate-y-1/2 translate-x-1/2 group-hover:bg-white/4 transition-colors" />

            <div className="relative">
              <div className="inline-flex items-center gap-2 bg-white/5 text-gray-400 font-body text-xs font-semibold px-3 py-1 rounded-full mb-4">
                Скоро
              </div>

              <h2 className="font-heading font-bold text-2xl text-white mb-2">
                Новые
                <br />
                из Китая
              </h2>
              <p className="text-gray-400 font-body text-sm mb-6 max-w-xs">
                Новые автомобили с завода. Актуальные модели 2024–2025 года. Гарантия производителя.
              </p>

              <div className="flex items-center gap-2 text-gray-500 font-body font-semibold text-sm">
                Скоро в каталоге
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </div>
            </div>

            <div className="relative mt-6 flex flex-wrap gap-2">
              {["Haval H6", "Geely Monjaro", "Chery Tiggo 8", "BYD Seal"].map((model) => (
                <span
                  key={model}
                  className="bg-graphite-700 text-gray-500 text-xs font-body px-3 py-1 rounded-full"
                >
                  {model}
                </span>
              ))}
            </div>
          </Link>

        </div>
      </div>
    </section>
  );
}
