import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-graphite-900 border-t border-white/5 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Логотип и описание */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
                <span className="font-heading font-bold text-white text-xs">AI</span>
              </div>
              <span className="font-heading font-bold text-white text-sm uppercase tracking-wider">
                Avtopodbor Import
              </span>
            </div>
            <p className="text-gray-400 font-body text-sm leading-relaxed max-w-sm">
              Подбор и ввоз автомобилей из Китая под ключ. Прозрачная цена с доставкой и растаможкой.
            </p>
          </div>

          {/* Каталог */}
          <div>
            <div className="font-heading font-bold text-xs uppercase tracking-wider text-gray-500 mb-4">
              Каталог
            </div>
            <ul className="space-y-2">
              <li><Link href="/catalog/used" className="text-gray-400 hover:text-white font-body text-sm transition-colors">С пробегом из Китая</Link></li>
              <li><Link href="/catalog/new" className="text-gray-400 hover:text-white font-body text-sm transition-colors">Новые автомобили</Link></li>
              <li><Link href="/price" className="text-gray-400 hover:text-white font-body text-sm transition-colors">Цена под ключ</Link></li>
            </ul>
          </div>

          {/* Офисы */}
          <div>
            <div className="font-heading font-bold text-xs uppercase tracking-wider text-gray-500 mb-4">
              Офисы
            </div>
            <ul className="space-y-2 font-body text-sm text-gray-400">
              <li>Владивосток</li>
              <li>Москва</li>
              <li>Липецк</li>
            </ul>
          </div>
        </div>

        <div className="border-t border-white/5 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-gray-600 font-body text-xs">
            © 2024 AVTOPODBOR IMPORT. Расчёты предварительные.
          </p>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="text-gray-600 hover:text-gray-400 font-body text-xs transition-colors">
              Политика конфиденциальности
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
