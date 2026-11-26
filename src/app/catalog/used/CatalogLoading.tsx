export default function CatalogLoading() {
  return (
    <div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6"
      role="status"
      aria-label="Загружаем автомобили"
    >
      <div className="mb-3 h-8 w-3/4 rounded-lg bg-graphite-800" />
      <div className="mb-6 h-5 w-40 rounded bg-graphite-800" />
      <div className="mb-6 h-11 w-full rounded-full bg-graphite-800" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 12 }, (_, i) => (
          <div key={i} className="h-72 animate-pulse rounded-xl bg-graphite-800" />
        ))}
      </div>
    </div>
  );
}
