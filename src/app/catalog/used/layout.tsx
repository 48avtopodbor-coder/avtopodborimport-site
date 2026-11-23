import Link from "next/link";
import HeaderPhones from "@/components/layout/HeaderPhones";
import HeaderHomeLink from "@/components/layout/HeaderHomeLink";
export default function CatalogLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-graphite-900">
      <header className="border-b border-white/5 px-4 sm:px-6 py-4 flex flex-wrap gap-x-4 gap-y-2 items-center justify-between">
        <div className="flex min-w-0 items-center gap-2 sm:gap-5">
          <Link href="/" className="flex min-w-0 items-center gap-2 sm:gap-3">
            <div className="w-8 h-8 shrink-0 bg-orange-500 rounded flex items-center justify-center">
              <span className="font-heading font-bold text-white text-xs">AI</span>
            </div>
            <span className="font-heading font-bold text-white text-sm uppercase tracking-wider max-[420px]:max-w-[130px] max-[420px]:leading-4">
              AVTOPODBOR IMPORT
            </span>
          </Link>
          <HeaderHomeLink />
        </div>
        <nav className="hidden md:flex gap-6 text-sm font-body">
          <Link href="/catalog/used" className="text-white">
            С пробегом
          </Link>
          <Link href="/catalog/new" className="text-gray-400 hover:text-white transition-colors">
            Новые
          </Link>
          <Link href="/price" className="text-gray-400 hover:text-white transition-colors">
            Цена под ключ
          </Link>
        </nav>
        <HeaderPhones className="w-full justify-between sm:w-auto sm:flex-col sm:max-[930px]:ml-auto" />
      </header>
      {children}
    </div>
  );
}
