export default function Loading() {
  return (
    <div className="min-h-screen bg-graphite-900">
      <header className="border-b border-white/5 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-orange-500 rounded flex items-center justify-center">
            <span className="font-bold text-white text-xs">AI</span>
          </div>
          <span className="font-bold text-white text-sm uppercase tracking-wider">
            AVTOPODBOR IMPORT
          </span>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-6">
          <div className="h-8 w-64 bg-graphite-800 rounded animate-pulse mb-2" />
          <div className="h-4 w-32 bg-graphite-800 rounded animate-pulse" />
        </div>

        <div className="flex gap-8">
          <aside className="hidden lg:block w-56 shrink-0">
            <div className="bg-graphite-800 rounded-xl p-4 h-96 animate-pulse" />
          </aside>

          <div className="flex-1">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="bg-graphite-800 rounded-xl overflow-hidden animate-pulse">
                  <div className="h-44 bg-graphite-700" />
                  <div className="p-3">
                    <div className="h-4 bg-graphite-700 rounded mb-2 w-3/4" />
                    <div className="h-3 bg-graphite-700 rounded mb-2 w-1/2" />
                    <div className="h-4 bg-graphite-700 rounded w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
