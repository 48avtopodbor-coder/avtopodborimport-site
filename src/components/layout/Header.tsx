import Link from "next/link";
import HeaderPhones, { consultationHref } from "./HeaderPhones";

export default function Header() {
  return (
    <header className="home-header sticky top-0 z-50 bg-graphite-900/95 backdrop-blur border-b border-white/5">
      <div className="home-header-inner max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
        <div className="home-header-grid grid min-h-16 grid-cols-1 items-center gap-x-3 gap-y-2 py-2">
          {/* Логотип */}
          <Link
            href="/"
            className="home-header-brand flex w-fit min-w-0 max-w-full items-center gap-3"
          >
            <div className="w-8 h-8 shrink-0 bg-orange-500 rounded-lg flex items-center justify-center">
              <span className="font-heading font-bold text-white text-xs">AI</span>
            </div>
            <span className="font-heading min-w-0 font-bold text-white text-sm uppercase tracking-wider">
              Avtopodbor Import
            </span>
          </Link>

          {/* Навигация */}
          <nav className="home-header-menu items-center justify-self-center gap-6">
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

          <div className="home-header-contacts flex min-w-0 items-center justify-between gap-3 xl:gap-5">
            <HeaderPhones className="shrink-0 flex-col" />
            <a
              href={consultationHref}
              className="min-w-0 max-w-full text-center [overflow-wrap:anywhere] bg-orange-500 hover:bg-orange-600 text-white font-body font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
            >
              Получить консультацию
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}
