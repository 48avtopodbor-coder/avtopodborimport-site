export default async function CarPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="min-h-screen bg-graphite-900 flex items-center justify-center">
      <div className="text-center">
        <h1 className="font-heading font-bold text-2xl text-white mb-2">
          Автомобиль #{id}
        </h1>
        <p className="text-gray-400 font-body">Страница в разработке</p>
      </div>
    </main>
  );
}
