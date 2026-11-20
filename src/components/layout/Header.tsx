import Link from "next/link";
import HeaderPhones, { consultationHref } from "./HeaderPhones";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 bg-graphite-900/95 backdrop-blur border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
        <div className="grid min-h-16 items-center gap-x-3 gap-y-2 py-2 sm:grid-cols-[minmax(0,1fr)_auto] lg:grid-cols-[auto_1fr_auto]">
          {/* Логотип */}
          <Link href="/" className="flex w-fit items-center gap-3">
            <div className="w-8 h-8 shrink-0 bg-orange-500 rounded-lg flex items-center justify-center">
              <span className="font-heading font-bold text-white text-xs">AI</span>
            </div>
            <span className="font-heading font-bold text-white text-sm uppercase tracking-wider">
              Avtopodbor Import
            </span>
          </Link>

          {/* Навигация */}
          <nav className="hidden items-center justify-self-center gap-6 md:col-span-full md:row-start-2 md:flex lg:col-span-1 lg:col-start-2 lg:row-start-1 lg:gap-3 xl:gap-6">
            <Link
              href="/catalog/used"
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              С пробегом
            </Link>
            <Link
              href="/catalog/new"
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              Новые
            </Link>
            <Link
              href="/price"
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              Цена под ключ
            </Link>
            <Link
              href="/contacts"
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              Контакты
            </Link>
          </nav>

          <div className="flex items-center justify-between gap-3 sm:col-start-2 sm:row-start-1 sm:justify-self-end lg:col-start-3 xl:gap-5">
            <HeaderPhones className="shrink-0 flex-col" />
            <a
              href={consultationHref}
              className="text-center bg-orange-500 hover:bg-orange-600 text-white font-body font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
            >
              Получить консультацию
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}
