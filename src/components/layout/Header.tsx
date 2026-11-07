import Link from "next/link";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 bg-graphite-900/95 backdrop-blur border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Логотип */}
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
              <span className="font-heading font-bold text-white text-xs">AI</span>
            </div>
            <span className="font-heading font-bold text-white text-sm uppercase tracking-wider">
              Avtopodbor Import
            </span>
          </Link>

          {/* Навигация */}
          <nav className="hidden md:flex items-center gap-6">
            <Link href="/catalog/used" className="text-gray-400 hover:text-white text-sm transition-colors">
              С пробегом
            </Link>
            <Link href="/catalog/new" className="text-gray-400 hover:text-white text-sm transition-colors">
              Новые
            </Link>
            <Link href="/price" className="text-gray-400 hover:text-white text-sm transition-colors">
              Цена под ключ
            </Link>
            <Link href="/contacts" className="text-gray-400 hover:text-white text-sm transition-colors">
              Контакты
            </Link>
          </nav>

          {/* CTA */}
          <a
            href="tel:+74742000000"
            className="bg-orange-500 hover:bg-orange-600 text-white font-body font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
          >
            Получить консультацию
          </a>
        </div>
      </div>
    </header>
  );
}
