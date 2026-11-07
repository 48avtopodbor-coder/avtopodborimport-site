import Link from "next/link";

// Заглушки — потом заменим реальными данными из базы
const MOCK_CARS = [
  {
    id: "1",
    brand: "Haval",
    model: "Jolion",
    year: 2023,
    mileage: 18000,
    priceChina: 1200000,
    priceTotal: 1890000,
    city: "Чэнду",
    fuel: "Гибрид",
    transmission: "Автомат",
    color: "Белый",
  },
  {
    id: "2",
    brand: "Geely",
    model: "Coolray",
    year: 2022,
    mileage: 32000,
    priceChina: 980000,
    priceTotal: 1620000,
    city: "Шанхай",
    fuel: "Бензин",
    transmission: "Автомат",
    color: "Серый",
  },
  {
    id: "3",
    brand: "Chery",
    model: "Tiggo 7 Pro",
    year: 2023,
    mileage: 12000,
    priceChina: 1450000,
    priceTotal: 2180000,
    city: "Пекин",
    fuel: "Бензин",
    transmission: "Автомат",
    color: "Синий",
  },
  {
    id: "4",
    brand: "BYD",
    model: "Seal",
    year: 2023,
    mileage: 8000,
    priceChina: 2100000,
    priceTotal: 3050000,
    city: "Шэньчжэнь",
    fuel: "Электро",
    transmission: "Автомат",
    color: "Чёрный",
  },
];

function formatPrice(price: number) {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(price);
}

function formatMileage(km: number) {
  return new Intl.NumberFormat("ru-RU").format(km) + " км";
}

export default function LatestArrivals() {
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
            Все 42 184 авто
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MOCK_CARS.map((car) => (
            <Link
              key={car.id}
              href={`/car/${car.id}`}
              className="group bg-graphite-800 rounded-xl overflow-hidden border border-white/5 hover:border-orange-500/20 transition-all duration-200"
            >
              {/* Фото-заглушка */}
              <div className="aspect-[4/3] bg-graphite-700 relative overflow-hidden">
                <div className="absolute inset-0 flex items-center justify-center">
                  <svg className="w-16 h-16 text-graphite-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 9l-7-7-7 7M5 9v11a1 1 0 001 1h3v-5h4v5h3a1 1 0 001-1V9" />
                  </svg>
                </div>
                {/* Бейдж топлива */}
                <div className="absolute top-2 left-2">
                  <span className="bg-graphite-900/80 text-gray-300 font-body text-xs px-2 py-1 rounded-full backdrop-blur">
                    {car.fuel}
                  </span>
                </div>
              </div>

              {/* Инфо */}
              <div className="p-4">
                <div className="font-heading font-bold text-sm text-white mb-1">
                  {car.brand} {car.model}
                </div>
                <div className="flex items-center gap-2 text-gray-400 font-body text-xs mb-3">
                  <span>{car.year}</span>
                  <span>·</span>
                  <span>{formatMileage(car.mileage)}</span>
                  <span>·</span>
                  <span>{car.city}</span>
                </div>

                {/* Цены */}
                <div className="border-t border-white/5 pt-3">
                  <div className="text-gray-500 font-body text-xs mb-0.5">
                    Цена в Китае: {formatPrice(car.priceChina)}
                  </div>
                  <div className="font-heading font-bold text-orange-500 text-base">
                    {formatPrice(car.priceTotal)}
                  </div>
                  <div className="text-gray-500 font-body text-xs">под ключ в России</div>
                </div>
              </div>
            </Link>
          ))}
        </div>

        <div className="text-center mt-8 sm:hidden">
          <Link
            href="/catalog/used"
            className="inline-flex items-center gap-2 bg-graphite-800 text-white font-body font-semibold text-sm px-6 py-3 rounded-xl border border-white/5 hover:border-orange-500/30 transition-all"
          >
            Все 42 184 авто
          </Link>
        </div>
      </div>
    </section>
  );
}
