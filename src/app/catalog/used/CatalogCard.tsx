import Link from "next/link";
import { formatCarFullName } from "@/lib/car-title";
import { firstDisplayValue } from "@/lib/format";
import type { CatalogCar } from "@/lib/catalog-data";
function getFirstPhoto(car: CatalogCar): string | null {
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

export default function CatalogCard({ car }: { car: CatalogCar }) {
  const name = formatCarFullName(car);
  const remotePhoto = getFirstPhoto(car);
  const photoSrc =
    car.local_photo || (remotePhoto ? `/api/img?url=${encodeURIComponent(remotePhoto)}` : null);
  return (
    <Link
      href={`/car/${car.listing_id}`}
      className="bg-graphite-800 rounded-xl overflow-hidden hover:ring-1 hover:ring-orange-500/50 transition-all group"
    >
      {/* Фото */}
      <div className="relative h-44 bg-graphite-700">
        {photoSrc ? (
          <img src={photoSrc} alt={name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600">
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Инфо */}
      <div className="p-3">
        <div className="font-heading font-bold text-white text-sm mb-1 [overflow-wrap:anywhere]">
          {name}
        </div>
        <div className="flex gap-3 text-xs text-gray-400 font-body mb-2">
          <span>{car.year}</span>
          <span>{car.mileage_km ? `${(car.mileage_km / 1000).toFixed(0)} тыс. км` : "—"}</span>
          {firstDisplayValue(car.fuel, car.spec_fuel) && (
            <span>{firstDisplayValue(car.fuel, car.spec_fuel)}</span>
          )}
        </div>
        <div className="text-orange-400 font-heading font-bold text-sm">
          {formatPrice(car.price_cny)}
        </div>
        <div className="text-xs text-gray-500 font-body">{car.city_display}</div>
      </div>
    </Link>
  );
}
